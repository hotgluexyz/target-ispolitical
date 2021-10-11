#!/usr/bin/env python3
import os
import json
import argparse
import logging

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("target-ispolitical")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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


def upload_contributions(config, auth):
    # Get input path
    input_path = f"{config['input_path']}/contributions.json"
    # Read the contributions
    contributions = load_json(input_path)

    for c in contributions:
        logger.info(c)
        # Post to ISPolitical
        r = requests.post("https://app.ispolitical.com/api/PublicForms/", auth=auth, json=c)

        # Parse response
        response = r.text
        logger.info(response)


def upload(config, args):
    # Generate basic auth
    auth = HTTPBasicAuth(f"{config['client_account_name']}|{config['integration_login_name']}", config['password'])

    # Upload Contributions
    if os.path.exists(f"{config['input_path']}/contributions.json"):
        logger.info("Found contributions.json, uploading...")
        upload_contributions(config, auth)
        logger.info("contributions.json uploaded!")

    logger.info("Posting process has completed!")


def main():
    # Parse command line arguments
    args = parse_args()

    # Upload the new QBO data
    upload(args.config, args)


if __name__ == "__main__":
    main()
