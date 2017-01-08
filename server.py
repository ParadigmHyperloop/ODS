#!/usr/bin/env python3
##
# Copyright (c) OpenLoop, 2016
#
# This material is proprietary of The OpenLoop Alliance and its members.
# All rights reserved.
# The methods and techniques described herein are considered proprietary
# information. Reproduction or distribution, in whole or in part, is forbidden
# except by express written permission of OpenLoop.
#
# Source that is published publicly is for demonstration purposes only and
# shall not be utilized to any extent without express written permission of
# OpenLoop.
#
# Please see http://www.opnlp.co for contact information
##

import os
from datetime import datetime
import logging
import socketserver
import argparse
import threading
import time
from influxdb import InfluxDBClient

BASE_PATH = '.'


class SpaceXPacket:
    def __init__(self, team_id, status=None, position=None, velocity=None,
                 acceleration=None, battery_voltage=None,
                 battery_current=None, battery_temperature=None,
                 pod_temperature=None, stripe_count=None):
        self.team_id = team_id
        self.status = status
        self.position = position
        self.velocity = velocity
        self.acceleration = acceleration
        self.battery_voltage = battery_voltage
        self.battery_current = battery_current
        self.battery_temperature = battery_temperature
        self.pod_temperature = pod_temperature
        self.stripe_count = stripe_count


class ODSDataHandler:
    def __init__(self, team_id, spacex_addr, influx, name='default'):
        self.influx = influx
        self.spacex_addr = spacex_addr
        self.spacex_packet = SpaceXPacket(team_id)

    def handle(self, data):
        measurements = []
        for name, value in list(data.items()):
            measurements.append({
                    "measurement": name,
                    "tags": {},
                    "time":  datetime.utcnow().isoformat() + "Z",
                    "fields": {"value": value}})
        self.influx.write_points(measurements)


class RawReader:
    def __init__(self, filename, handler):
        self.filename = filename
        self.handler = handler

    def start(self):
        while True:
            try:
                with open(self.filename, 'r') as f:
                    for line in f:
                        logging.info("FIFO Line: %s" % line)

                        data = {}

                        for i, v in enumerate(line.split()):
                            data["raw_%d" % i] = float(v)

                        self.handler.handle(data)
            except OSError as e:
                logging.exception(e)
                time.sleep(5)


class LoggingHandler(socketserver.StreamRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def send_spacex(self):
        pass

    def handle(self):
        startTime = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        log_fname = os.path.join(self.server.base_path, "logging" + startTime + ".csv")
        data_fname = os.path.join(self.server.base_path, "data" + startTime + ".csv")

        self.log_file = open(log_fname, 'w+')
        self.data_file = open(data_fname, 'w+')

        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
        while True:

            self.data = self.rfile.readline().decode('utf-8')

            # if disconnected, then break
            if not self.data:
                logging.error("[DISCONNECT]")
                break

            self.data = self.data.strip("\r\n ")

            logging.debug("[DATA] '{}'".format(self.data))

            response = None

            if self.valid(self.data):
                pkt_type = int(self.data[3])
                if pkt_type == 1:
                    response = self.handle_log(self.data[4:])
                elif pkt_type == 2:
                    response = self.handle_data(self.data[4:])
                else:
                    logging.error("Unknown Type {}".format(pkt_type))
            else:
                logging.warn("[DROP] '{}'".format(self.data))

            # Likewise, self.wfile is a file-like object used to write back
            # to the client
            if response is None:
                self.wfile.write(("FAIL: " + self.data + "\n").encode('utf-8'))
            else:
                self.wfile.write((response + "\n").encode('utf-8'))

    def handle_data(self, msg):
        logging.info("[DATA] {}".format(msg))
        self.data_file.write(makeLine(msg))
        (name, value) = msg.split(' ', 1)

        try:
            value = float(value)
        except ValueError:
            return "ERROR: Bad Value '{}'".format(value)

        self.server.data_handler.handle({name: value})

        return "OK: ({},{})".format(name, value)

    def handle_log(self, msg):
        self.log_file.write(makeLine(msg))

        return "OK: LOGGED"

    def valid(self, s):
        return len(s) >= 4 and s[0:3] == "POD" and isPositiveInt(s[3])


class ODSTCPServer(socketserver.TCPServer):
    def __init__(self, addr, handler, base_path, data_handler):
        self.data_handler = data_handler
        self.base_path = base_path
        super().__init__(addr, handler)


def isPositiveInt(s):
    try:
        return int(s) > 0
    except ValueError:
        return False


def makeLine(msg):
    """Takes a message and prepends a timestamp to it for logging"""
    lineToWrite = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return lineToWrite + msg + "\n"


if "__main__" == __name__:
    parser = argparse.ArgumentParser(description="Openloop Data Shuttle")

    parser.add_argument("-v", "--verbose", action="store_true")

    parser.add_argument("-p", "--port", type=int, default=7778,
                        help="Server listen port")

    parser.add_argument("-d", "--directory", default='.',
                        help="directory to store raw log and data files in")
    parser.add_argument("-s", "--serial", default=None,
                        help="Serial desive that spits out raw data")

    # Used for the SpaceX data stream format
    parser.add_argument("--spacex-host", default=None,
                        help="The hostname/ip of the SpaceX data reciever")
    parser.add_argument("--spacex-port", default=0, type=int,
                        help="The SpaceX data reciever port")
    parser.add_argument("--team-id", default=0, type=int,
                        help="The team id assigned by spacex")

    # Influx arguments
    parser.add_argument("--influx-host", default='127.0.0.1',
                        help="Influxdb hostname")

    parser.add_argument("--influx-port", default=8086, type=int,
                        help="Influxdb port")

    parser.add_argument("--influx-user", default='root',
                        help="Influxdb username")

    parser.add_argument("--influx-pass", default='root',
                        help="Influxdb password")

    parser.add_argument("--influx-name", default='example',
                        help="Influxdb database name")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Create connection to influx database
    influx = InfluxDBClient(args.influx_host, args.influx_port,
                            args.influx_user, args.influx_pass,
                            args.influx_name)

    influx.create_database(args.influx_name)

    # Setup the data handler, tell it about the spacex server
    spacex_addr = (args.spacex_host, args.spacex_port)
    data_handler = ODSDataHandler(args.team_id, spacex_addr, influx)

    # Startup the main main TCP reciever
    print(("Starting ODS Server on 0.0.0.0:{}".format(args.port)))
    server = ODSTCPServer(("0.0.0.0", args.port), LoggingHandler,
                          args.directory, data_handler)

    t = threading.Thread(target=server.serve_forever)
    t.start()

    if args.serial:
        logging.info("Starting raw serial reader on: %s" % args.serial)
        RawReader(filename=args.serial, handler=data_handler).start()

    t.join()
