# opendaq-python / opendaq

Main project files.

Go to [openDAQ documentation](https://www.google.com "DAQ.py walkthrough") in ReadTheDocs to take a look at the functions included in them.



## Using opendaq-utils script for device calibration

This script provides useful tools for device testing and analog calibration.

Once the opendaq library has been istalled in the system, the script can be called directly from command promt: `$ opendaq-utils`.
The script needs some arguments and uses sub-commands to control the specific actions to be executed:

```sh
Usage: opendaq-utils [-h] [-p PORT] [-m METER] (info, calib, serial, test, set-voltage)

Optional arguments:
    -h, --help              show help message
    -p PORT, --port PORT    select serial port (default: /dev/ttyUSB0)
    -m METER, --meter METER Use a digital multimeter for fully automated test
    
Subcomands:
    info                    Show device information and versions
    calib                   Calibrate the devices
    test                    Test device calibration
    set-voltage             Set DAC voltage
    serial                  Read or write the serial number
    

[opendaq-utils calib] optional arguments:
    -l, --log               generate log file
    -r, --reset             reset the calibration values
    -d, --dac               Apply only DAC calibration and exit
    -f FILE, --file FILE    Select fiel source to load DAC parameters (default: calib.txt)
    -s, --show              Show calibration values
    -a, --auto              Use the external USB multimeter to perform automated calibration
    
[opendaq-utils test] optional arguments:
    -l, --log               generate log file
    -a, --auto              Use the external USB multimeter to perform automated calibration

[opendaq-utils set-voltage] optional arguments:
    -i, --interactive       Interactively ask for voltage values

[opendaq-utils serial] optional arguments:
    -w SERIAL, --write SERIAL   Write a new serial number
    
```

Please note that for calibrating the device, you will need a external multimeter. 
All the analog inputs will be calibrated, as well as the analog output (DAC). 
It will be necessary to connect all of them in between (tied one to each other) to execute the calibration and test scripts.