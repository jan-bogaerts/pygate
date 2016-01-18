#!/bin/sh

#globally available parameters
#INSTALL_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "install to: $MY_PATH"

##################################

#pyGate
#######

#install requirements
pip install -r requirements.txt
# add to crontab
command="$MY_PATH/launcher.sh"
job="@reboot $command  &"
cat <(fgrep -i -v "$command" <(crontab -l)) <(echo "$job") | crontab -

##################################


# fogdevice
############

# install mosquitto
# apt-get install mosquitto
# plugin's autolauncher
chmod "$MY_PATH"/FogDevices/launcher.sh 775
# add to crontab
command="$MY_PATH/FogDevices/launcher.sh"
job="@reboot $command  &"
echo "auto start for fog device: $MY_PATH"
#cat <(fgrep -i -v "$command" <(crontab -l)) <(echo "$job") | crontab -


##################################

# zwave
#######
apt-get install -y git make
git clone https://github.com/OpenZWave/python-openzwave
cd python-openzwave
sudo apt-get update
sudo make repo-deps
make update
make build
make install
cd ..