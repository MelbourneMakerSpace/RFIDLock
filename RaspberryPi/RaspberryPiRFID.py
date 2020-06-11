#!/usr/bin/python2

#############################################################################
# RaspberryPiRFID.py
#############################################################################
# This is meant to run on a raspberry pi or other
# computer that's connected to the internet and
# the front door lock. It queries a REST service
# by handing it the scanned in RFID reader and
# it will return 'true' if the key owner has
# made a payment in the last 45 days. It will return 'false' otherwise.
# The computer would then send the signal to the door lock actuator to
# open it if returned true or do nothing if false.  We could also have
# a display that would say ACCESS DENIED! or something as well...
# Josh Pritt
# ramgarden@gmail.com
# Feb 19, 2015
#############################################################################
__author__ = "Josh Pritt"
__copyright__ = "Copyright 2015, Melbourne Makerspace"
__credits__ = ["Josh Pritt"]
__license__ = "GPL"
__version__ = "3.2.0"
__maintainer__ = "Josh Pritt"
__email__ = "ramgarden@gmail.com"
__status__ = "In Production"

import serial
import re, sys, signal, os, time, datetime
import RPi.GPIO as GPIO
import RFIDValidator
import Adafruit_CharLCD as LCD
import smtplib
import os
import logging
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler


#make all log messages look like this:
#12/12/2010 11:46:36 AM is when this event was logged.
#logging.basicConfig(level='INFO',filename=logFile,
#                    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

logFile='/ram/RFIDLock.log'
log_formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024*1024,
                                 backupCount=2, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)
app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)
app_log.addHandler(my_handler)

DoorLockPin = 7  # connected to maglock
ExitButtonPin = 11  # connected to an unlock button inside

#PID file is used by Watchdog python script to restart this
# main script if it ever quits for any reason.
PIDFILE = "/ram/ACON.pid"

DEBUGMODE = False
WHITELISTFILENAME = "/ram/whitelist.txt"
WHITELISTUPDATEMINUTE = 0 #update at this minute every hour
UPDATEWAITTIME = 10 #number of seconds to wait between bad attempts to update the whitelist
whitelistUpdated = False
lastUpdateTime = time.time()

readyMessage = "Melbourne\nMakerspace"

