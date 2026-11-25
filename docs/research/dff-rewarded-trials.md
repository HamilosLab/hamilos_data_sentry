# How DF/F of rewarded trials is computed today, and where it lives in a statObj

Ticket: HamilosLab/hamilos_data_sentry#13. Research only; nothing on the share or in sibling repos was modified.

Evidence labels: **[V]** verified (file, command or count given), **[I]** inference, **[?]** unknown.

Sources read: `CLASS_photometry_roadmapv1_4` (sibling repo `photometry_roadmapv1_4/src/`), `MATLAB/CED Analysis/` scripts (`gfitdF_F_fx.m`, `Roadmap 1.4 Split By Signals/FX_gfitdF_F_fx_roadmapv1_4.m`, `operant only/first_lick_grabber_operant_fx_0msv.m`, `trial_binner_fx.m`, `licksplorer_3.m`, `Nao_method_df_f.m`), top-level `MATLAB/normalizedMultiBaselineDFF.m`, and the downstream Python extractors in sibling repo `norri_stochastic_generative_2026` (`src/latent-sampling/da_ramps_l26/l26_extract_ramps.py`, `src/sessions_registry/statobj_labels.py`). Data: read-only h5py on `Mouse Data/` (see "Method" at the end).

## Short answers

1. `gfit` is a fractional DF/F (0.027 means 2.7 %), at the photometry sample rate (1 kHz in 200 of 206 per-session statObjs). In every photometry statObj I surveyed it is the "10-trial normalized multi-baseline" DF/F, not the older 200-s moving-mean DF/F. [V: 201 of 206 objects have `GLM.gfitMode = '10trial norm multi baseline'`; the other 5 are `Abs-X`, a rectified accelerometer trace, not DA.]
2. Per trial, F0 is the median raw F over the 5 s ending at cue onset; the F0 used for trial i is the mean of those medians over trials i-5..i+5 (truncated at the session edges). Every sample from 5 s before cue i up to 5 s before cue i+1 is `(F - F0) / F0`. I re-implemented this in numpy from `GLM.rawF` and `GLM.pos.baselineStart` and it reproduces the stored `gfit` exactly (max abs difference 0.0 over all 791 trials of one session). [V]
3. "Rewarded" has three non-identical definitions in the lab code. The usable one from a statObj is: first lick after cue falls in [3.333, 7) s after cue (`GLM.flick_s_wrtc`). `GLM.rewardedTrials` (juice-based) differs from it in 153 of 202 sessions. [V, details below]
4. h5py can read all of the needed arrays from a per-session statObj. It cannot decode the MCOS object wrapper itself, but the property values are ordinary MATLAB structs and arrays under `/#refs#/`, and they are found by matching keys. [V on 206 files, one recipe run end to end]
5. The DA-vs-control question has no clean answer from the statObj alone: the control channel in every file is `X` (accelerometer), a tdTomato `tdt` reference is stored in only 1 of 206, and the file does not say which of `VLS` / `VLSred` is the DA indicator. [V / ?]

## 1. What `gfit` is

### 1a. Current style: normalized multi-baseline (the one in the statObjs)

Code: method `normalizedMultiBaselineDFF(obj, baselineWin, nTrials, ts, ...)` of the class (`CLASS_photometry_roadmapv1_4.m`, around line 16317; the call that builds `gfit` is `obj.normalizedMultiBaselineDFF(5000, 10, obj.GLM.rawF)`, e.g. in `addMoveControls`, `Window = 5000; ntrials = 10`, and in `redoNMBgfitChR2`). `gfitMode` is set to `'10trial norm multi baseline'`. [V: code read]

Steps (in samples; 1 sample = 1 ms at 1 kHz):

1. Despike: moving-mean smooth of raw F with span 1000, subtract, replace points more than 15 SD above the residual by the mean of their two neighbours.
2. Baseline per trial: `F0s(i) = median(F[cue_i - 5000 + 1 : cue_i])`, 5 s ending at cue onset. Stored as `GLM.pos.baselineStart(i) = pos.cue(i) - 5000 + 1`. [V: `baselineStart - cue = -4999` for every trial of the Peter day-13 object]
3. `F0(i) = nanmean(F0s(i-5 : i+5))` (11 trials; edge trials use whatever neighbours exist).
4. `gfit[baselineStart(i) : baselineStart(i+1)-1] = (F - F0(i)) / F0(i)`. So each trial's DF/F segment starts 5 s before its own cue and ends 5 s before the next cue.
5. Samples before the first trial's baseline start use the older 200-s moving-mean DF/F (1b).
6. At the end, values above 15 SD of the whole trace are set to NaN (one NaN per file in the files checked; only the positive tail is clipped).

