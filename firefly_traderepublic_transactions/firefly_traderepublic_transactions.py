import json
import os

from datetime import datetime, timedelta
from pathlib import Path

import requests
import asyncio

from appdirs import user_cache_dir
from pytr.account import login
from pytr.timeline import Timeline

_CACHE_FILE = 'last_transaction.txt'
_CACHE_DIR = 'traderepublic'
_DATE_FORMAT = '%Y-%m-%d'

_TRANSACTIONS_ENDPOINT = 'api/v1/transactions'

class FireflyTransaction:
    def __init__(
        self,
        leg_id,
        transaction_type,
        date,
        description,
        merchant,
        amount,
        category,
        is_vault,
        currency
    ):
        self.leg_id = leg_id
        self.transaction_type = self.extract_type(transaction_type, amount)
        self.date = self.extract_date(date)
        self.opposite_account = self.extract_opposite_acount(merchant, description)
        self.amount = amount.get_real_amount()
        self.category = category
        self.is_vault = is_vault
        self.currency = currency
      
    def write_transaction_leg_id(self):
        Path(_CACHE_DIR).mkdir(parents=True, exist_ok=True)
        file = Path(os.path.join(_CACHE_DIR, _CACHE_FILE)).open(mode='w')
        file.write(self.leg_id)
      
    @staticmethod
    def extract_date(date, date_format=_DATE_FORMAT):
        dt = datetime.fromtimestamp(date / 1000)
        dt_str = dt.strftime(date_format)
        return dt_str
      
    @staticmethod
    def extract_type(transaction_type, amount):
        if transaction_type == 'CARD_PAYMENT' or (transaction_type == 'EXCHANGE' and amount.get_real_amount() < 0):
            return 'withdrawal'
        if (transaction_type == 'TRANSFER' or transaction_type == 'EXCHANGE' or transaction_type == 'CARD_REFUND') and amount.get_real_amount() > 0:
            return 'deposit'
        if transaction_type == 'TOPUP' or transaction_type == 'TRANSFER' or transaction_type == 'ATM':
            return 'transfer'
        raise Exception('Unknown transfer type')
      
    @staticmethod
    def extract_opposite_acount(merchant, description):
        if merchant is not None:
            return merchant.get('name')
        else:
            return description
          
    @staticmethod
    def get_last_transaction_leg_id():
        Path(_CACHE_DIR).mkdir(parents=True, exist_ok=True)
        try:
            file = Path(os.path.join(_CACHE_DIR, _CACHE_FILE)).open(mode='r')
        except FileNotFoundError:
            return ''
        return file.readline()
      
    def get_json(self, account_id, vault_id, topup_id, wallet_id):
        if self.transaction_type == 'deposit' or (self.transaction_type == 'transfer' and self.amount > 0) \
                or (self.is_vault and self.opposite_account == 'To ' + self.currency):
            target_account_key = 'destination_id'
            target_account_val = account_id
            source_account_key = 'source_name'
            source_account_val = self.opposite_account
        else:
            target_account_key = 'destination_name'
            target_account_val = self.opposite_account
            source_account_key = 'source_id'
            source_account_val = account_id
        if self.is_vault:
            if vault_id is None:
                raise Exception('Missing vault id')
            if source_account_key == 'source_name':
                source_account_key = 'source_id'
                source_account_val = vault_id
            else:
                target_account_key = 'destination_id'
                target_account_val = vault_id
        elif self.transaction_type == 'transfer' and self.amount > 0:
            if topup_id is None:
                raise Exception('Missing topup account id')
            source_account_key = 'source_id'
            source_account_val = topup_id
        elif self.transaction_type == 'transfer' and self.amount < 0:
            if wallet_id is None:
                raise Exception('Missing wallet account id')
            target_account_key = 'destination_id'
            target_account_val = wallet_id
        return {
            'description': self.category,
            'type': self.transaction_type,
            'amount': abs(self.amount),
            'category': self.category,
            'date': self.date,
            'currency_code': self.currency,
            target_account_key: target_account_val,
            source_account_key: source_account_val,
        }
      
class FireflyTransactions:
    def __init__(self, account_transactions, firefly_token, account_id, vault_id, topup_id, wallet_id, firefly_url,
                 currency):
        self.account_id = account_id
        self.vault_id = vault_id
        self.topup_id = topup_id
        self.wallet_id = wallet_id
        self.currency = currency
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + firefly_token,
        }
        self.push_url = firefly_url + _TRANSACTIONS_ENDPOINT
        self.list = []
        for transaction in sorted(account_transactions, key=lambda k: k['createdDate']):
            if (self.currency is None or self.currency == transaction.get('currency')) \
                    and (transaction.get('vault') is None or transaction.get('amount') < 0) \
                    and transaction.get('state') != 'DECLINED':
                firefly_transaction = FireflyTransaction(
                    leg_id=transaction.get('legId'),
                    transaction_type=transaction.get('type'),
                    date=transaction.get('createdDate'),
                    description=transaction.get('description'),
                    merchant=transaction.get('merchant'),
                    amount=transaction.get('amount'),
                    category=transaction.get('category'),
                    is_vault=bool(transaction.get('vault')),
                    currency=transaction.get('currency')
                )
                self.list.append(firefly_transaction)
                      
    def __len__(self):
        return len(self.list)
      
    def process(self):
        last_trans_leg_id = FireflyTransaction.get_last_transaction_leg_id().strip()
        process_state = False
        last_transaction = None
        fresh_run_transaction = None
        for transaction in self.list:
            if process_state:
                payload = transaction.get_json(self.account_id, self.vault_id, self.topup_id, self.wallet_id)
                self.push_transaction(payload)
                last_transaction = transaction
            elif transaction.leg_id == last_trans_leg_id:
                process_state = True
                fresh_run_transaction = None
            else:
                fresh_run_transaction = transaction
        if last_transaction is not None:
            last_transaction.write_transaction_leg_id()
            return
        if fresh_run_transaction is not None:
            fresh_run_transaction.write_transaction_leg_id()
          
    def push_transaction(self, payload):
        payload = {'transactions': [payload]}
        response = requests.post(self.push_url, headers=self.headers, json=payload).json()
        print(response)
      
class FireflyTraderepublicClient:
    def __init__(self, phone_no, pin, firefly_token, account_id, firefly_url, vault_id, topup_id, wallet_id, currency):
        self.phone_no = phone_no
        self.pin = pin
        self.firefly_token = firefly_token
        self.account_id = account_id
        self.vault_id = vault_id
        self.topup_id = topup_id
        self.wallet_id = wallet_id
        self.firefly_url = firefly_url
        self.currency = currency
    async def dl_loop(self):
        tr=login(phone_no=self.phone_no, pin=self.pin)
        tl = Timeline(self.tr, 0)
        await tl.get_next_timeline_transactions()
    
    def process(self):
        asyncio.get_event_loop().run_until_complete(self.dl_loop())
        #transactions.process()
