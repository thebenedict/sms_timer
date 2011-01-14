#!/usr/bin/env python

import pygsm
import urllib
import time
from datetime import datetime, timedelta

#message format: sent_from*sent_to*sent_count*date_sent*time_sent*'signal
#                strength of sending modem at time of send'


##########
# Config #
##########

modem_config = [
    #{'name':      'Vodacom TZ', \
    # 'number':    '+255767199999', \
    # 'port':      '/dev/ttyUSB0', \
    # 'baudrate': '115200', \
    # 'send_to_self': 1}, \
    #{'name':      'Tigo TZ B', \
    # 'number':    '+255717435798', \
    # 'port':      '/dev/ttyUSB0', \
    # 'baudrate': '115200', \
    # 'send_to_self': 1},
    {'name':      'Airtel TZ', \
     'number':    '+255686037495', \
     'port':      '/dev/ttyUSB0', \
     'baudrate': '115200', \
     'send_to_self': 1},
    {'name':      'Zantel TZ', \
     'number':    '+255774769736', \
     'port':      '/dev/ttyUSB1', \
     'baudrate': '115200', \
     'send_to_self': 1}
    #...etc if you have >2 modems. You lucky fool.
]
    
#SEND_INTERVAL must be an even number
SEND_INTERVAL = 900

#Just for the startup check
ADMIN_NUMBER = '+255767199999'

##############
# End Config #
##############

sent_message_counter = 0
messages_to_send = []

def logModems():
    networks = []
    for m in modem_config:
        print "Starting %s modem..." % m['name']
        modem = pygsm.GsmModem(port=m['port'],baudrate=m['baudrate'],logger=pygsm.GsmModem.debug_logger).boot()
        #modem.send_sms(ADMIN_NUMBER,"%s hello world!" % m['name'])
        networks.append({'name': m['name'], 'number': m['number'], \
                'sent_count': 0, 'received_count': 0,
                'modem': modem, 'send_to_self': m['send_to_self']})

    timer = 0
    global messages_to_send
    while True:
        print "Next sending in %s seconds" % (SEND_INTERVAL - (timer % SEND_INTERVAL))
        for n in networks:
            try:
                print "about to read message on %s modem" % n['name']
                msg = n['modem'].next_message()
                if msg is not None:
                    print "splitting message rec by %s..." % n['name']
                    msg_data = msg.text.split('*')
                    logfile = open('smslog.csv', 'a')
                    if len(msg_data) is 7:
                        n['received_count'] += 1
                        delay = getDelay(msg_data[4],msg_data[5])
                        print "   writing log file ..."
                        logfile.write("\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"\n" %(msg_data[0], msg_data[1], msg_data[2], msg_data[3], n['received_count'], msg_data[4], msg_data[5], datetime.now().date(), datetime.now().time(), delay, msg_data[6], n['modem'].signal_strength()))
                    else:
                        logfile.write("\"Malformed message to %s modem\",\"%s\",\"%s\"\n" % (n['name'], msg.text, datetime.now()))
                    logfile.close()
            except:
                    print "   failed!"
                    logfile = open('smslog.csv', 'a')
                    logfile.write("read error for network %s\n" % n['name'])
                    logfile.close()
        if messages_to_send:
            route = messages_to_send.pop()
            sendFromModems(route)
        if timer % SEND_INTERVAL == 0:
            print "Timer is %s, queueing messages to send" % timer
            populateSendQueue(networks)
            print "Deleting stored messages"
            for m in networks:
                for i in range(1,41):
                    try:
                        m['modem'].command('AT+CMGD=' + str(i))
                        print("    +++deleted message from %s index %s" % (m['name'], i))
                    except:
                        print("    ---failed to delete message from %s index %s" % (m['name'], i))
        time.sleep(2)
        timer += 2

'''generate a queue of messages to send'''
def populateSendQueue(networks):
        for a in networks:
            for b in networks:
                if a != b or a['send_to_self'] == 1:
                    m = {'origin': a, 'destination': b}
                    global messages_to_send
                    messages_to_send.append(m)

'''sends messaeges using the modems'''
def sendFromModems(route):
        origin = route['origin']
        destination = route['destination']
        print "Sending %s-->%s" % (origin['name'], destination['name'])
        try:
            origin['sent_count'] += 1
            global sent_message_counter
            sent_message_counter += 1
            origin['modem'].send_sms(destination['number'],"%s*%s*%s*%s*%s*%s*%s" % (origin['name'],destination['name'], sent_message_counter, origin['sent_count'], datetime.now().date(), datetime.now().time(),destination['modem'].signal_strength()))
        except:
            print "***An error occured, message not sent***"

def getDelay(date_string, time_string):
    sent_datetime_string = "%s@%s" % (date_string, time_string)
    sent_datetime = datetime.strptime(sent_datetime_string,"%Y-%m-%d@%H:%M:%S.%f")
    delta = datetime.now() - sent_datetime
    return (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10**6) / 10**6

if __name__ == "__main__":
    logModems()
