echo 'Enter brandeis.edu username'
read username
mount_path=/media/files_brandeis_drive
# Check that the mount path exists
# If it does not exist, create it
if [ ! -d "$mount_path" ]; then
    echo "$mount_path does not exist. Creating it now."
    sudo mkdir $mount_path
else
    echo "$mount_path already exists."
fi
sudo mount -t cifs //files.brandeis.edu/katz-lab $mount_path -o username=$username,domain=brandeis.edu,vers=3.0,uid=1000,gid=1000
