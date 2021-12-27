#!/bin/python3

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------
import traceback
import sys
import hashlib
import logging

from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError
from sawtooth_sdk.processor.core import TransactionProcessor

DEFAULT_URL = 'tcp://validator:4004'

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

def getStartupsAddress(startup):
    return FAMILY_NAME + INVESTING_ENTRIES + hash(startup)[:58]

def getInvestorAddress(investor):
    investor = str(investor)
    return FAMILY_NAME + INVESTORS + hash(investor)[:58]

class InvestingTransactionHandler(TransactionHandler):
    '''
    Transaction Processor class for the voting family
    '''
    def __init__(self, namespace_prefix):
        '''Initialize the transaction handler class.
        '''
        self._namespace_prefix = namespace_prefix

    @property
    def family_name(self):
        '''Return Transaction Family name string.'''
        return family_name

    @property
    def family_versions(self):
        '''Return Transaction Family version string.'''
        return ['1.0']

    @property
    def namespaces(self):
        '''Return Transaction Family namespace 6-character prefix.'''
        return [self._namespace_prefix]

    # Get the payload and extract the voting-specific information.
    # It has already been converted from Base64, but needs deserializing.
    # It was serialized with CSV: action, value
    def _unpack_transaction(self, transaction):
        header = transaction.header
        payload_list = self._decode_data(transaction.payload)
        return payload_list


    def apply(self, transaction, context):
        '''This implements the apply function for the TransactionHandler class.
        '''
        
        try:
            payload_list = self._unpack_transaction(transaction)
            action = payload_list[0]
            try:
                if action == "addstartup":
                    startupName = payload_list[1]
                    startupLink = payload_list[2]
                    startupLocation = payload_list[3]
                    startupGoal = payload_list[4]
                    startupBalance = payload_list[5]
                    self._addstartup(context,startupName,startupLink,startupLocation,startupGoal,startupBalance)
                elif action == "invest":
                    investorName = payload_list[1]
                    startupName = payload_list[2]
                    value = int(payload_list[3])
                    self.invest_in(context,investorName,startupName,value)
                
            except IndexError as i:
                raise Exception()
        except Exception as e:
            raise InvalidTransaction("Error: {}".format(e))
  
    def invest_in(self, context, investorName, startupName,value):
        startupaddress = getStartupsAddress(startupName)
        try:
            existing_startups= self._readData(context, STARTUPS_TABLE)
            if existing_startups:
                if startupName in existing_startups:
                    index = existing_startups.index(startupName)
                    investors_list = self._readData(context, INVESTORS_TABLE)
                    initial_value_count = self._readData(context, startupaddress)
                    if int(existing_startups[index + 3]) - int(existing_startups[index + 4]) == 0 :
                        raise InvalidTransaction('{} already got the Goal.'.format(startupName))
                    else:
                        if (value + int(existing_startups[index + 4])) <= (int(existing_startups[index+3])) :
                            newbalance = value + int(existing_startups[index + 4])  
                            investors_list.append(investorName)
                            investors_list.append(startupName)
                            investors_list.append(str(value))
                            existing_startups[index+4] = str(newbalance)
                            existing_startups[index+3] = str(int(existing_startups[index+3]))
                            addresses = context.set_state({
                            STARTUPS_TABLE: self._encode_data(existing_startups),
                            INVESTORS_TABLE: self._encode_data(investors_list),
                            startupaddress: self._encode_data(str(newbalance))
                            })
                        else:
                            newbalance = int(existing_startups[index + 3])
                            investors_list.append(investorName)
                            investors_list.append(startupName)
                            value = (int(existing_startups[index + 3])- int(existing_startups[index + 4]))
                            investors_list.append(str(value))
                            existing_startups[index+4] = str(newbalance)
                            existing_startups[index+3] = str(int(existing_startups[index+3]))
                            addresses = context.set_state({
                            STARTUPS_TABLE: self._encode_data(existing_startups),
                            INVESTORS_TABLE: self._encode_data(investors_list),
                            startupaddress: self._encode_data(str(newbalance))
                            })                  
                else:
                        raise InvalidTransaction('Startup doesn\'t exist..')
            else:
                raise InvalidTransaction('there is no Startups.')
                
        except TypeError as t:
                logging.debug('TypeError in _invest: {}'.format(t))
                raise InvalidTransaction('Type error')
        except InvalidTransaction as e:
                logging.debug ('excecption: {}'.format(e))
                raise e
        except Exception as e:
                logging.debug('excecption: {}'.format(e))
                raise InvalidTransaction('excecption: {}'.format(e))

    @classmethod
    def _addstartup(self, context,startupName,startupLink,startupLocation,startupGoal,startupBalance):
        startupaddress = getStartupsAddress(startupName)
        try:
            startups  = self._readData(context, STARTUPS_TABLE)  
            if startups:
                if startupName not in startups:
                    details = [startupName,startupLink,startupLocation,startupGoal,startupBalance]
                    for x in details:
                        startups.append(x)
                else:
                    pass
                    # raise InvalidTransaction('{} already exists.'.format(partyName))
            else:
                startups = [startupName,startupLink,startupLocation,startupGoal,startupBalance]
            startups = self._encode_data(startups)
            addresses = context.set_state({
            STARTUPS_TABLE: startups,
                startupaddress: self._encode_data(str(startupBalance))
            })
        except Exception as e:
            logging.debug ('excecption: {}'.format(e))
            raise InvalidTransaction("State Error")

    # returns a list
    @classmethod
    def _readData(self, context, address):
        state_entries = context.get_state([address])
        if state_entries == []:
            return []
        data = self._decode_data(state_entries[0].data)
        return data

    # returns a list
    @classmethod
    def _decode_data(self, data):
        return data.decode().split(',')

    # returns a csv string
    @classmethod
    def _encode_data(self, data):
        return ','.join(data).encode()


def main():
    try:
        # Setup logging for this class.
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)

        # Register the Transaction Handler and start it.
        processor = TransactionProcessor(url=DEFAULT_URL)
        sw_namespace = FAMILY_NAME
        handler = InvestingTransactionHandler(sw_namespace)
        processor.add_handler(handler)
        processor.start()
    except KeyboardInterrupt:
        pass
    except SystemExit as err:
        raise err
    except BaseException as err:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()