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
from sqlobject import DateTimeCol
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
    date = DateTimeCol()


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
    sent_time = DateTimeCol()
    origin = StringCol()
    origin_signal = IntCol(notNone=False)
    destination = StringCol()
    destination_signal = IntCol(notNone=False)
    received_time = DateTimeCol(notNone=False)
    run = ForeignKey('Run')
    number = StringCol()


    def sendFormat(self):
        text = "(%s)" % urlencode({'id': self.id,})
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
            baudrate=modemConfig['baudrate'],
            logger=GsmModem.debug_logger,)
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


def check_balance(**kwargs):
    name = kwargs.pop('name')
    data = kwargs.pop('data')
    modem = data['modem']
    cmd = modem.command(data['credit_command'])
    #import ipdb; ipdb.set_trace()
    results = re.search(data['credit_re'],"".join(cmd))                        
    if results:
        print(results.groups())


def make_messsage(**kwargs):
    origin = kwargs.pop('origin')
    destination = kwargs.pop('destination')
    logger = kwargs.pop('logger')
    signal = None
    try:
        signal = origin[1]['modem'].signal_strength()
    except Exception, e:
        logger.debug(e)
    run = kwargs.pop('run')
    msg = Message(sent_time=datetime.now(),
                  run=run,
                  origin=origin[0],
                  origin_signal=signal,
                  received_time=None,
                  destination=destination[0],
                  destination_signal=None,
                  number=destination[1]['number'])
    return msg


def send_from_modems(logger, run):
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
                                logger=logger,
                                destination=destination,
                                run=run)
        logger.info('Sending %s' % message)
        modem = origin[1]['modem']
        origin[1]['modem'].send_sms(destination[1]['number'],
                                    message.sendFormat())

def check_for_new_message(**kwargs):
    name = kwargs.pop('name')
    data = kwargs.pop('data')
    logger = kwargs.pop('logger')
    timer = kwargs.pop('timer')
    logger.info(
        'Check %s modem  for new messages @ %s' % (name, timer))
    msg = data['modem'].next_message()
    if msg:
        logger.info('Got message %s from modem %s' % (msg, name))
        if re.match('^\(.*\)$',msg.text):                    
            results = parse_qs(msg.text.strip('(').strip(')'))
            try:
                signal = data['modem'].signal_strength()
            except Exception, e:
                logger.debug(e)
            try:
                message = Message.get(results['id'][0])
                message.received_time = datetime.now()
                message.destination_signal = signal
                logger.info('Updating message %s' % message.id)
            except Exception,e:
                logger.info(e)
        # remove all messages
        else:
            logger.info('Invalid Message %s"' % msg.text)
        data['modem'].command('at+cmgd=1,4')
        logger.info('Removing all messags from the modem')



def runTest(config, logger):
    """
    Main loop to send messages
    """
    run = Run(location=config['location'],
              date=datetime.now())
    logger.info('Starting test at %s' % run.date)
    timer = 0
    while True:
        for name, data in networks.iteritems():            
            send_from_modems(logger, run)
            check_for_new_message(name=name,
                                  data=data,
                                  logger=logger,
                                  timer=timer)
            if timer % config.get('send_interval') == 0:
                #check_balance(name=name,data=data)
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