Verification [V]: numpy re-implementation of steps 2-4 from `rawF` and `pos.baselineStart` of the Peter day-13 VLS object gave `max |pred - gfit| = 0.0` in trials 1, 2, 101 and 790, and median per-trial error 0.0 over all trials (the despike step did not change any sample in those segments).

Consequences for any signal-quality metric [I]: the pre-cue baseline is near 0 by construction (stored `gfit` median is about 0 in the sessions I looked at), so baseline level says nothing about quality; the baseline window (5000) and `nTrials` (10) are **not stored** in the object (`gFitLP` is an empty struct) and are known only from code defaults plus `pos.baselineStart`. Samples are counted, not milliseconds, so at a non-1-kHz sampling rate (see section 6) the 5000-sample window is not 5 s.

### 1b. Older style: 200-s moving-mean "box" DF/F

`MATLAB/CED Analysis/gfitdF_F_fx.m` (two channels, 2017) and `Roadmap 1.4 Split By Signals/FX_gfitdF_F_fx_roadmapv1_4.m` (one channel, window passed as a string). Both: despike as above, then `Fsmooth = smooth(Frs, 200000, 'moving')` and `gfit = (Frs - Fsmooth) ./ Fsmooth`. At 1 kHz the window is 200 s; the code comments saying "10 seconds" are stale. [V: code read; the 1000/200000 are sample counts] MATLAB's `smooth` with `'moving'` forces an odd span and shrinks the window at the ends [I: from MATLAB documentation, not tested here]. In the class this is `gfitMode = 'box200000'`; `gfitBox(ts, win)` calls it. I did not find a per-session statObj on the share with this mode (0 of 206), but the class still supports it and the pre-session segment of every multi-baseline `gfit` is made with it. [V / ?: older objects elsewhere were not surveyed]

### 1c. Legacy per-trial "local" DF/F (2017 GUI scripts)

