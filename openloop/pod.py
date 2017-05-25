import socket
import logging
import select
import threading
from datetime import datetime, timedelta


MAX_MESSAGE_SIZE = 2048
PING_TIMEOUT = timedelta(seconds=1)


class PodStateType(type):
    MAP = {
        'POST': 0,
        'BOOT': 1,
        'LPFILL': 2,
        'HPFILL': 3,
        'LOAD': 4,
        'STANDBY': 5,
        'ARMED': 6,
        'PUSHING': 7,
        'COASTING': 8,
        'BRAKING': 9,
        'VENT': 10,
        'RETRIEVAL': 11,
        'EMERGENCY': 12,
        'SHUTDOWN': 13
    }

    SHORT_MAP = {
        'POST': 0,
        'BOOT': 1,
        'LPFL': 2,
        'HPFL': 3,
        'LOAD': 4,
        'STBY': 5,
        'ARMD': 6,
        'PUSH': 7,
        'COAS': 8,
        'BRKE': 9,
        'VENT': 10,
        'RETR': 11,
        'EMRG': 12,
        'SDWN': 13
    }

    def __getattr__(cls, name):
        if name in cls.MAP:
            return cls.MAP[name]
        raise AttributeError(name)


class PodState(metaclass=PodStateType):
    def __init__(self, state):
        self.state = int(state)

    def is_fault(self):
        return self.state == PodState.EMERGENCY

    def is_moving(self):
        return self.state in (PodState.BRAKING, PodState.COASTING,
                              PodState.PUSHING)

    def __str__(self):
        keys = [key for key, val in PodState.MAP.items() if val == self.state]
        if not keys:
            return "UNKNOWN"
        else:
            return keys[0]

    def short(self):
        keys = [key for key, val in PodState.SHORT_MAP.items()
                if val == self.state]
        if not keys:
            return "----"
        else:
            return keys[0]

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.state == other.state
        return False


class Pod:
    def __init__(self, addr):
        self.sock = None
        self.addr = addr
        self.recieved = 0
        self.state = None
        self.lock = threading.Lock()
        self.timeout_handler = None

    def ping(self, _):
        if self.is_connected():
            response = self.run("ping", timeout=PING_TIMEOUT)
            if response is None:
                if self.timeout_handler is not None:
                    self.timeout_handler()
                self.close()
                self.state = None
            else:
                if 'PONG:' in response:
                    self.state = PodState(response.strip().split(':')[1])

    def run(self, cmd, timeout=None):
        if timeout is None:
            timeout = timedelta(seconds=1)

        if self.lock.acquire():
            self.send(cmd + "\n")
            data = self.recv(timeout=timeout)
            self.lock.release()
            return data

        raise RuntimeError("Failed to acquire Lock on Channel %s" % self)

    def transcribe(self, data):
        logging.info("[DATA] {}".format(data))

    def send(self, data):
        if not self.is_connected():
            raise RuntimeError("Pod is not connected")

        try:
            logging.debug("Sending {}".format(data))
            self.sock.send(data.encode('utf-8'))
        except Exception as e:
            self.close()
            raise e

    def recv(self, timeout=None):
        if not self.is_connected():
            return

        try:
            (ready, _, _) = select.select([self.sock], [], [],
                                          timeout.total_seconds())
            if self.sock in ready:
                data = self.sock.recv(MAX_MESSAGE_SIZE).decode('utf-8')
                logging.debug("Sending {}".format(data))
                return data
            return None
        except Exception as e:
            self.close()
            raise e

    def connect(self):
        try:
            self.sock = socket.create_connection(self.addr, 1)

            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

            self.recieved = 0
            self.last_ping = datetime.now()
        except Exception as e:
            self.close()
            raise e

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def is_connected(self):
        return self.sock is not None and self.sock.fileno() >= 0

    def __str__(self):
        return "%s:%d" % self.addrport
