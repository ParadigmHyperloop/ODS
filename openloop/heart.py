import time
import traceback


class Heart:
    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.running = False

    def start(self):
        self.running = True
        print("[Heart] Starting")

        while self.running:
            try:
                self.callback(self)
            except Exception as e:
                print("[Heart] Exception: {}".format(e))

            time.sleep(self.interval)

    def stop(self):
        print("[Heart] Stopped")

        self.running = False
