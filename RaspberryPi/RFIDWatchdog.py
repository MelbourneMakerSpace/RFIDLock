#!/usr/bin/python2

#############################################################################
# RFIDWatchdog.py
#############################################################################
# This script is meant to run at boot time. It checks the last modified
# date/time on the configured file.  If that file hasn't been modified
# within the configured time interval (usually 2 minutes) then it will
# execute the configured command (usually to restart the RFID lock script).
# Josh Pritt
# ramgarden@gmail.com
# April 4, 2015
#############################################################################
__author__ = "Josh Pritt"
__copyright__ = "Copyright 2015, Melbourne Makerspace"
__credits__ = ["Josh Pritt"]
__license__ = "GPL"
__version__ = "2.0.0"
__maintainer__ = "Josh Pritt"
__email__ = "ramgarden@gmail.com"
__status__ = "User Validation"

import os
import time

#this PIDFILE must match the one set in the main 
#RaspberryPiRFID.py script!
PIDFILE = "/home/pi/ACON.pid"
#this is the command to run the main script.
#this script and the main script should all be in
#the same folder.
COMMAND = "python /home/pi/RaspberryPiRFID.py &"
CHECKWAITTIME = 10 #check every X seconds

#since this script is run at boot time with the main
#door lock script, wait a good while for the main
#script to get started touching the PIDFILE.
time.sleep(CHECKWAITTIME * 3)

pid = None

def readPidFile():
    global pid
    with open(PIDFILE,'r') as pidfile:
        pid = pidfile.read()
    print('pid = ' + str(pid))

readPidFile()

while True:
    time.sleep(CHECKWAITTIME)

    #if the process isn't running then the script must have stopped
    # running for whatever reason.  Run the configured
    # command to restart it.

    if(not os.path.exists("/proc/" + str(pid))):
        #no longer running!
        print "file not running! Running command: " + COMMAND
        os.system(COMMAND)
        #wait a while for it to start, then get the new PID
        time.sleep(CHECKWAITTIME)
        readPidFile()

