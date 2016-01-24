#!/bin/sh

#globally available parameters
INSTALL_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "install to: $INSTALL_PATH"

##################################

#pyGate
#######

#install requirements
pip install -r requirements.txt
# add to crontab
command="$INSTALL_PATH/launcher.sh"
job="@reboot $command  &"
cat <(fgrep -i -v "$command" <(crontab -l)) <(echo "$job") | crontab -

##################################


# fogdevice
############

# install mosquitto
wget http://repo.mosquitto.org/debian/mosquitto-repo.gpg.key
sudo apt-key add mosquitto-repo.gpg.key
cd /etc/apt/sources.list.d/
sudo wget http://repo.mosquitto.org/debian/mosquitto-wheezy.list
sudo apt-get update
cd $INSTALL_PATH
apt-get install mosquitto
#users & pwds
sudo mosquitto_passwd -b /etc/mosquitto/accesslist.txt pyGate abc123
sudo mosquitto_passwd -b /etc/mosquitto/accesslist.txt client abc123
sudo sh -c 'zcat $INSTALL_PATH/FogDevices/mosquitto.conf > /etc/mosquitto/conf.d/mosquitto.conf'
sudo service mosquitto restart
# plugin's autolauncher
chmod "$INSTALL_PATH"/FogDevices/launcher.sh 775
# add to crontab
command="$INSTALL_PATH/FogDevices/launcher.sh"
job="@reboot $command  &"
echo "auto start for fog device: $INSTALL_PATH"
cat <(fgrep -i -v "$command" <(crontab -l)) <(echo "$job") | crontab -


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