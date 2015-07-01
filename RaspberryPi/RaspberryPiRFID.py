#!/usr/bin/python2

#############################################################################
# RaspberryPiRFID.py
#############################################################################
# This is meant to run on a raspberry pi that's connected to the internet and
# the front door magnet lock. It queries a REST service
# by handing it the scanned in RFID card reader and
# it will return 'true' if the key owner owes less than 3 months worth of
# their monthly payment. It will return 'false' otherwise.
# The computer would then send the signal to the door lock actuator to
# open it if returned true or do nothing if false.  It also has
# an LCD backlit display that would say ACCESS GRANTED or DENIED!
# Josh Pritt
# ramgarden@gmail.com
# Feb 19, 2015
#############################################################################
__author__ = "Josh Pritt"
__copyright__ = "Copyright 2015, Melbourne Makerspace"
__credits__ = ["Josh Pritt"]
__license__ = "GPL"
__version__ = "2.0.0"
__maintainer__ = "Josh Pritt"
__email__ = "ramgarden@gmail.com"
__status__ = "User Validation"

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

#this is the master log file that shows which card scanned in
# at what time/date and other events / errors.
logFile='/home/pi/RFIDLock.log'

#make all log messages look like this:
#12/12/2010 11:46:36 AM is when this event was logged.
#logging.basicConfig(level='INFO',filename=logFile,
#                    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

log_formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024*1024,
                                 backupCount=2, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)
app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)
app_log.addHandler(my_handler)

#we will be using GPIO.BOARD mode so these are the physical pin numbers,
# NOT the GPIO## pin numbers!
DoorLockPin = 7  # connected to maglock
ExitButtonPin = 11  # connected to an unlock button inside

