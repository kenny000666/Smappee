#!/usr/bin/python2.7

import sys
import os
import requests
import time
import re
import logging
import paho.mqtt.publish as publish
from ConfigParser import SafeConfigParser
from time import sleep

log = None

def initLogger(name):
    global log
    logging.basicConfig(filename=os.path.normpath(os.path.dirname(os.path.realpath(__file__)) + "/" + name + ".log"), level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger(__name__)
    soh = logging.StreamHandler(sys.stdout)
    soh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.addHandler(soh)
    log.setLevel(logging.DEBUG)

class SmappeeMQTT():
    def __init__(self):
        cfg = SafeConfigParser()
        cfg.optionxform = str
        cfg.read(os.path.normpath(os.path.dirname(os.path.realpath(__file__)) + "/smappee-mqtt.conf"))
        self.smappee = cfg.get("smappee", "hostname")
        log.info("Smappee Host: " + self.smappee)

    @property
    def grid(self):
        return self.grid

    @property
    def solar(self):
        return self.solar

    @property
    def excess (self):
        return self.excess

    def run(self):
        reline = re.compile("<BR>\s*(\S+=.+?)<BR>")
        refield = re.compile(",\s+")
        smappeevalues = [None] * 3
        try:
            response = requests.get("http://" + self.smappee + "/gateway/apipublic/reportInstantaneousValues")
            report = response.json()["report"]
            i = 0
            for line in re.findall(reline, report):

                if re.findall("activePower=", line):

                    for field in re.split(refield, line):

                        if re.findall("^activePower=",field):
                            smappeevalues[i] = float(field.replace("activePower=", "").replace(" W", ""))
                            log.debug("Value " + str(i) + " = " + str(smappeevalues[i]))
                            i = i + 1

            self.grid = smappeevalues[0]*-1
            if self.grid < 0:
      		self.grid = 0
            self.solar = smappeevalues[1]
            if self.solar < 0:
                self.solar = 0
            self.excess = smappeevalues[2]


        except Exception, e:
            log.warning(e)
            pass


def main(argv=None):
    initLogger("Smappee")
    log.info("Initializing Smappee...")
    smappee = SmappeeMQTT()

    cfg = SafeConfigParser(
            {"client_id": "smappee-mqtt-" + str(os.getpid()), "hostname": "localhost", "port": "1883", "auth": "False",
             "retain": "False", "qos": "0"})
    cfg.optionxform = str
    cfg.read(os.path.normpath(os.path.dirname(os.path.realpath(__file__)) + "/smappee-mqtt.conf"))
    genIDX = cfg.get("domoticz", "consumptionIDX")
    solarIDX = cfg.get("domoticz", "solarIDX")
    excessIDX = cfg.get("domoticz", "excessIDX")
    client_id = cfg.get("mqtt", "client_id")
    host = cfg.get("mqtt", "hostname")
    port = eval(cfg.get("mqtt", "port"))
    topic = cfg.get("mqtt", "topic")
    qos = eval(cfg.get("mqtt", "qos"))
    retain = eval(cfg.get("mqtt", "retain"))
    if eval(cfg.get("mqtt", "auth")):
        auth = {"username": cfg.get("mqtt", "user"), "password": cfg.get("mqtt", "password")}
    else:
        auth = None

    log.info("Connecting to MQTT Broker on " + host + " port " + str(port))

    while True:
        smappee.run()
        gridTopic = topic + "grid"
        solarTopic = topic + "solar"
        excessTopic = topic + "excess"

        try:
            gridmsgs = [{"topic": gridTopic, "payload": """{ "idx" : """ + genIDX + """, "nvalue" : 0, "svalue" : \"""" + str(smappee.grid) + ";0\"}", "qos": qos, "retain": retain}]
            publish.multiple(gridmsgs, hostname=host, port=port, client_id=client_id, auth=auth)
        except:
            log.warning("Unable to publish message, " + gridmsgs)

        try:
            solarmsgs = [{"topic": solarTopic, "payload": """{ "idx" : """ +solarIDX + """, "nvalue" : 0, "svalue" : \"""" + str(smappee.solar) + ";0\"}", "qos": qos, "retain": retain}]
            publish.multiple(solarmsgs, hostname=host, port=port, client_id=client_id, auth=auth)
        except:
            log.warning("Unable to publish message, " + solarmsgs)

        try:
            excessmsgs = [{"topic": excessTopic, "payload": """{ "idx" : """ + excessIDX + """, "nvalue" : 0, "svalue" : \"""" + str(smappee.excess) + ";0\"}", "qos": qos, "retain": retain}]
            publish.multiple(excessmsgs, hostname=host, port=port, client_id=client_id, auth=auth)
        except:
            log.warning("Unable to publish message, " + excessmsgs)

        time.sleep(5)

if __name__ == "__main__":
    main(sys.argv)