`licksplorer_3.m` ('Local' = subtract the mean of the last 3 s of each trial; optional exponential-fit correction), `Nao_method_df_f.m` (F0 = mean of the previous trial's last ~1 s, DF/F = (F - F0)/F0), `trial_binner_fx.m` (bins trials by first-lick time, with the local-DF/F code commented out). These are pre-Roadmap-1.4 tools; none of these styles appears as a `gfitMode` in the objects surveyed. Top-level `MATLAB/normalizedMultiBaselineDFF.m` is a dead stub that begins with `error('not implemented ...')`; the working implementation is the class method. [V: read]

### 1d. `Abs-X` objects

For 5 of 206 objects `gfit = abs(bandpass(accelerometer X))` (`gfitMode = 'Abs-X'`): 4 with `iv.signalname = 'X'` (sampling interval 0.5 ms) and 1 `VLS` object at about 20 Hz. This is movement, not DF/F. Filter on `iv.signaltype_ == 'photometry'` and `gfitMode != 'Abs-X'`. [V]

## 2. How a trial is labelled "rewarded"

Task geometry in code: reward window opens 3.333 s after cue and closes at 7 s; trial length `iv.total_time_ = 17000` ms; 0-ms reaction window (licks in 0-0.5 s after cue are scored as "rxn" and are never rewarded). [V: `first_lick_grabber_operant_fx_0msv.m`: `op_win_open = 3.333; ITI_begin = 7; rxn_window = 0.5`; `iv.total_time_ = 17000`, `iv.rxnwin_ = 0`, `iv.exptype_ = 'op'` in 206/206 objects]

Definitions found:

| Definition | Where | Boundary | Excluded trials |
|---|---|---|---|
| Lick-based: `3.333 <= flick_s_wrtc < 7` | class code (`catBounds = [0,0.5,3.333,7,17]`, `getBinnedTimeseries` modes `custom`, `first-ntrials` with `[3.333,7]`) | Not consistent in the code: `>= 3.333` in the n-1 conditioning, strict `(3.333, 7)` in the block code, `(3.333, 7]` wrt cue in the 2017 grabber | Excluded trials have NaN `flick_s_wrtc` |
| Juice-based: `GLM.rewardedTrials` | `extractRewardedTrials`: trial numbers whose cue-to-next-cue interval contains a Juice event time from the CED file; flag `GLM.revisedRewardedTrials` | n/a | Not filtered by exclusions (the code says "using all rewarded trials regardless of exclusions") |
| Block window: `GLM.reward_windows_by_block` | cell of strings per block (class `CLASS_ZigZagTimeWindows` expects strings like `3.3-7s`) | per block | n/a |

"First lick" is the first lick with `cue_i <= t < cue_{i+1}` (MATLAB `histcounts(lick_s, cue_s)` + `unique`), then trials in `iv.exclusions_struct.Excluded_Trials` are dropped. `flick_s_wrtc` (length = number of cues) is NaN for trials with no lick or excluded; `fLick_trial_num` (1-based) lists trials that have a value; `firstLick_s` is aligned to `fLick_trial_num`, not to trials. [V: for Peter day 13, 304 of 791 trials contain a lick, 258 survive exclusion = `len(fLick_trial_num)`; `flick_s_wrtc[fLick_trial_num-1] == firstLick_s - cue_s[fLick_trial_num-1]` and a from-scratch first-lick computation from `lick_s`/`cue_s` matches for all 258.]

Agreement between the two definitions across the surveyed objects [V: 202 objects that have `rewardedTrials`]:
- Equal counts in 49 of 202; median `len(rewardedTrials) - n_lick_window` = +3; one session where the lick window count is larger by 1.
- In 196 of 202 objects every lick-window trial is also in `rewardedTrials`; in the other 6 (Lois1, Lois2, MJ1) exactly one lick-window trial is not (a first lick in the window but no juice event assigned to that trial). [V: counts of window trials whose number is in `rewardedTrials`]
- Small excess (a few trials): Peter day 13 has 73 juice trials vs 66 by lick window; the 7 extra trials all have NaN `flick_s_wrtc` and all appear in `iv.excludedtrials_`, so exclusions explain it. [V]
- Large excess (more than 25): 24 objects (MJ1, Lois1 and Lois2 days 2-6; Bob day 11 in both channels; two Jessie days). In MJ1 day 2, 520 of 600 trials are "rewarded". [V counts] These look like early or non-operant days where juice is delivered regardless of the lick window; the class code even contains a fallback "assuming this is pretraining" that sets `rewardedTrials = 1:numel(juice_s)`. [I: cause not confirmed; `FLAGG` field absent in all 206]
- Recommendation [I]: for "operant rewarded trial DF/F" use the lick window on `flick_s_wrtc`, optionally intersected with `rewardedTrials`; do not use `rewardedTrials` alone on early days.

## 3. Time base and indexing

- `GLM.gtimes` is the photometry time axis in seconds, uniform: `gtimes[0]` is a small offset (0.0003-0.0007 s in the files I looked at) and spacing is 0.001 s (`Plot.samples_per_ms = 1`). `rawF`, `gfit`, `gtimes` have equal length (11-40 million samples; 3 h sessions are normal). [V]
- All event times (`cue_s`, `lampOff_s`, `lick_s`, `firstLick_s`, `juice_s`) are seconds on the same clock as `gtimes`. [V: `gtimes[pos.cue-1]` is within 0.75 ms of `cue_s`]
- `GLM.pos.*` (`cue`, `lampOff`, `lick`, `flick`, `juice`, `baselineStart`) are 1-based MATLAB sample indices. For Peter day 13, `pos.cue - round((cue_s - gtimes[0]) / dt)` is 1 or 2, i.e. up to 2 samples of rounding. Prefer computing your own index: `i = round((t - gtimes[0]) / dt)`, 0-based. Note that `pos.flick` has one entry per `fLick_trial_num`, not per trial. [V]
- `GLM.juice` is an analog juice trace on the same samples; `juice_durations`, `juice_low/mid/high` are per trial (present in 181 of 206). [V]
- The accelerometer `GLM.X` / `Xtimes` is 2 samples per photometry sample (2 kHz); `gX = abs(bandpass(X))`. [V: lengths 2N vs N]

Window around events used by the lab:
- No single canonical analysis window exists in the class. `getBinnedTimeseries(ts, Mode, nbins, timePad, ...)` returns, for each bin, a mean over trials of `ts[cue - timePad : cue + total_time_ + timePad]` (CTA, cue-aligned, `total_time_ = 17000`) and `ts[firstLick - timePad : firstLick + timePad]` (LTA, lick-aligned). `timePad` is in samples and is chosen by the caller: default 30000 in `getBinnedTimeseries`, 15000 in the constructor for stim+photometry objects; the Peter day-13 object's stored `ts.Plot.CTA.xticks.s` spans -60 to +77 s, i.e. `timePad = 60000`. [V]
- The stored `ts.BinnedData.CTA/LTA` is a single "times" bin (1 bin) in the object checked, so it is not a per-trial rewarded-trial array; compute per-trial windows from `gfit` instead. [V: one object]
- Conventions in the downstream Python (sibling repo, not the class): DA covariate = mean `gfit` in the 0-0.5 s after first lick; also mean over [-0.5, -0.1] s before lick and [-0.4, 0] s before cue; and 50-ms bins over [cue-3, cue+20] and [lick-8, lick+1]. [V: `l26_extract_ramps.py`]
- Example result for sanity checking [V]: Peter day 13, 66 lick-window rewarded trials, mean `gfit` -0.0011 over the 0.5 s before first lick and +0.027 over the 0.5 s after.

## 4. HDF5 map (what h5py sees)

MCOS (MATLAB class object) layout in a v7.3 file:

- `/obj`: uint32 dataset (1, 6), attributes `MATLAB_class = 'CLASS_photometry_roadmapv1_4'`, `MATLAB_object_decode = 3`. Opaque; no data to read.
- `/#subsystem#/MCOS`: object-reference dataset (1, 20). Element 0 is a uint8 metadata blob (version 4); the saved object's property values are the following elements. Decoding the blob (string table of property names, then a per-object table of `(name_index, flag, value_index)`) gives the property order `Plot, iv, Mode, BinParams, BinnedData, SaveMode, Log, Stat, Stim, ChR2, gFitLP, GLM, ts, CtrlCh, video`, and property k is `MCOS[0, value_index + 2]`. [V: decoded, matches `/#refs#` contents]
- In the 5 files where I printed paths (Peter VLS and VLSred, Lois1, MJ1, Ezio) the groups were at `/#refs#/B` (GLM), `/#refs#/d` (iv), `/#refs#/c` (Plot), `/#refs#/E` (ts). These names are assigned by the writer, so do not hard-code them: match on keys (the sibling `l26_extract_ramps.py` and `statobj_labels.py` do this) or decode the property table. [V for 5 files / I for stability]

Fields (all inside the `GLM` group unless stated; MATLAB column-major arrays appear as `(1, N)`):

| Need | Path | Type / shape | Note |
|---|---|---|---|
| DF/F trace | `GLM/gfit` | float64 (1, N) | fractional; 1 NaN typical |
| style tag | `GLM/gfitMode` | uint16 chars | decode with `chr` |
| raw F | `GLM/rawF` (also `rawFchop`) | float64 (1, N) | volts; see section 7 |
| time axis | `GLM/gtimes` | float64 (1, N) | seconds |
| cue, lamp-off, lick times | `GLM/cue_s`, `lampOff_s`, `lick_s` | float64 (1, T) / (1, nLicks) | seconds |
| first lick wrt cue | `GLM/flick_s_wrtc` | float64 (1, T) | NaN = no lick or excluded |
| first-lick trials | `GLM/fLick_trial_num`, `firstLick_s` | float64 (1, nL) | 1-based trial numbers |
| juice-based rewarded | `GLM/rewardedTrials`, `juice_s` | float64 (1, R) | 1-based; missing in 4 of 206 (the X-only/Abs-X objects) |
| baseline index | `GLM/pos/baselineStart` | float64 (1, T+1) | 1-based samples; last entry = N |
| block windows | `GLM/reward_windows_by_block` | cell of refs to uint16 chars | all `'3.333-7s'` in the 202 that have it |
| accelerometer | `GLM/X`, `Xtimes`, `gX` | float64 (1, 2N) | 2 kHz |
| channel name | `iv/signalname` | cell (object ref) -> uint16 chars | `VLS`, `VLSred`, `X` |
| channel type | `iv/signaltype_` | uint16 chars | `photometry` or `accelerometer` |
| control channel | `iv/ctrl_signalname`, `iv/ctrl_signaltype_` | chars / cell | `X` / `accelerometer` in 206/206 |
| trial length, rxn window, type | `iv/total_time_`, `iv/rxnwin_`, `iv/exptype_` | float64 (1,1) / chars | 17000, 0, `op` in 206/206 |
| sampling rate | `Plot/samples_per_ms` | float64 (1,1) | 1.0 for 200 of 206 |
| excluded trials | `iv/excludedtrials_` (text), `iv/exclusions_struct` (group, not opened) | | text is free-form; do not copy into public output |

HDF5 gotchas [V]: MATLAB empty values are stored as a `(2,)` uint64 dataset with attribute `MATLAB_empty` (e.g. `stimTrials` reads as `[0, 1]` but is empty); logicals are uint8; chars are uint16 code points; cells are datasets of object references that must be dereferenced with `f[ref]`.

A plain `gfit.mat` sits in many session folders (v7.3, `gfit_struct/gfit_signal` and `gfit_struct/gfit_window`; the window is empty for multi-baseline). For Peter day 13 it is identical to the statObj `gfit` (`allclose`, max diff 0.0, same length). It is a much smaller file (38 MB vs 551 MB) and needs no MCOS handling, but carries no event times. [V: one session]

## 5. Python route

- h5py works for per-session statObjs (all 206 opened; metadata read about 0.5 s per file, reading `gfit` of 14.6 M samples about 1-2 s on the network share). `scipy.io.loadmat` cannot open v7.3; `mat73` was not installed and was not tried. A MATLAB R2024a install exists on this machine and could load the object if the class is on the path; not tested. [V / ?]
- What h5py cannot do: return a typed `CLASS_photometry_roadmapv1_4` object or run its methods. It does not matter here because all needed properties are plain structs and arrays (`/obj` itself holds nothing). [V]
- Combined-dataset objects (`V3x10_<signal>_statObj_Modetimes_*.mat`) have `GLM.isSingleSeshObj = 0` and only 5 `GLM` fields (`Mode, exclusionsTaken, flick_s_wrtc, gfitMode, isSingleSeshObj`): no `gfit`, `cue_s` or `rawF`. Rewarded-trial DF/F needs a per-session object. [V: 1 combined object opened; the 346 non-per-session names are mostly this pattern, [I] for the rest]

Minimal recipe, run on the Peter day-13 VLS object (66 rewarded trials, output shape (66, 4000)):

```python
import h5py, numpy as np

def find_glm(f):
    for r in f['#subsystem#/MCOS'][()].ravel():
        try: o = f[r]
        except Exception: continue
        if isinstance(o, h5py.Group) and {'cue_s', 'flick_s_wrtc', 'gfit', 'gtimes'} <= set(o.keys()):
            return o
    raise KeyError('no per-session GLM struct')

def rewarded_dff(path, pre=1.0, post=3.0, lo=3.333, hi=7.0):
    with h5py.File(path, 'r') as f:
        g = find_glm(f)
        t0 = float(g['gtimes'][0, 0]); dt = float(np.median(np.diff(g['gtimes'][0, :2000])))
        x = np.array(g['gfit']).ravel(); cue = np.array(g['cue_s']).ravel()
        fw = np.array(g['flick_s_wrtc']).ravel()
        trials = np.where((fw >= lo) & (fw < hi))[0]            # 0-based trial index
        npre, npost = int(round(pre / dt)), int(round(post / dt))
        rows = []
        for k in trials:
            i = int(round((cue[k] + fw[k] - t0) / dt))          # first-lick sample, 0-based
            if i - npre >= 0 and i + npost <= x.size:
                rows.append(x[i - npre:i + npost])
        return np.array(rows), trials + 1, dt
```

## 6. What varies by cohort, era or session

[V, from 206 per-session objects, `<mouse>_REVISED[_stimFixed]_<signal>_statObj.mat` at depth <= 5 under `Mouse Data/`, out of 552 files with "statObj" in the name]

- gfit style: 201 multi-baseline, 5 `Abs-X`. No 200-s-box objects among them.
- Object build year (`iv.date`, which is when the object was built, not when the mouse was recorded): 2024: 23, 2025: 61, 2026: 122.
- Sampling: 200 at 1 kHz; 4 X-only objects (Jessie) at 2 kHz; 2 objects (Hector) at about 20 Hz (sampling interval 50.1 ms), one of them labelled multi-baseline. [I] At 20 Hz the 5000-sample baseline window spans about 250 s, not 5 s, so its DF/F is not comparable with the 1 kHz objects. [V: counts; I: consequence]
- Mode: `iv.exptype_ = 'op'`, `iv.rxnwin_ = 0`, `total_time_ = 17000` in all 206 (one folder is named `op500` but its object says `rxnwin_ = 0`; not resolved). Hybrid/500-ms-window objects were not found in this set.
- Reward window: `reward_windows_by_block = '3.333-7s'` (single block) in all 202 that have it, so no window-change (zigzag) sessions are in this per-session set. The Peter folder has a separate `zigzag stim` folder that I did not open. [V / ?]
- Number of trials per session: 600 to 1636.
- Stim sessions: 19 objects carry `ChR2_s` / `ChR2values`, 6 carry `artifact_correction`; for stim sessions the class corrects the stim artifact locally before DF/F (`correct_stim_by_single_trial_step`, +/- 20 ms around stim start). Not examined further.
- Sensor (dLight vs rdLight1): not stored in the statObj. The lab's own table in this repo (`reference/session_notes_log.md`) gives dLight1.x for MJ1, Lois1, Lois2 (MJ1 flagged "user to confirm") and rdLight1 for Bob, Peter, OktoberfestB, Sprite. Keep it as a per-mouse covariate. [V that the note says so; ? whether correct]
- Raw F range differs strongly: in the sessions inspected `gfit` SD ranged 0.016 to 0.175, and MJ1 day 2 has negative raw F (median about -0.0014 V on VLS), which makes (F - F0)/F0 sign-inverted and ill-defined there. [V for these sessions; ? how common]

## 7. Channels and telling DA from control

- `iv.signalname` is the channel the object was built for: `VLS` (149 objects), `VLSred` (53), `X` (4). Bob and Peter, for example, have both a `VLS` and a `VLSred` per-session object (separate `rawF`/`gfit`, same trial structure). Both get the same DF/F method, so `gfit` is not always the DA signal. [V]
- Control channel: `iv.ctrl_signalname = 'X'` and `iv.ctrl_signaltype_ = 'accelerometer'` in 206/206 objects. This confirms from the files that `X` is an accelerometer (the norri notes call it "unverified from the files"). `gX = abs(bandpass(X))`. [V]
- tdTomato reference (`GLM.tdt`, the raw red channel; `addMoveControls` selects the CED channel whose name contains `red`): present in 1 of 206 objects (a `VLS` object). The sibling notes say `tdt` exists for VLS sessions, but on this share it is almost never stored; those objects live elsewhere or were built differently. [V count; ? where tdt lives otherwise]
- Which of `VLS` / `VLSred` is the DA indicator: not decidable from the statObj. The sibling analyses treat the `VLS` object as the DA trace even for rdLight1 mice (a red sensor), so the channel name is a site or rig label, not a colour. Do not infer colour from the name. [I from sibling docs; ? needs lab confirmation]
- No `EMG`, `ChR2_LED_monitor` or `MOVEtimes` in nearly all per-session objects here (0, 0 and 1 of 206 respectively). [V]

## 8. Unknowns

- Which of `VLS` / `VLSred` is DA, per mouse, and the rig channel mapping (needs the lab; maybe in the CED channel setup, not in the statObj).
- Whether any 200-s-box `gfit` objects exist on the share outside the pattern I surveyed (`*snpObj*`, `sObj`, other naming, `HMS SERVER FILES/`, depth > 5, the 346 other statObj-named files).
- Where `tdt` references are stored for the sessions that have them.
- Window-change and hybrid sessions: not in this set; `reward_windows_by_block` contents for multi-block sessions unseen.
- Prevalence of negative raw F, and whether the 20 Hz Hector objects are valid DF/F.
- Why 24 early-day sessions have `rewardedTrials` far above the lick-window count (inference only).
- MATLAB-side route (loading with the class) not tested.

## Method

- Code read from sibling repos by direct file reading (no edits). Line numbers refer to `CLASS_photometry_roadmapv1_4.m` in `photometry_roadmapv1_4/src/`.
- Share access: one `find -iname '*statObj*.mat'` with `-maxdepth 5` and timeouts on `Mouse Data/` (552 hits, 206 per-session pattern), then h5py (`python -I`, read mode) on all 206 for metadata and small fields (`survey`), and on Peter day 13 (VLS and VLSred) for full arrays. The MCOS property table was decoded from `/#subsystem#/MCOS[0]` (version 4 blob). Large arrays were read only for Peter day 13, MJ1 day 2, Hector day 11 and the Peter `gfit.mat`.
- No file on the share was written. No free-text from notebooks or the exclusion text was copied into this note.
