pyGate
======
A gateway application that connects different types of devices (physical or virtual) to the [AllThingsTalk](https://maker.smartliving.io/) platform.   
This is the main app which only sets up the environment to manage all the features.  
Funcionallity itself is provided through various plugins which have to be installed individually.

###supported plugins
The following plugins are currently supported: 

- [zwave](https://github.com/allthingstalk/pygate-zwave): connect devices using the zwave communication protocol
- [arpscanner](https://github.com/allthingstalk/pygate-arpscanner): detect the presence of network devices without installling anything on the devices. Usage example: track user presence through the presence of your mobile phone
- [associations](https://github.com/allthingstalk/pygate-associations): create associations between devices, accross communication protocols
- [fogdevices](https://github.com/allthingstalk/pygate-fogdevices) (beta): locally connect wifi enabled devices that use the AllThingsTalk api
- [groups](https://github.com/allthingstalk/pygate-groups): group assets together so that they can be used as a single asset
- [main](https://github.com/allthingstalk/pygate-main): some core functionality for the gateway, like refresh the definition of all devices.
- [mbus](https://github.com/allthingstalk/pygate-mbus): connect devices using the m-bus communication protocol
- [otu](https://github.com/allthingstalk/pygate-otu): over the air upgrades
- [scenes](https://github.com/allthingstalk/pygate-scenes): creates scenes accross communication protocols, that can be activated using an asset.
- [virtual-devices](https://github.com/allthingstalk/pygate-virtual-devices): create devices from publicly available web api's such as virtual weather stations
- [watchdog](https://github.com/allthingstalk/pygate-watchdog): make certain that the gateway reconnects after something went wrong with the network connection.
- [xbee](https://github.com/allthingstalk/pygate-xbee) (beta): connect devices using the xbee communication protocol



### Installation
- downoad the application
- install the requirements (pip install -r requirements.txt)
- update pyGate\launcher.sh so that it points to the correct path.
- to start the application automatically, you can use launcher.sh and start it from the cron:
	- edit the cron: `sudo crontab -e`
	- at the bottom, add the line: `@reboot {path_to_launcher.sh}\launcher.sh` 

### dependencies
The following dependencies are automatically installed from requirements.txt 

- [att-iot-gateway](https://github.com/allthingstalk/rpi-python-gateway-client)
- [pygate-core](https://github.com/allthingstalk/pygate-core)
- paho-mqtt
- PyYAML




