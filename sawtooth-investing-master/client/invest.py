#!/bin/python3
import hashlib
import os
import base64
import random
import time
import requests
import yaml
import sys
import logging
import optparse
from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey
from sawtooth_sdk.protobuf.transaction_pb2 import TransactionHeader
from sawtooth_sdk.protobuf.transaction_pb2 import Transaction
from sawtooth_sdk.protobuf.batch_pb2 import BatchList
from sawtooth_sdk.protobuf.batch_pb2 import BatchHeader
from sawtooth_sdk.protobuf.batch_pb2 import Batch

logging.basicConfig(filename='client.log',level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

parser = optparse.OptionParser()
parser.add_option('-U', '--url', action = "store", dest = "url", default = "http://rest-api:8008")

def hash(data):
    return hashlib.sha512(data.encode()).hexdigest()

family_name = "investing"
FAMILY_NAME = hash(family_name)[:6]

INVESTORS = hash("investors")[:6]
INVESTOR_LIST = hash("investors-list")
INVESTORS_TABLE = FAMILY_NAME + INVESTORS + INVESTOR_LIST[:58]

INVESTING_ENTRIES = hash("investing-entries")[:6]
STARTUPS = hash("startups")
STARTUPS_TABLE = FAMILY_NAME + INVESTING_ENTRIES + STARTUPS[:58]

# random private key
context = create_context('secp256k1')
private_key = context.new_random_private_key()
signer = CryptoFactory(context).new_signer(private_key)
public_key = signer.get_public_key().as_hex()

base_url = ''

def getStartupsAddress(startup):
    return FAMILY_NAME + INVESTING_ENTRIES + hash(startup)[:58]

def getInvestorAddress(investor):
    investor = str(investor)
    return FAMILY_NAME + INVESTORS + hash(investor)[:58]

def addStartup(startupName,startuplink,startuplocation,startupGoal):
    l = [startupName,startuplink,startuplocation,str(startupGoal),str(0)]
    command_string = ','.join(l)
    input_address_list = [STARTUPS_TABLE]
    output_address_list = [STARTUPS_TABLE, getStartupsAddress(startupName)]
    response = wrap_and_send("addstartup", command_string, input_address_list, output_address_list, wait = 5)
    print ("add response: {}".format(response))
    return yaml.safe_load(response)['data'][0]['status']

def Invest(investorName,startupName,value):
    l = [investorName,startupName,value]
    command_string = ','.join(l)
    startupaddress = getStartupsAddress(startupName)
    input_address_list = [STARTUPS_TABLE, INVESTORS_TABLE, startupaddress]
    output_address_list = [STARTUPS_TABLE, INVESTORS_TABLE, startupaddress]
    response = wrap_and_send("invest", command_string, input_address_list, output_address_list, wait = 5)
    print ("add response: {}".format(response))
    return yaml.safe_load(response)['data'][0]['status']


def listStartups():
    result = send_to_rest_api("state/{}".format(STARTUPS_TABLE))
    try:
        return (base64.b64decode(yaml.safe_load(result)["data"])).decode()
    except BaseException:
        return None

def listInvestors():
    result = send_to_rest_api("state/{}".format(INVESTORS_TABLE))
    try:
        return (base64.b64decode(yaml.safe_load(result)["data"])).decode()
    except BaseException:
        return None

def send_to_rest_api(suffix, data=None, content_type=None):
    url = "{}/{}".format(base_url, suffix)
    headers = {}
    logging.info ('sending to ' + url)
    if content_type is not None:
        headers['Content-Type'] = content_type

    try:
        if data is not None:
            result = requests.post(url, headers=headers, data=data)
            logging.info ("\nrequest sent POST\n")
        else:
            result = requests.get(url, headers=headers)
        if not result.ok:
            logging.debug ("Error {}: {}".format(result.status_code, result.reason))
            raise Exception("Error {}: {}".format(result.status_code, result.reason))
    except requests.ConnectionError as err:
        logging.debug ('Failed to connect to {}: {}'.format(url, str(err)))
        raise Exception('Failed to connect to {}: {}'.format(url, str(err)))
    except BaseException as err:
        raise Exception(err)
    return result.text

def wait_for_status(batch_id, result, wait = 10):
    '''Wait until transaction status is not PENDING (COMMITTED or error).
        'wait' is time to wait for status, in seconds.
    '''
    if wait and wait > 0:
        waited = 0
        start_time = time.time()
        logging.info ('url : ' + base_url + "batch_statuses?id={}&wait={}".format(batch_id, wait))
        while waited < wait:
            result = send_to_rest_api("batch_statuses?id={}&wait={}".format(batch_id, wait))
            status = yaml.safe_load(result)['data'][0]['status']
            waited = time.time() - start_time

            if status != 'PENDING':
                return result
        logging.debug ("Transaction timed out after waiting {} seconds.".format(wait))
        return "Transaction timed out after waiting {} seconds.".format(wait)
    else:
        return result


def wrap_and_send(action, startupName, input_address_list, output_address_list, wait=None):
    '''Create a transaction, then wrap it in a batch.
    '''
    payload = ",".join([action, str(startupName)])
    logging.info ('payload: {}'.format(payload))

    # Construct the address where we'll store our state.
    # Create a TransactionHeader.
    header = TransactionHeader(
        signer_public_key = public_key,
        family_name = family_name,
        family_version = "1.0",
        inputs = input_address_list,         # input_and_output_address_list,
        outputs = output_address_list,       # input_and_output_address_list,
        dependencies = [],
        payload_sha512 = hash(payload),
        batcher_public_key = public_key,
        nonce = random.random().hex().encode()
    ).SerializeToString()

    # Create a Transaction from the header and payload above.
    transaction = Transaction(
        header = header,
        payload = payload.encode(),                 # encode the payload
        header_signature = signer.sign(header)
    )

    transaction_list = [transaction]

    # Create a BatchHeader from transaction_list above.
    header = BatchHeader(
        signer_public_key = public_key,
        transaction_ids = [txn.header_signature for txn in transaction_list]
    ).SerializeToString()

    # Create Batch using the BatchHeader and transaction_list above.
    batch = Batch(
        header = header,
        transactions = transaction_list,
        header_signature = signer.sign(header)
    )

    # Create a Batch List from Batch above
    batch_list = BatchList(batches=[batch])
    batch_id = batch_list.batches[0].header_signature
    # Send batch_list to the REST API
    result = send_to_rest_api("batches", batch_list.SerializeToString(), 'application/octet-stream')

    # Wait until transaction status is COMMITTED, error, or timed out
    return wait_for_status(batch_id, result, wait = wait)

if __name__ == '__main__':
    try:
        opts, args = parser.parse_args()
        base_url = opts.url
        if sys.argv[1] == "addstartup":
            result = addStartup(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])
            if result == 'COMMITTED':
                logging.info (sys.argv[2] + " added")
                print ("\nStartup added " + sys.argv[2])
            else:
                logging.info (sys.argv[2] + " not added")
                print ("\n{} not added ".format(sys.argv[2]))
        elif sys.argv[1] == "invest":
            result = Invest(sys.argv[2],sys.argv[3],sys.argv[4])
            if result == 'COMMITTED':
                print ("\n" + sys.argv[2] + " invest in " + sys.argv[3])
            else:
                print ("\ncannot invest in " + sys.argv[3])
        elif sys.argv[1] == "liststartups":
            if len(sys.argv) >= 3:
                if sys.argv[2] == "bylocation":
                    location = sys.argv[3]
                    result = listStartups()   
                    r = result.split(",")
                    for i in range(0,int(len(r)/5)):
                        if (r[i*5+2]== location):
                            top5 = (r[i*5:(i+1)*5])
                            print ('Startup: {}'.format (top5))
            else: 
                result = listStartups()   
                r = result.split(",")
                for i in range(0,int(len(r)/5)):
                    top5 = (r[i*5:(i+1)*5])
                    print ('Startup: {}'.format (top5))

        elif sys.argv[1] == "listinvestors":
            if len(sys.argv) >= 3:
                if sys.argv[2] == "bystartup":
                    name = sys.argv[3]
                    result = listInvestors()   
                    r = result.split(",")
                    print('\n{} investors:'.format(name))
                    for i in range(0,int(len(r)/3)):
                        if (r[i*3+1]== name):
                            top3 = (r[i*3:(i+1)*3])
                            print ('{}'.format (top3))
            else:
                result = listInvestors()
                r = result.split(",")
                print("\nThe investors:")
                for i in range(0,int(len(r)/3)):
                    top3 = (r[i*3:(i+1)*3])
                    print ('{}'.format (top3))
                
            
    except IndexError as i:
        logging.debug ('startup name not entered')
        print ('Enter startup name.')
        print (i)
    except Exception as e:
        print (e)