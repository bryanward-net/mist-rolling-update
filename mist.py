#!/usr/bin/env python

import requests
import json
import string
import websocket
import ssl
import threading
import logging

####################
###
### mist.py
###
### Python wrapper for interacting with the Mist API
### Written by Felix Windt and Bryan Ward, 2019-2020
###
### Version 20200308
###
####################

class Mist:
    def __init__(self, token, org_id, version="v1", ignore_failures=False):
        self.token = token
        self.org_id = org_id
        self.headers = {"Authorization": "Token {0}".format(self.token), "Content-type": "application/json"}
        self.base_url = "https://api.mist.com/api"
        self.version = version
        self.ignore_failures = ignore_failures


    def _constructURL(self, url):
        return self.base_url + "/" + self.version + "/" + url.lstrip("/")


    def _interact(self, method, url, payload=None):
        if payload:
            payload = json.dumps(payload)
        func = getattr(requests, method)
        self.last_reply = func(self._constructURL(url), data=payload, headers=self.headers)
        if self.last_reply.status_code in [200, 201, 202]:
            return self.last_reply.json()
        elif self.last_reply.status_code == 204:
            return True
        elif self.last_reply.status_code in [400, 404, 405, 500, 502, 503]:
            if self.ignore_failures:
                return False
            else:
                raise Exception("HTTP {0}: {1}".format(self.last_reply.status_code, self.last_reply.text))
        else:
            raise Exception("HTTP {0}: {1}".format(self.last_reply.status_code, self.last_reply.text))


    def ignore_failures(self, value):
        self.ignore_failure = value
        return True


    def last_reply(self):
        return self.last_reply


    def get(self, url, payload=None):
        return self._interact("get", url, payload)


    def post(self, url, payload=None):
        return self._interact("post", url, payload)


    def put(self, url, payload=None):
        return self._interact("put", url, payload)


    def delete(self, url, payload=None):
        return self._interact("delete", url, payload)

    def get_self(self):
        myself = self.get("self")
        return myself

    def test_connection(self):
        myself = self.get_self()
        if self.org_id in myself['privileges'][0]['org_id']:
            return True
        return False


class MistHelpers:
    def __init__(self, api):
        self.api = api


    def get_sites(self):
        sites = self.api.get("orgs/{0}/sites".format(self.api.org_id))
        return sites


    def get_site_by_name(self, name):
        for site in self.get_sites():
            if site["name"] == name:
                return site
        return None


    def get_devices_stats_in_site(self, site_id):
        devices = self.api.get("/sites/{0}/stats/devices".format(site_id))
        logging.debug(devices)
        return devices


    def get_device_stats_in_site_by_mac(self, site_id, mac):
        mac = mac.replace(":", "").replace("-", "").replace(".", "").lower()
        devices = self.api.get("/sites/{0}/stats/devices".format(site_id))
        device=list(filter(lambda device: device['mac'] == mac, devices))
        if len(device) == 1:
            return device[0]
        elif len(device) < 1:
            return None
        else:
            if self.api.ignore_failures:
                return None
            else:
                raise Exception("Found more than one matching AP")


    def get_devices_in_site(self, site_id):
        devices = self.api.get("/sites/{0}/devices/search?limit=-1".format(site_id))["results"]
        logging.debug(devices)
        return devices


    def get_device_in_site_by_mac(self, site_id, mac):
        mac = mac.replace(":", "").replace("-", "").replace(".", "").lower()
        results = self.api.get("sites/{0}/devices/search?mac={1}".format(site_id, mac))
        logging.debug(results)
        if results["total"] == 1:
            return results["results"][0]
        elif results["total"] < 1:
            return None
        else:
            if self.api.ignore_failures:
                return None
            else:
                raise Exception("Found more than one matching AP")


    def get_all_devices(self):
        result = []
        for site in self.get_sites():
            this_site = {"site": site["name"], "site_id": site["id"]}
            this_site["devices"] = self.get_devices_in_site(site["id"])
            result.append(this_site)


    def get_ap_by_mac(self, mac, site):
        mac = mac.replace(":", "").replace("-", "").replace(".", "").lower()
        aps = self.api.get("sites/{0}/devices".format(site))
        for ap in aps:
            if ap["mac"] == mac:
                return ap
        return None


    def get_ap_fw_ver_by_mac(self, mac, site):
        mac = mac.replace(":", "").replace("-", "").replace(".", "").lower()
        ap = self.get("sites/{0}/devices/search?mac={1}".format(site,mac))
        if (ap['total'] == 1):   ###and mac in ap['results']['mac']['hostname']):
            print(ap['results'][0]['version'])
            return ap['results'][0]['version']
        return None

    def get_devices(self, site):
        devices = None
        devices = self.api.get("sites/{0}/stats/devices".format(site))
        return devices

    def get_device_by_id(self, device_id, site):
        device = None
        device = self.api.get("sites/{0}/stats/devices/{1}".format(site,device_id))
        return device

    def get_device_by_name(self, device_name, site):
        device = None
        device = self.api.get("sites/{0}/stats/devices?name={1}".format(site,device_name))
        return device

    def get_device_by_mac2(self, device_mac, site):
        device = None
        device = self.api.get("sites/{0}/stats/devices/00000000-0000-0000-1000-{1}".format(site,device_mac.translate(str.maketrans('', '', string.punctuation)).lower()))
        return device

    def get_device_fw(self, device):
        fw = None
        fw = device['version']
        return fw

    def update_fw(self, site, device, version):
        status = None
        if version is not None:
            logging.debug("About to command FW update...")
            #from pudb import set_trace
            #logging.disable(logging.CRITICAL)
            #set_trace()
            status = self.api.post("sites/{0}/devices/{1}/upgrade".format(site, device['id']), payload={'version': version})
            return status
        return


