"""
SMS Timer Script
"""
from optparse import OptionParser
import os
import time
from datetime import datetime
from Queue import Queue
from urllib import urlencode
from urlparse import parse_qs
import logging
import re
from yaml import load
from pygsm import GsmModem
from sqlobject import connectionForURI
from sqlobject import sqlhub
from sqlobject import SQLObject
from sqlobject import StringCol
from sqlobject import TimeCol
from sqlobject import BoolCol
from sqlobject import IntCol
from sqlobject import ForeignKey


networks = {}
messageRoutes = Queue()
sent_message_counter = 0


class Run(SQLObject):
    """
    A class to store a test session in the database
    Each test has its own Run object associated with it.
    """
    location = StringCol()
    date = TimeCol()


class Modem(SQLObject):
    """
    A class to store info about the modem
    """
    name = StringCol()
    number = IntCol()
    port = StringCol()
    network = StringCol()
    send_to_self = BoolCol()
    sent_cout = IntCol(default=0)
    received_count = IntCol(default=0)

    def __str__(self):
        return "Modem @ %s" % self.port


class Message(SQLObject):
    """Class to store message in db"""
    sent_time = TimeCol()
    origin = StringCol()
    destination = StringCol()
    received_time = TimeCol(notNone=False,
                            notNull=False)
    signal_strength = IntCol()
    run = ForeignKey('Run')
    number = StringCol()


    def sendFormat(self):
        text = "(%s)" % urlencode({'sent_time': self.sent_time,
                                   'run' : self.run.id,
                                   'id': self.id,})
        return text

def make_logger(file):
    """
    Load the logging config...
    """
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    ch = logging.FileHandler(file)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    log.addHandler(ch)
    return log


def initdb(config, logger):
    dbfile = os.path.abspath(config['file'])
    conn = connectionForURI(
        "%s:%s" % (config['type'],
                   dbfile))
    sqlhub.processConnection = conn
    if not Modem.tableExists():
        Modem.createTable()
        Message.createTable()
        Run.createTable()


def loadModems(config, logger):
    """
    Updates networks
    """
    for m in config['modems'].keys():
        modemConfig = config['modems'][m]
        modem = GsmModem(
            port=modemConfig['port'],
            baudrate=modemConfig['baudrate'])
        modem.boot()
        networks.update({m: modemConfig})
        networks[m].update({'modem': modem})

def make_routes(logger):
    """
    Generate a queue of messages to send
    """
    for a in networks.items():
        for b in networks.items():
            if a[0] != b[0] or a[1]['send_to_self'] == True:
                m = {'origin': a, 'destination': b}
                logger.info('Making a route from %s to %s' % (a, b))
                messageRoutes.put(m)


def make_messsage(**kwargs):
    origin = kwargs.pop('origin')
    destination = kwargs.pop('destination')
    run = kwargs.pop('run')
    msg = Message(sent_time=datetime.now(),
                  run=run,
                  origin=origin[0],
                  received_time=None,
                  destination=destination[0],
                  signal_strength=destination[1]['modem'].signal_strength(),
                  number=destination[1]['number'])
    return msg


def sendFromModems(logger, run):
    """
    Sends messaeges using the modem
    get message from the queue
    """
    if not messageRoutes.empty():
        route = messageRoutes.get()
        origin = route['origin']
        destination = route['destination']
        logger.info("Sending %s-->%s" % (origin[0], destination[0]))
        origin[1]['sent_count'] += 1
        global sent_message_counter
        sent_message_counter += 1
        message = make_messsage(origin=origin,
                                destination=destination,
                                run=run)
        logger.info('Sending %s' % message)
        modem = origin[1]['modem']
        origin[1]['modem'].send_sms(destination[1]['number'],
                                    message.sendFormat())


def runTest(config, logger):
    """
    Main loop to send messages
    """
    run = Run(location=config['location'],
              date=datetime.now())
    logger.info('Starting test at %s' % run.date)
    timer = 0
    while True:
        for modemKey, modemValue in networks.iteritems():            
            sendFromModems(logger, run)
            logger.info('Check modem %s for new messages @ %s' % (
                modemKey, timer))
            msg = modemValue['modem'].next_message()
            if msg:
                logger.info('Got message %s from modem %s' % (msg,
                                                              modemKey))
                if re.match('^\(.*\)$',msg.text):                    
                    data = parse_qs(msg.text.strip('(').strip(')'))
                    message = Message.get(data['id'][0])
                    message.received_time = datetime.now()
                    logger.info('Updating message %s' % message.id)
                # remove all messages
                else:
                    logger.info('Invalid Message %s"' % msg.text)
                modemValue['modem'].command('at+cmgd=1,4')
                logger.info('Removing all messags from the modem')
            if timer % config.get('send_interval') == 0:
                make_routes(logger)
            time.sleep(config.get('sleep'))
            timer = timer + + int(config.get('sleep'))
            
def main(*args):
    """
    Main function gets called via the command line
    """
    logger = make_logger('logs.txt')
    logger.info('Starting SMS timer script')
    parser = OptionParser()
    parser.add_option("-c", "--config", dest="config",
                      help="config file")
    (options, args) = parser.parse_args()

    config = load(open(options.config))
    initdb(config['database'], logger)
    loadModems(config, logger)
    runTest(config, logger)
