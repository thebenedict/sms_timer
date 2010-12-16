#!/usr/bin/env python

import pygsm
import urllib
import time
from datetime import datetime

#message format: sent_from*sent_to*date_sent*time_sent

MTN_NUMBER = "+256789906279"
AIRTEL_NUMBER = "+256758311742"
#SEND_INTERVAL must be an even number
SEND_INTERVAL = 3600
MTN_PORT = "/dev/ttyUSB1"
AIRTEL_PORT = "/dev/ttyUSB0"

def logModems():
    mtnModem = pygsm.GsmModem(port=MTN_PORT,baudrate="115200")
    airtelModem = pygsm.GsmModem(port=AIRTEL_PORT,baudrate="115200")
    timer = 0

    while True:
        mtnMsg = mtnModem.next_message()
        airtelMsg = airtelModem.next_message()

        if mtnMsg is not None:
            msg_data = mtnMsg.text.split('*')
            logfile = open('smslog.csv', 'a')
            if len(msg_data) is 4:
                logfile.write("\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"" %(msg_data[0], msg_data[1], msg_data[2], msg_data[3], datetime.now().date(), datetime.now().time()) + "\n")
            else:
                logfile.write("\"Malformed message from MTN modem\",\"%s\",\"%s\"" % (mtnMsg.text, datetime.now()) + "\n")
            logfile.close()

        if airtelMsg is not None:
            msg_data = airtelMsg.text.split('*')
            logfile = open('smslog.csv', 'a')
            if len(msg_data) is 4:
                logfile.write("\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"" %(msg_data[0], msg_data[1], msg_data[2], msg_data[3], datetime.now().date(), datetime.now().time()) + "\n")
            else:
                logfile.write("\"Malformed message from Airtel modem\",\"%s\",\"%s\"" % (airtelMsg.text, datetime.now()) + "\n")
            logfile.close()

        if timer == SEND_INTERVAL:
            print "Timer is %s, sending from modems" % timer
            sendFromModems("Airtel",airtelModem)
            sendFromModems("MTN",mtnModem)
            timer = 0
        else: time.sleep(2)
        timer += 2

'''sends messaeges using the modems'''
def sendFromModems(origin_network,modem):
        print "in sendFromModems, origin_network is %s" % origin_network 
        if origin_network is 'MTN':
            print "Sending MTN->MTN"
            modem.send_sms(MTN_NUMBER,"MTN*MTN*%s*%s" % (datetime.now().date(), datetime.now().time()))
            print "Sending MTN->Airtel"
            modem.send_sms(AIRTEL_NUMBER, "MTN*Airtel*%s*%s" % (datetime.now().date(), datetime.now().time()))
        if origin_network is 'Airtel':
            print "Sending Airtel->Airtel"
            modem.send_sms(AIRTEL_NUMBER,"Airtel*Airtel*%s*%s" % (datetime.now().date(), datetime.now().time()))
            print "Sending Airtel->MTN"
            modem.send_sms(MTN_NUMBER, "Airtel*MTN*%s*%s" % (datetime.now().date(), datetime.now().time()))

if __name__ == "__main__":
    logModems()
