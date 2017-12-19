import os
import time
import logging
from datetime import datetime


class RawReader:
    def __init__(self, filename, baudrate=115200, influx=None):
        self.filename = filename
        self.influx = influx

    def run_safe(self):
        """ Runs the RawReader and restarts it if there is an exception """
        while True:
            try:
                self.run()
            except Exception as e:
                logging.exception(e)

    def run(self):
        """Runs the RawReader"""
        with open(self.filename) as f:
            for line in f:
                if line:
                    logging.debug("[%s] %s" % (self.filename, line))
                    data = {}
                    for i, v in enumerate(line.split()):
                        name = "raw_%d" % i
                        if '=' in v:
                            name = v.split('=')[0]
                            v = v.split('=')[1]
                        data[name] = float(v)

                    print("%f %s" % (time.time(), data))
                    self.store_metrics(data)

    def store_metrics(self, data):
        if self.influx:
            measurements = []
            for name, value in list(data.items()):
                measurements.append({
                        "measurement": name,
                        "tags": {},
                        "time":  datetime.utcnow().isoformat() + "Z",
                        "fields": {"value": value}})
            self.influx.write_points(measurements)
            print("... Stored!")