class MistWebsocket:
    def __init__(self, token, ev, version="v1", ignore_failures=False, trace=False):
        self.token = token
        self.headers = {"Authorization": "Token {0}".format(self.token), "Content-type": "application/json"}
        self.base_url = "wss://api-ws.mist.com/api-ws/{0}/stream".format(version)
        self.version = version
        self.ignore_failures = ignore_failures
        self.is_open = False
        self.messages = []
        self.app = None
        self.wst = None
        self.ev = ev
        if trace:
            websocket.enableTrace(True)


    def subscribe(self, channel="/test"):
        logging.debug("Subscribing to {0}".format(channel))
        self.app.send(json.dumps({"subscribe": channel}))
        return

    def unsubscribe(self, channel="/test"):
        logging.debug("Unsubscribing from {0}".format(channel))
        self.app.send(json.dumps({"unsubscribe": channel}))
        return

    def on_message(self, message):
        logging.debug(message)
        self.messages.append(message)
        self.ev.set()
        return

    def on_error(self, ws, error="Unknown"):
        logging.error(error)
        return

    def on_close(self, *ws):
        logging.debug("Websocket Closed!")
        self.is_open=False
        return

    def on_open(self, *ws):
        logging.debug("Websocket Open!")
        self.is_open = True
        return

    def on_ping(self, *ws):
        logging.debug("PING")
        return

    def on_pong(self, *ws):
        logging.debug("PONG")
        return

    def flush_messages(self):
        self.messages = []
        self.ev.clear()
        logging.debug("Message stack flushed!")
        return

    def get_next_message(self):
        m = None
        m = self.messages.pop(0)
        return m

    def get_latest_message(self):
        m = None
        m = self.messages.pop(-1)
        return m

    def close(self):
        logging.debug("Closing Websocket")
        #self.app.keep_running = False
        self.app.close()
        self.wst.join()
        logging.debug("Websocket Thread Terminated")
        return

    def open(self):
        logging.debug("Opening Websocket...")
        try:
            self.app = websocket.WebSocketApp(self.base_url,
                #header=["Authorization: Basic {0}".format(base64.encodestring(config["ws_username"] + ':' + config["ws_password"]))],
                header = {"Authorization": "Token {0}".format(self.token), "Content-type": "application/json"},
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open,
                on_ping=self.on_ping,
                on_pong=self.on_pong)
        except Exception as e:
            logging.error(e)
        try:
            logging.debug("Trying to run")
            self.app.keep_running = True
            self.wst = threading.Thread(target=self.app.run_forever, kwargs={"ping_interval":10, "ping_timeout":5}) #"sslopt":{"cert_reqs": ssl.CERT_NONE}
            self.wst.daemon = True
            self.wst.start()
            logging.debug("Websocket Thread Started")
            while not self.app.sock.connected:
                from time import sleep
                sleep(1)
            if self.app.sock.connected:
                logging.debug("Sock Connected")
                #assert self.is_open = True
    

        except Exception as e:
            logging.error(e)
        return