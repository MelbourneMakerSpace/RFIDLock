#############################################################################
# RFIDValidator.py
#############################################################################
# This is meant to run on a raspberry pi or other
# computer that's connected to the internet and
# the front door lock. It queries a REST service
# by handing it the scanned in RFID reader and
# it will return 'true' if the key owner owes less than 3 times their monthly
# plan price. It will return 'false' otherwise.
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

import requests
import json
import pprint

#set this to the URL where you've installed Seltzer.
#it's just the server so don't include the /crm/... part.
#www.yourwebsite.com for example
SELTZERSERVER = "yourSeltzerServer"

def validate(rfid):
    """
    Validates a given RFID using a REST web service that takes the RFID as input
    and returns a simple 'true' if the key owner has paid their dues in the past
    45 days or 'false' otherwise
    :param rfid: the RFID read from the reader
    :return: True if RFID owner is OK, False otherwise
    """

    # pass the RFID to the REST service
    url = 'http://' + SELTZERSERVER + '/crm/api/query.php?action=doorLockCheck&rfid=' + rfid
    payload = ''
    response = requests.get(url, data=payload, timeout=30.0)

    # the response.content should be 'true' or 'false'
    #pprint.pprint(response.content)
    return json.loads(response.content)

def getWhitelist():
    """
    Gets the most recent whitelist of valid RFID card serial numbers based on member
    payments and up to date accounts.  If fields param is blank it will return all
    the fields from the database. Otherwise pass in a comma separated list of field
    names to return.
    :param fields:
    :return:
    """
    url = 'http://' + SELTZERSERVER + '/crm/api/query.php?action=getRFIDWhitelist'
    payload = ''
    response = requests.get(url, data=payload, timeout=30.0)

    whitelist = json.loads(response.content)
    #pprint.pprint(whitelist)

    return whitelist