GPIO.setmode(GPIO.BOARD)
GPIO.setup(DoorLockPin, GPIO.OUT)
GPIO.setup(ExitButtonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

LOCKED = GPIO.LOW
UNLOCKED = GPIO.HIGH

#comment out the device you are not using.
#in this case we have our RFID reader hooked to the 
#GPIO UART pins
SERIALDEVICE = '/dev/ttyAMA0' #GPIO UART pins
#SERIALDEVICE = '/dev/ttyUSB0' #USB serial

#the whitelist file is updated once a day with all the members
# who have paid their dues.  This file is checked first when a
# card is swiped for very fast access without having to wait
# for the REST query. If not found in whitelist it will then
# do the REST query in case they were just added to the DB. 
WHITELISTFILENAME = "whitelist.txt"
WHITELISTUPDATEHOUR = 1 #update at this hour every day (24 hour clock)
UPDATEWAITTIME = 600 #number of seconds to wait between bad attempts to update the whitelist
whitelistUpdatedToday = False
lastUpdateTime = time.time()

#this message is shown on the LCD screen while it waits for an RFID card swipe.
readyMessage = "Melbourne\nMakerspace"

#bit rate of the RFID reader's serial connection. Ours is 9600.
BITRATE = 9600

#set up the LCD screen variables.
lcd = None
RED = [1.0,0.0,0.0]
GREEN = [0.0,1.0,0.0]
BLUE = [0.0,0.0,1.0]

defaultBackLightColor = BLUE

####################
#Email stuff for when bad cards or new cards are scanned
# it will email you!
####################
SMTPSERVER = "smtp.gmail.com:587"
USERNAME = "melbournemakerspace@gmail.com"
PASSWORD = "secret!"
FROM = "RFIDLockPi@melbournemakerspace.org"
TO = "admin@melbournemakerspace.org"
SUBJECT = "Invalid RFID scanned at the door"
MSGTEXT = "RFID serial number scanned: "

# Lock the door on boot
GPIO.output(DoorLockPin, LOCKED)

#this PID file is used by the watchdog script to make sure
# this script is restarted if it ever quits.
PIDFILE = "/home/pi/ACON.pid"

#list of valid rfid cards.
CARDS = []

def initLCDScreen():
    #set up the LCD object for writing messages, etc.
    try:
        global lcd
        app_log.info("Initializing LCD screen.")
        lcd = LCD.Adafruit_CharLCDPlate()
        lcd.clear()
        lcd.message(readyMessage)
        lcd.set_backlight(1.0)
        app_log.info("LCD screen initialized OK!")
    except Exception as ex:
        app_log.info("Error trying to init LCD screen: " + str(ex.message))

def updateLocalWhitelist():
    # get the latest whitelist from the Seltzer DB and save to file
    try:
        global lastUpdateTime
        currentTime = time.time()
        if ((currentTime - lastUpdateTime) > UPDATEWAITTIME ):
            print "Updating the local whitelist..."
            app_log.info('Updating local whitelist to file: ' + WHITELISTFILENAME)
            whitelist = RFIDValidator.getWhitelist()
            with open(WHITELISTFILENAME, "w+") as text_file:
                #text_file.write(str(whitelist))
                json.dump(whitelist,text_file)
            app_log.info("Updated whitelist to file OK")
            print "Updated whitelist OK!"
            global whitelistUpdatedToday
            whitelistUpdatedToday = True
            lastUpdateTime = time.time()

    except Exception as ex:
        app_log.info("Couldn't update the witelist." + str(ex.message))
        lastUpdateTime = time.time()

def readLocalWhitelist():
    """
    read the whitelist file and return an array of serial numbers
    :return: ARRAY
    """
    app_log.info('Reading local whitelist file: ' + WHITELISTFILENAME)
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
        app_log.info('Whitelist not found or empty or badly formatted JSON.')
    #app_log.info('Read whitelist file OK. Got whitelist: ' + str(serialWhiteList))
    app_log.info('Read whitelist file OK.')
    return serialWhiteList

def writeLCDMessage(message, redVal=0.0, greenVal=0.0, blueVal=1.0):
    try:
        global lcd
        lcd.clear()
        lcd.message(message)
        lcd.set_color(redVal, greenVal, blueVal)
    except Exception as ex:
        app_log.info("Error writing LCD message: " + str(ex.message))

def signal_handler(signal, frame):
    print "Closing RFID Door Lock Script"
    global pipe
    app_log.info("======Closing ACON RFID Door Lock Script.======")
    GPIO.output(DoorLockPin, UNLOCKED)  # Unlock the door on program exit
    GPIO.cleanup()
    os.close(pipe)
    ser.close()
    sys.exit(0)

def unlock_door(duration):
    print "Unlocking door for %d seconds" % duration
    app_log.info("Unlocking door for %d seconds." % duration)
    GPIO.output(DoorLockPin, UNLOCKED)
    time.sleep(duration)
    print "Locking the door"
    app_log.info("Locking the door.")
    GPIO.output(DoorLockPin, LOCKED)
    writeLCDMessage(readyMessage)

def sendEmail(rfidSerial):
    app_log.info('Sending email to ' + TO)
    try:
		global SMTPSERVER
		global USERNAME
		global PASSWORD
		#Next, log in to the server
        server = smtplib.SMTP(SMTPSERVER)
        server.ehlo()
        server.starttls()
        #This will need to change if the password ever changes on our gmail account!!!
        server.login(USERNAME, PASSWORD)

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
        app_log.info('Email sent OK.')
    except Exception as ex:
        app_log.info("Error trying to send email: " + str(ex.message))

def touch(fname):
    try:
        open(fname, 'a').close()
        os.utime(fname, None)
    except Exception as ex:
        app_log.info("Error while trying to touch " + PIDFILE + ": " + str(ex.message))

def touchPipe(pipe):
    try:
        os.write(pipe,str(time.time()))
    except Exception as ex:
        app_log.info("Error while touching pipe: " + str(ex.message))

def writePidFile():
    try:
        pid = os.getpid()
        with open(PIDFILE, "w+") as text_file:
            text_file.write(str(pid))
    except Exception as ex:
        app_log.info("Error while writing PID file " + PIDFILE + ": " + str(ex.message))

if __name__ == '__main__':
    app_log.info("======Starting ACON RFID Lock Script======")
    buffer = ''
    pipe = os.pipe()
	global SERIALDEVICE
    ser = serial.Serial(SERIALDEVICE, BITRATE, timeout=0)
    rfidPattern = re.compile(b'[\W_]+')
    signal.signal(signal.SIGINT, signal_handler)

    initLCDScreen()

    #write this process's ID to the PIDFILE so our watchdog script
    # can check if this script is still running or crashed.
    writePidFile()

    while True:
        # Read data from RFID reader
        #print 'listening to serial port...'
        buffer = buffer + ser.read(ser.inWaiting())
        if '\n' in buffer:
            lines = buffer.split('\n')
            last_received = lines[-2]
            match = rfidPattern.sub('', last_received)

            # check if the RFID is stored in our local whitelist
            if match:
                print match
                app_log.info('RFID card scanned: ' + match)
                #writeLCDMessage(match)
                writeLCDMessage('checking...')
                CARDS = readLocalWhitelist()
                if match in CARDS:
                    print 'card authorized'
                    app_log.info('Card authorized via whitelist.')
                    writeLCDMessage('Whitelist OK!\nAccess Granted!',0.0,1.0,0.0)
                    unlock_door(10)
                else:
                    #not in the local whitelist, check REST web service
                    jsonResponse = RFIDValidator.validate(match)
                    print 'validate() json response: ' + str(jsonResponse)
                    jsonString = jsonResponse[0]
                    print 'validate() json string: ' + jsonString
                    if (jsonString == "True"):
                        print 'card authorized with REST service'
                        app_log.info('Card authorized via REST service.')
                        writeLCDMessage('Auth w/ REST\nAccess Granted!',0.0,1.0,0.0)
                        unlock_door(10)
                    else:
                        print 'unauthorized card'
                        app_log.info('RFID serial not found or member payments are due. Access Denied.')
                        writeLCDMessage('Unauthorized.\nAccess Denied!',1.0,0.0,0.0)
                        sendEmail(match + "\nPossible reason: " + jsonString)
                        time.sleep(5)
                        writeLCDMessage(readyMessage)

            # Clear buffer
            buffer = ''
            lines = ''

        # Listen for Exit Button input
        if not GPIO.input(ExitButtonPin):
            print "Exit button pressed."
            app_log.info("Exit button pressed.")
            writeLCDMessage('Exit button \npressed.',1.0,1.0,1.0)
            unlock_door(5)

        # Update the whitelist every night at 1 am
        if datetime.now().hour == WHITELISTUPDATEHOUR:
            if whitelistUpdatedToday == False:
                updateLocalWhitelist()

        # After whitelist update hour, set the flag back.
        # This keeps it from updating constantly for the whole hour!
        if datetime.now().hour  == (WHITELISTUPDATEHOUR + 1):
            whitelistUpdatedToday = False

        # wait a bit before looping again
        time.sleep(0.1)
