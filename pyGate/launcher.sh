#!/bin/sh
# launcher.sh
# navigate to home directory, then to this directory, then execute python script, then back home


LOGFILE=/root/pygate/logs/restart.log

writelog() {
  now=`date`
  echo "$now $*" >> $LOGFILE
}


while true ; do
  #check for network connectivity
  wget -q --timeout=99 --spider http://google.com  #--tries=10  tries does not appear to be supported on all platforms (fifthplay gateway)
  sleep 1
  if [ $? -eq 0 ]; then
        ntpdate -b -s -u pool.ntp.org   # update the time, bb has not external clock
        cd /root/pygate/pyGate
        # pause a little, if we don't then the zwave stack crashes cause it's started too fast. With the delay, everything is ok.
        sleep 1
        writelog "Starting"
        sudo python pyGate.py
        writelog "Exited with status $?"
  else
        writelog "No network connection, retrying..."
  fi
done
cd /



