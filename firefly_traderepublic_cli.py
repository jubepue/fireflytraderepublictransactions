#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import sys

from firefly_traderepublic_transactions import FireflyTraderepublicClient

@click.command()
@click.option(
    '--phone_no', '-d',
    envvar="TRADEREPUBLIC_PHONE",
    type=str,
    help='Trade Republic phone +49XXXXXXXXX format (required)',
)
@click.option(
    '--pin', '-p',
    envvar="TRADEREPUBLIC_PIN",
    type=str,
    help='Trade Republic pin 0000 format (required)',
)
@click.option(
    '--firefly-token', '-f',
    envvar="FIREFLY_TOKEN",
    type=str,
    help='Firefly token (required)',
)
@click.option(
    '--account-id', '-a',
    envvar="TRADEREPUBLIC_ACCOUNT",
    type=str,
    help='Id of Trade Republic account in FireflyIII (required)',
)
@click.option(
    '--vault-id', '-v',
    envvar="TRADEREPUBLIC_VAULT",
    type=str,
    help='Id of Trade Republic vault in FireflyIII',
)
@click.option(
    '--topup-id', '-t',
    envvar="TOPUP_ACCOUNT",
    type=str,
    help='Id of topup account in FireflyIII',
)
@click.option(
    '--wallet-id', '-w',
    envvar="WALLET_ACCOUNT",
    type=str,
    help='Id of wallet account in FireflyIII',
)
@click.option(
    '--currency', '-c',
    envvar="CURRENCY",
    type=str,
    help='Currency of transactions to process',
)
@click.option(
    '--firefly-url', '-u',
    envvar="FIREFLY_URL",
    type=str,
    help='URL to FireflyIII instance including trailing slash "/" (required)',
)
def main(phone_no, pin, firefly_token, account_id, vault_id, topup_id, wallet_id, currency, firefly_url):
    if phone_no is None:
        print("You don't have a Trade Republic phone number. Use '+49XXXXXXXXX' format")
        sys.exit()
    if pin is None:
        print("You don't have a Trade Republic pin. Use '0000' format")
        sys.exit()
    if firefly_token is None:
        print("You don't have a FireflyIII token. Use 'Create Personal Access token' option in FireflyIII")
        sys.exit()
    if account_id is None:
        print("You don't have a Trade Republic account Id inside FireflyIII")
        sys.exit()
    if firefly_url is None:
        print("You don't have FireflyIII instance URL")
        sys.exit()
    client = FireflyTraderepublicClient(phone_no, pin, firefly_token, account_id, firefly_url, vault_id, topup_id, wallet_id, currency)
    client.process()
    
if __name__ == "__main__":
    main()
