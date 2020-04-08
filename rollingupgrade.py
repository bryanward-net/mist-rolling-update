#!/usr/bin/env python3

import os
import sys
import time
import argparse
import logging
import json
import threading

from time import sleep

from dartmist import mist, misthelpers, mistwebsocket
import config

####################
# Defaults

# Versions to upgrade to are defined in config.py


####################
# Setup

parser = argparse.ArgumentParser(
    description="Upgrade FW of Mist APs, one at a time"
)
parser.add_argument(
    "--token",
    help="Mist API Token.  Can also use env var MIST_TOKEN"
)
parser.add_argument(
    "--orgid",
    required=False,
    help="Organization ID to run against.  Can also use env var MIST_ORGID"
)
parsergroup_site = parser.add_mutually_exclusive_group(required=True)
parsergroup_site.add_argument(
    "--site",
    required=False,
    help="Site name to upgrade"
)
parsergroup_site.add_argument(
    "--siteid",
    required=False,
    help="Site ID to upgrade"
)
parser.add_argument(
    '--delay',
    required=False,
    help='Additional time to wait between devices',
    default=0,
    dest='delay'
)
parser.add_argument(
    '--debug',
    help='Debug Logging Enabled',
    default=False,
    action='store_true',
    dest='debug'
)

args = parser.parse_args()

if args.debug:
    logging.basicConfig(
        format='%(asctime)s\t%(levelname)s\t%(module)s.%(funcName)s:\t%(message)s', level=logging.DEBUG)
else:
    logging.basicConfig(
        format='%(asctime)s\t%(levelname)s\t%(module)s.%(funcName)s:\t%(message)s', level=logging.INFO)

if args.token:
    TOKEN = args.token
else:
    if not os.environ.get("MIST_TOKEN"):
        raise Exception("MIST_TOKEN environment variable is not set!")
    else:
        TOKEN = os.environ.get("MIST_TOKEN")

if args.orgid:
    ORGID = args.orgid
else:
    if not os.environ.get("MIST_ORGID"):
        raise Exception("MIST_ORGID environment variable is not set!")
    else:
        ORGID = os.environ.get("MIST_ORGID")


####################
# Main

def rollingupgrade(ev):

    devices = []
    devices = h.get_devices_stats_in_site(SITEID)

    for device in devices:
        logging.debug(device)
        logging.debug("Working on device {0} [{1}] of type {2}".format(
            device['name'], device['mac'], device['model']))

        # Check if it's disconnected
        if device['status'] != "connected":
            logging.warning("Device {0} [{1}] is in {2} status, skipping...".format(
                device['name'], device['mac'], device['status']))
        # Check if we know this model
        elif device['model'] not in config.versions:
            logging.warning("Unknown model {0}, skipping...".format(device['model']))
        elif device['version'] != config.versions[device['model']]['version']:
            logging.info("Updating firmware on device {0} [{1}] from version {2} to version {3}".format(
                device['name'], device['mac'], device['version'], config.versions[device['model']]['version']))
            # COMMAND FW UPDATE
            logging.debug("Commanding FW Update...")
            logging.debug(config.versions[device['model']]['version'])
            status = h.update_fw(
                SITEID, device, config.versions[device['model']]['version'])
            logging.debug("Commanded FW Update")
            logging.debug(status)

            working = True
            while working:
                logging.debug("Working...")
                msg_rcvd = False
                while not ev.isSet() and len(ws.messages) == 0:
                    logging.debug("Waiting...")
                    msg_rcvd = ev.wait(10)
                if msg_rcvd or ev.isSet() or len(ws.messages) > 0:
                    logging.debug("MESSAGE!")
                    # Process messages
                    msg = json.loads(ws.get_next_message())
                    logging.debug(msg)
                    if msg['event'] == "data" and "data" in msg:
                        data = json.loads(msg['data'])
                        if "mac" in data and device['mac'] == data['mac']:
                            # This is the device we're looking for
                            logging.debug("This is the device we're looking for...")
                            # Check upgrade status
                            if "status" in data and data['status'] == "upgrading" and "upgrading" in data and data['upgrading'] == True and "progress" in data:
                                logging.info("Update of device {0} [{1}] is in progress: {2}%".format(
                                    device['name'], device['mac'], data["progress"]))
                            else:
                                # Poll device status
                                logging.debug("Poll device stats")
                                device2 = h.get_device_stats_in_site_by_mac(SITEID, device['mac'])
                                device = device2
                            logging.debug("Checking if versions match")
                            if device['version'] == config.versions[device['model']]['version']:
                                # Done upgrading!
                                logging.debug("Yes, versions match")
                                logging.info("Update of device {0} [{1}] Complete!  Now at version {2}".format(
                                    device['name'], device['mac'], device['version']))
                                working = False
                    logging.debug(len(ws.messages))
                    ev.clear()
                    # If message says we're still upgrading, then logging.info
                    # If message says we're done upgrading, then break and goto the next device
        else:
            logging.info("Firmware on device {0} [{1}] is already at version {2}".format(
                device['name'], device['mac'], device['version']))
        # Wait additional time between devices
        if int(args.delay) > 0:
            logging.info("Waiting {0} seconds before continuing...".format(str(args.delay)))
            time.sleep(int(args.delay))


####################
# ENTRY POINT

if __name__ == '__main__':
    try:
        logging.info("Connecting to Mist API...")
        logging.debug("ORGID: {0}".format(ORGID))
        conn = mist.Mist(TOKEN, ORGID)
        ws = None
        # myself = conn.get_self()
        # logging.debug(myself)

        if conn.test_connection():
            logging.info("Successfully connected to API.")
        else:
            logging.error("Error connecting to API or no permissions for Organization.  Terminating.")
            exit(-101)

        h = misthelpers.MistHelpers(conn)
        logging.debug("Helpers loaded.")

        if config.config:
            logging.debug("Config present.")
        else:
            logging.error("config.py not loaded!")
            exit(-102)

        if args.site and not args.siteid:
            logging.debug("Getting Site ID...")
            SITEID = h.get_site_by_name(args.site)['id']
        else:
            SITEID = args.siteid
        logging.debug("Site ID is {0}".format(SITEID))

        logging.debug("Creating Websocket")
        try:
            ev = threading.Event()
            ws = mistwebsocket.MistWebsocket(TOKEN, ev)
            logging.debug("Websocket init")
        except Exception as e:
            logging.error(e)

        try:
            ws.open()
        except Exception as e:
            logging.error(e)

        if ws.is_open:
            logging.debug("Yes, the Websocket is open")
        else:
            logging.error("Failed to open Websocket?")
            exit(-103)

        # Subscribe to updates for the devices
        ws.subscribe("/sites/{0}/stats/devices".format(SITEID))

        rollingupgrade(ev)
        logging.info("Rolling upgrade complete!")

        logging.debug("Shutting down websocket...")
        ws.unsubscribe("/sites/{0}/stats/devices".format(SITEID))

        ws.close()
        logging.debug("Websocket shut down")
        logging.debug("Exiting...")
        exit(0)
    except Exception as e:
        logging.error("Unknown error!")
        logging.error(e)
        exit(-100)
