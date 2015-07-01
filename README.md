RFIDLock
========

An RFID door lock using a Raspberry Pi, ID-20, JS-1124, AdaFruit LCD screen, a push button, and a magnet lock.

See the wiki project page here:
https://wiki.melbournemakerspace.org/projects/RFIDDoorLock

This code is broken into two parts to make the access control system (ACON) work with Seltzer.
https://github.com/elplatt/seltzer

The python files stored in the RaspberryPi folder go in the /usr/home/pi folder.
The Seltzer PHP files need to be uploaded via FTP to the same web server where you've installed Seltzer.
It should line up where this "api" folder is under the "crm" folder so that the URL looks like "http://yourserver.com/crm/api/query.php....."

If you don't want it to interface with Seltzer you could take out the part that updates the whitelist file and just populate the file manually with the valid users and their RFID serial numbers.  The whitelist file should have a JSON array like this:
[{"firstName":"Josh","lastName":"Pritt","serial":"8045AB453449"},{"firstName":"Tony","lastName":"Bellomo","serial":"6554557774BC"},{"firstName":"Arlo","lastName":"Del Rosario","serial":"4944D8938D11"}]

There are several variables to set in all three Python files in the RaspberryPi folder.  They are all at the top and usually are ALL CAPS.  Change these values if you need to such as the USERNAME and PASSWORD for your email server.

You need to run a few commands on the Raspberry Pi command line (terminal) to get it to run the Python scripts correctly.
sudo apt-get install python-dev python-rpi.gpio

Then get the AdaFruit LCD screen library and setup the I2C pins on the GPIO by following these directions:
https://learn.adafruit.com/adafruit-16x2-character-lcd-plus-keypad-for-raspberry-pi/usage

Finally, set up the RPi so that it runs the main python script as soon as it boots up:
sudo crontab -e 

add this to the end of the cron:
@reboot python /home/pi/RaspberryPiRFID.py &  

then save and exit and reboot the pi.

