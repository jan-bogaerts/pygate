#!/bin/sh

# fogdevice
############
# install mosquitto
sudo apt-get install mosquitto
# plugin's autolauncher
chmod /root/pygate/pyGate/FogDevices/launcher.sh 775


##################################


#pyGate
#######
# add to crontab
job="@reboot $command  &"

command="/root/pygate/pyGate/FogDevices/launcher.sh"
cat <(fgrep -i -v "$command" <(crontab -l)) <(echo "$job") | crontab -

command="/root/pygate/pyGate/launcher.sh"
cat <(fgrep -i -v "$command" <(crontab -l)) <(echo "$job") | crontab -