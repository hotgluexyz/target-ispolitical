#!/usr/bin/env python3
import argparse
import json
import logging
import os
from datetime import datetime

import phonenumbers
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("target-ispolitical")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

ENDPOINT = "https://app.ispolitical.com/api/PublicForms/"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def write_json_file(filename, content):
    with open(filename, 'w') as f:
        json.dump(content, f, indent=4)


def parse_args():
    '''Parse standard command-line args.
    Parses the command-line arguments mentioned in the SPEC and the
    BEST_PRACTICES documents:
    -c,--config     Config file
    -s,--state      State file
    -d,--discover   Run in discover mode
    -p,--properties Properties file: DEPRECATED, please use --catalog instead
    --catalog       Catalog file
    Returns the parsed args object from argparse. For each argument that
    point to JSON files (config, state, properties), we will automatically
    load and parse the JSON file.
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-c', '--config',
        help='Config file',
        required=True)

    args = parser.parse_args()
    if args.config:
        setattr(args, 'config_path', args.config)
        args.config = load_json(args.config)

    return args

def upload_items(output, auth):
    for c in output:
        logger.info(c)
        # Post to ISPolitical
        r = requests.post(ENDPOINT, auth=auth, json=c)

        # Parse response
        response = r.text
        logger.info(response)


def convert_date(date):
    date_str = " ".join(date.split(" ")[1:4])
    return datetime.strptime(date_str, "%d %b %Y")


def convert_phone_numbers(number:str):
    phone = phonenumbers.parse(number, None)
    number = phonenumbers.format_number(phone, 2)
    return f"+1 {number}"


def convert_contribution(input: list, transaction_type="Monetary Contribution"):
    contribution_outputs = []
    for contribution in input:
        contribution["date"] = convert_date(contribution["date"])
        contribution["phone"] = convert_phone_numbers(contribution["phone"])
        if contribution["entity_type"]=="Individual":
            output = dict(
                EntityType=contribution["entity_type"],
                NamePrefix=contribution["title"],
                FirstName=contribution["first_name"],
                MiddleName=contribution["middle_name"],
                LastName=contribution["last_name"],
                NameSuffix=contribution["suffix"],
                Nickname=contribution["salutation"],
                Occupation=contribution["occupation"],
                Employer=contribution["employer"],
                AddressType="Home",
                Company="",
                Line1=contribution["line_1"],
                Line2="",
                City=contribution["city"],
                State=contribution["state"],
                ZipCode=contribution["zip"],
                Notes="",
                Source=f"NUMERO-{contribution['form']}",
                Transactions = [
                    dict(
                        Amount=contribution["amount"],
                        Date=contribution["date"].strftime("%Y-%m-%d"),
                        NoteForInternal="",
                        UniqueIdentifier="-".join(
                                [
                                    "NUMERO",
                                    contribution["type"].upper(),
                                    contribution["id"]
                                ]
                            ),
                        TransactionType=transaction_type
                    )
                ],
                Emails=[
                    dict(
                        EmailAddress = contribution["email"]
                    )
                ],
                Phones=[
                    dict(
                        PhoneNumber = contribution["phone"],
                        PhoneType = "Home"
                    )
                ]
            )
        elif contribution["entity_type"]=="Organization":
            output = dict(
                EntityType="Company",
                FullName=contribution["first_name"],
                Occupation=contribution["occupation"],
                Employer=contribution["employer"],
                AddressType="Work",
                Company=contribution["first_name"],
                Line1=contribution["line_1"],
                Line2="",
                City=contribution["city"],
                State=contribution["state"],
                ZipCode=contribution["zip"],
                Notes="",
                Source=f"NUMERO-{contribution['form']}",
                Transactions = [
                    dict(
                        Amount=contribution["amount"],
                        Date=contribution["date"].strftime("%Y-%m-%d"),
                        NoteForInternal=contribution["source_code"],
                        UniqueIdentifier="-".join(
                                [
                                    "NUMERO",
                                    contribution["type"].upper(),
                                    contribution["id"]
                                ]
                            ),
                        TransactionType=transaction_type
                    )
                ],
                Emails=[
                    dict(
                        EmailAddress = contribution["email"]
                    )
                ],
                Phones=[
                    dict(
                        PhoneNumber = contribution["phone"],
                        PhoneType = "Work"
                    )
                ]
            )
        contribution_outputs.append(output)
        return contribution_outputs


def convert_payout(input: list):
    payout_outputs = []
    for payout in input:
        payout["date"] = convert_date(payout["date"])
        payout["coverage_starts_at"] = convert_date(payout["coverage_starts_at"])
        payout["coverage_ends_at"] = convert_date(payout["coverage_ends_at"])
        fees = dict(
            Company="Numero, Inc.",
            EntityType="Company",
            Line1="200 Spectrum Center Drive",
            Line2="Suite 300",
            City="Irvine",
            State="CA",
            ZipCode="92618",
            Transactions=[
                dict(
                    Amount=payout["fees_amount"],
                    Date=payout["date"].strftime("%Y-%m-%d"),
                    NoteForInternal="Processing Fees",
                    TransactionType="Expense",
                    UniqueIdentifier=f"NUMERO-FEES-{payout['id']}"
                )
            ]
        )
        items = [f"NUMERO-CONTRIBUTION-{c}" for c in payout["contribution_ids"]]
        items += [f"NUMERO-REFUND-{c}" for c in payout["refund_ids"]]
        items += [f"NUMERO-FEES-{payout['id']}"]
        deposit = dict(
            Company="Deposit",
            EntityType="Other",
            Notes=payout["batch"],
            Transactions=[
                dict(
                    Amount=payout["net_amount"],
                    Date=payout["date"].strftime("%Y-%m-%d"),
                    NoteForInternal=payout["destination"],
                    TransactionType="Deposit",
                    UniqueIdentifier="-".join(["NUMERO-PAYOUT", payout["id"]])
                )
            ],
            Items=items
        )
        output = dict(
            Fees=fees,
            Deposit=deposit)
        payout_outputs.append(output)
    return payout_outputs

def upload(config, args):
    # Generate basic auth
    auth = HTTPBasicAuth(f"{config['client_account_name']}|{config['integration_login_name']}", config['password'])

    # Upload Contributions
    input_path = f"{config['input_path']}/contributions.json"
    if os.path.exists(input_path):
        logger.info("Found contributions.json, uploading...")
        contributions = load_json(input_path)
        contributions = convert_contribution(contributions)
        upload_items(contributions, auth)
        logger.info("contributions.json uploaded!")


    # Upload Refunds
    input_path = f"{config['input_path']}/refunds.json"
    if os.path.exists(input_path):
        logger.info("Found refunds.json, uploading...")
        refunds = load_json(input_path)
        refunds = convert_contribution(refunds, "Refunded Contribution")
        upload_items(contributions, auth)
        logger.info("refunds.json uploaded!")
    
    # Upload Payouts
    input_path = f"{config['input_path']}/payouts.json"
    if os.path.exists(input_path):
        logger.info("Found payouts.json, uploading...")
        payouts = load_json(input_path)
        payouts = convert_payout(payouts)
        
        for payout in payouts:
            logger.info(payout)
            r = requests.post(ENDPOINT, auth=auth, json=payout['Fees'])
            logger.info(r.text)
            if r.status_code==201:
                r = requests.post(ENDPOINT, auth=auth, json=payout['Deposit'])
                logger.info(r.text)
        logger.info("payouts.json uploaded!")

    logger.info("Posting process has completed!")


def main():
    # Parse command line arguments
    args = parse_args()

    # Upload the new QBO data
    upload(args.config, args)


if __name__ == "__main__":
    main()