BITRATE = 9600
GPIO.setmode(GPIO.BOARD)
GPIO.setup(DoorLockPin, GPIO.OUT)
GPIO.setup(ExitButtonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

LOCKED = GPIO.LOW
UNLOCKED = GPIO.HIGH

lcd = None
RED = [1.0,0.0,0.0]
GREEN = [0.0,1.0,0.0]
BLUE = [0.0,0.0,1.0]

defaultBackLightColor = BLUE

####################
#Email stuff
####################
FROM = "RFIDLockPi@melbournemakerspace.org"
TO = "admin@melbournemakerspace.org"
SUBJECT = "Invalid RFID scanned at the door"
MSGTEXT = "RFID serial number scanned: "

# Lock the door on boot
GPIO.output(DoorLockPin, LOCKED)


CARDS = []

def logMessage(message):
    #log a message to the debug log file
    try:
        if(DEBUGMODE):
            app_log.info(str(message))
    except Exception as ex:
        print("Error while writing to debug log file: " + str(ex.message))

def initLCDScreen():
    #set up the LCD object for writing messages, etc.
    try:
        global lcd
        logMessage("Initializing LCD screen.")
        lcd = LCD.Adafruit_CharLCDPlate()
        lcd.clear()
        lcd.message(readyMessage)
        lcd.set_backlight(1.0)
        logMessage("LCD screen initialized OK!")
    except Exception as ex:
        logMessage("Error trying to init LCD screen: " + str(ex.message))

def updateLocalWhitelist():
    # get the latest whitelist from the Seltzer DB and save to file
    try:
        global lastUpdateTime
        currentTime = time.time()
        if ((currentTime - lastUpdateTime) > UPDATEWAITTIME ):
            print "Updating the local whitelist..."
            logMessage('Updating local whitelist to file: ' + WHITELISTFILENAME)
            whitelist = RFIDValidator.getWhitelist()
            with open(WHITELISTFILENAME, "w+") as text_file:
                #text_file.write(str(whitelist))
                json.dump(whitelist,text_file)
            logMessage("Updated whitelist to file OK")
            print "Updated whitelist OK!"
            global whitelistUpdated
            whitelistUpdated = True
            lastUpdateTime = time.time()

    except Exception as ex:
        logMessage("Couldn't update the witelist." + str(ex.message))
        lastUpdateTime = time.time()

def readLocalWhitelist():
    """
    read the whitelist file and return an array of serial numbers
    :return: ARRAY
    """
    logMessage('Reading local whitelist file: ' + WHITELISTFILENAME)
    serialWhiteList = []
    try:
        with open(WHITELISTFILENAME, "r") as text_file:
            whitelistData = json.load(text_file)
            #pprint.pprint(whitelistData)
            for record in whitelistData:
                serialNum = str(record["serial"])
                if len(serialNum) > 5:
                    serialWhiteList.append(serialNum)
    except Exception:
        logMessage('Whitelist not found or empty or badly formatted JSON.')
    logMessage('Read whitelist file OK.')
    return serialWhiteList

def writeLCDMessage(message, redVal=0.0, greenVal=0.0, blueVal=1.0):
    try:
        global lcd
        lcd.clear()
        lcd.message(message)
        lcd.set_color(redVal, greenVal, blueVal)
    except Exception as ex:
        logMessage("Error writing LCD message: " + str(ex.message))

def signal_handler(signal, frame):
    print "Closing RFID Door Lock Script"
    global pipe
    logMessage("======Closing ACON RFID Door Lock Script.======")
    GPIO.output(DoorLockPin, UNLOCKED)  # Unlock the door on program exit
    GPIO.cleanup()
    os.close(pipe)
    ser.close()
    sys.exit(0)


def unlock_door(duration):
    print "Unlocking door for %d seconds" % duration
    logMessage("Unlocking door for %d seconds." % duration)
    GPIO.output(DoorLockPin, UNLOCKED)
    time.sleep(duration)
    print "Locking the door"
    logMessage("Locking the door.")
    GPIO.output(DoorLockPin, LOCKED)
    writeLCDMessage(readyMessage)

def sendEmail(rfidSerial):
    logMessage('Sending email to ' + TO)
    try:
        #Next, log in to the server
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        #This will need to change if the password ever changes on our gmail account!!!
        server.login("melbournemakerspace@gmail.com", "secret!")

        bodyText = MSGTEXT + rfidSerial

        #Send the mail
        msg = "\r\n".join([
          "From: " + FROM,
          "To: " + TO,
          "Subject: " + SUBJECT,
          "",
          bodyText
          ])

        server.sendmail(FROM, TO, msg)
        logMessage('Email sent OK.')
    except Exception as ex:
        logMessage("Error trying to send email: " + str(ex.message))

def touch(fname):
    try:
        open(fname, 'a').close()
        os.utime(fname, None)
    except Exception as ex:
        logMessage("Error while trying to touch " + PIDFILE + ": " + str(ex.message))

def touchPipe(pipe):
    try:
        os.write(pipe,str(time.time()))
    except Exception as ex:
        logMessage("Error while touching pipe: " + str(ex.message))

def writePidFile():
    try:
        pid = os.getpid()
        with open(PIDFILE, "w+") as text_file:
            text_file.write(str(pid))
    except Exception as ex:
        logMessage("Error while writing PID file " + PIDFILE + ": " + str(ex.message))

def updateAccessLog(rfid, access, reason):
    try:
        RFIDValidator.logDoorAccess(rfid, access, reason)
        logMessage("logged door access OK!")
    except Exception as ex:
        logMessage("Error while updating access log: " + str(ex.message))

if __name__ == '__main__':
    logMessage("======Starting ACON RFID Lock Script======")
    buffer = ''
    pipe = os.pipe()
    #ser = serial.Serial('/dev/ttyUSB0', BITRATE, timeout=0) #USB serial
    ser = serial.Serial('/dev/ttyAMA0', BITRATE, timeout=0) #GPIO UART pins
    rfidPattern = re.compile(b'[\W_]+')
    signal.signal(signal.SIGINT, signal_handler)

    initLCDScreen()

    #write this process's ID to the PIDFILE so our watchdog script
    # can check if this script is still running or crashed.
    writePidFile()

    rfid = ""
    access = 0
    reason = ""
    rfidWasSwiped = False

    while True:
        # Read data from RFID reader
        #print 'listening to serial port...'
        buffer = buffer + ser.read(ser.inWaiting())
        if '\n' in buffer:
            lines = buffer.split('\n')
            last_received = lines[-2]
            match = rfidPattern.sub('', last_received)

            # check if the RFID is stored in our local whitelist
            rfid = match
            access = 0
            reason = ""
            rfidWasSwiped = False
            if match:
                print match
                logMessage('RFID card scanned: ' + match)
                rfidWasSwiped = True
                #writeLCDMessage(match)
                writeLCDMessage('checking...')
                CARDS = readLocalWhitelist()
                if match in CARDS:
                    print 'card authorized'
                    logMessage('Card authorized via whitelist.')
                    writeLCDMessage('Whitelist OK!\nAccess Granted!',0.0,1.0,0.0)
                    unlock_door(10)
                    access = 1
                else:
                    #not in the local whitelist, check REST web service
                    jsonResponse = RFIDValidator.validate(match)
                    print 'validate() json response: ' + str(jsonResponse)
                    jsonString = jsonResponse[0]
                    print 'validate() json string: ' + jsonString
                    if (jsonString == "True"):
                        print 'card authorized with REST service'
                        logMessage('Card authorized via REST service.')
                        writeLCDMessage('Auth w/ REST\nAccess Granted!',0.0,1.0,0.0)
                        unlock_door(10)
                        access = 1
                    else:
                        print 'unauthorized card'
                        logMessage('RFID serial not found or member payments are due. Access Denied.')
                        writeLCDMessage('Unauthorized.\nAccess Denied!',1.0,0.0,0.0)
                        sendEmail(match + "\nPossible reason: " + jsonString)
                        time.sleep(5)
                        writeLCDMessage(readyMessage)
                        access = 0
                        reason = jsonString

            # Clear buffer
            buffer = ''
            lines = ''

        # Update the access log if we scanned a card
        if rfidWasSwiped:
            updateAccessLog(rfid, access, reason)
            rfidWasSwiped = False

        # Listen for Exit Button input
        if not GPIO.input(ExitButtonPin):
            print "Exit button pressed."
            logMessage("Exit button pressed.")
            writeLCDMessage('Exit button \npressed.',1.0,1.0,1.0)
            unlock_door(5)

        # Update the whitelist every hour (at 00 minutes)
        if datetime.now().minute == WHITELISTUPDATEMINUTE:
            logMessage("time to update the whitelist!")
            if whitelistUpdated == False:
                updateLocalWhitelist()

        #reset the whitelist update flag after a minute so it will
        # try again the next hour
        if datetime.now().minute == WHITELISTUPDATEMINUTE + 1:
            whitelistUpdated = False
                
        # wait a bit before looping again
        time.sleep(0.1)
