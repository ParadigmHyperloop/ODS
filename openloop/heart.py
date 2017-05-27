import time


class Heart:
    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.running = False

    def start(self):
        self.running = True
        while self.running:
            self.callback(self)
            time.sleep(self.interval)

    def stop(self):
        self.running = False
