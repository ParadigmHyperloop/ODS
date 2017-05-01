import os
import time
import logging

class RawReader:
    def __init__(self, filename, baudrate=115200):
        self.filename = filename

    def run_safe(self):
        """ Runs the RawReader and restarts it if there is an exception """
        while True:
            try:
                self.start()
            except Exception as e:
                logging.exception(e)
                time.sleep(1)

    def run(self):
        """Runs the RawReader"""
        with open(self.filename) as f:
            for line in f:
                if line:
                    logging.debug("[%s] %s" % (self.filename, line))
                    data = {}
                    for i, v in enumerate(line.split()):
                        data["raw_%d" % i] = float(v)
                    print("%f %s" % (time.time(), data))
