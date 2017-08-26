#!/usr/bin/env python3
import socket
import struct
import logging
import argparse
import threading
import time
from datetime import datetime, timedelta
from influxdb import InfluxDBClient
from raw_reader import RawReader
from openloop.http.app import set_ods, set_pod, app, WEB_ROOT
from openloop.pod import Pod
from openloop.heart import Heart

PACKET_LENGTH = 216

SKATE_0_MASK = 0x0001
SKATE_1_MASK = 0x0002
SKATE_2_MASK = 0x0004
SKATE_3_MASK = 0x0008
CLAMP_ENG_0_MASK = 0x0010
CLAMP_REL_0_MASK = 0x0020
CLAMP_ENG_1_MASK = 0x0040
CLAMP_REL_1_MASK = 0x0080
WHEEL_CAL_0_MASK = 0x0080
HPFIL_MASK = 0x0100
VENT_MASK = 0x0200
PUSH_MASK = 0x0400

SPACEX_INTERVAL = timedelta(seconds=0.3)


class SpaceXStatus:
    FAULT = 0
    IDLE = 1
    READY = 2
    PUSHING = 3
    COASTING = 4
    BRAKING = 5


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
        self.current_sender = None

    def to_bytes(self):
        """Convert to bytes"""
        pattern = '!BBi7I'

        b = struct.pack(pattern, self.team_id, self.status, self.acceleration,
                        self.position, self.velocity, self.battery_voltage,
                        self.battery_current, self.battery_temperature,
                        self.pod_temperature, self.stripe_count)

        return b


class ODSServer:
    def __init__(self, addrport, team_id, spacex_addr, influx):
        self.addrport = addrport
        self.influx = influx
        self.spacex_addr = spacex_addr
        self.team_id = team_id
        self.spacex_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.last_spacex_packet = datetime.now()
        self.state = {}

    def get_state(self):
        return self.state

    def parse_message(self, msg):
        (version, size, state, solenoid_mask, timestamp,
         position_x, position_y, position_z,
         velocity_x, velocity_y, velocity_z,
         acceleration_x, acceleration_y, acceleration_z,
         pusher_0, pusher_1, pusher_2, pusher_3,
         levitation_0, levitation_1, levitation_2, levitation_3,
         levitation_4, levitation_5, levitation_6, levitation_7,
         hp_pressure,
         reg_pressure_0, reg_pressure_1, reg_pressure_2, reg_pressure_3,
         clamp_pressure_0, clamp_pressure_1,
         brake_tank_0, brake_tank_1,
         hp_thermo,
         reg_thermo_0, reg_thermo_1, reg_thermo_2, reg_thermo_3,
         reg_surf_thermo_0, reg_surf_thermo_1,
         reg_surf_thermo_2, reg_surf_thermo_3,
         power_thermo_0, power_thermo_1, power_thermo_2, power_thermo_3,
         clamp_thermo_0, clamp_thermo_1,
         frame_thermo,
         voltage_0, voltage_1,
         current_0, current_1) = struct.unpack("<BHBIQ50f", msg)

        params = {
            "state": state,
            "version": version,
            "solenoid_mask": solenoid_mask,
            "SOL_SKATE_0": 1 if (solenoid_mask & SKATE_0_MASK) else 0,
            "SOL_SKATE_1": 1 if (solenoid_mask & SKATE_1_MASK) else 0,
            "SOL_SKATE_2": 1 if (solenoid_mask & SKATE_2_MASK) else 0,
            "SOL_SKATE_3": 1 if (solenoid_mask & SKATE_3_MASK) else 0,
            "SOL_CLAMP_ENG_0": 1 if (solenoid_mask & CLAMP_ENG_0_MASK) else 0,
            "SOL_CLAMP_REL_0": 1 if (solenoid_mask & CLAMP_REL_0_MASK) else 0,
            "SOL_CLAMP_ENG_1": 1 if (solenoid_mask & CLAMP_ENG_1_MASK) else 0,
            "SOL_CLAMP_REL_1": 1 if (solenoid_mask & CLAMP_REL_1_MASK) else 0,
            "SOL_HPFIL": 1 if (solenoid_mask & HPFIL_MASK) else 0,
            "SOL_VENT": 1 if (solenoid_mask & VENT_MASK) else 0,
            "pusher_present": 1 if (solenoid_mask & PUSH_MASK) else 0,
            "timestamp": timestamp,
            "position_x": position_x,
            "position_y": position_y,
            "position_z": position_z,
            "velocity_x": velocity_x,
            "velocity_y": velocity_y,
            "velocity_z": velocity_z,
            "acceleration_x": acceleration_x,
            "acceleration_y": acceleration_y,
            "acceleration_z": acceleration_z,
            "levitation_0": levitation_0,
            "levitation_1": levitation_1,
            "levitation_2": levitation_2,
            "levitation_3": levitation_3,
            "levitation_4": levitation_4,
            "levitation_5": levitation_5,
            "levitation_6": levitation_6,
            "levitation_7": levitation_7,
            "pusher_0": pusher_0,
            "pusher_1": pusher_1,
            "pusher_2": pusher_2,
            "pusher_3": pusher_3,
            "hp_pressure": hp_pressure,
            "reg_pressure_0": reg_pressure_0,
            "reg_pressure_1": reg_pressure_1,
            "reg_pressure_2": reg_pressure_2,
            "reg_pressure_3": reg_pressure_3,
            "clamp_pressure_0": clamp_pressure_0,
            "clamp_pressure_1": clamp_pressure_1,
            "brake_tank_0": brake_tank_0,
            "brake_tank_1": brake_tank_1,
            "hp_thermo": hp_thermo,
            "reg_thermo_0": reg_thermo_0,
            "reg_thermo_1": reg_thermo_1,
            "reg_thermo_2": reg_thermo_2,
            "reg_thermo_3": reg_thermo_3,
            "reg_surf_thermo_0": reg_surf_thermo_0,
            "reg_surf_thermo_1": reg_surf_thermo_1,
            "reg_surf_thermo_2": reg_surf_thermo_2,
            "reg_surf_thermo_3": reg_surf_thermo_3,
            "power_thermo_0": power_thermo_0,
            "power_thermo_1": power_thermo_1,
            "power_thermo_2": power_thermo_2,
            "clamp_thermo_0": clamp_thermo_0,
            "clamp_thermo_1": clamp_thermo_1,
            "frame_thermo": frame_thermo,
            "voltage_0": voltage_0,
            "voltage_1": voltage_1,
            "current_0": current_0,
            "current_1": current_1,

        }

        return params

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.bind(self.addrport)

        while True:
            message, addr = sock.recvfrom(PACKET_LENGTH)
            length = len(message)
            if length == PACKET_LENGTH:
                results = self.parse_message(message)
                self.store_metrics(results)
                print(results)
                self.state = results

                if datetime.now() - self.last_spacex_packet > SPACEX_INTERVAL:
                    pkt = self.make_spacex_packet()
                    self.send_to_spacex(pkt)

                self.current_sender = addr
            elif length == 0:
                break
            else:
                print("Incorrect message length: %d" % length)

    def store_metrics(self, data):
        measurements = []
        for name, value in list(data.items()):
            measurements.append({
                    "measurement": name,
                    "tags": {},
                    "time":  datetime.utcnow().isoformat() + "Z",
                    "fields": {"value": value}})
        self.influx.write_points(measurements)

    def send_to_spacex(self, pkt):
        """Send to SpaceX over UDP"""
        if self.spacex_sock and self.spacex_addr:
            self.spacex_sock.sendto(pkt.to_bytes(), self.spacex_addr)

    def make_spacex_packet(self):
        state_mapper = [
            SpaceXStatus.IDLE,      # POST = 0,
            SpaceXStatus.IDLE,      # Boot = 1,
            SpaceXStatus.IDLE,      # LPFill = 2,
            SpaceXStatus.IDLE,      # HPFill = 3,
            SpaceXStatus.IDLE,      # Load = 4,
            SpaceXStatus.IDLE,      # Standby = 5,
            SpaceXStatus.READY,     # Armed = 6,
            SpaceXStatus.PUSHING,   # Pushing = 7,
            SpaceXStatus.COASTING,  # Coasting = 8,
            SpaceXStatus.BRAKING,   # Braking = 9,
            SpaceXStatus.IDLE,      # Vent = 10,
            SpaceXStatus.IDLE,      # Retrieval = 11,
            SpaceXStatus.FAULT,     # Emergency = 12,
            SpaceXStatus.IDLE       # Shutdown = 13,
        ]

        spacex_status = 0
        if self.state['state'] in state_mapper:
            spacex_status = state_mapper[self.state['state']]

        return SpaceXPacket(
            team_id=self.team_id,
            status=spacex_status,
            position=int(self.state['position_x']) * 100,
            velocity=int(self.state['velocity_x']) * 100,
            acceleration=int(self.state['acceleration_x']) * 100,
            battery_voltage=int(self.state['voltage_0']) * 1000,
            battery_current=int(self.state['current_0']) * 1000,
            battery_temperature=int(self.state['power_thermo_0']) * 10,
            pod_temperature=int(self.state['frame_thermo']) * 10,
            stripe_count=int(0)
        )


def main():
    parser = argparse.ArgumentParser(description="Openloop Data Shuttle")

    parser.add_argument("-v", "--verbose", action="store_true")

    parser.add_argument("-p", "--port", type=int, default=7778,
                        help="Server listen port")

    parser.add_argument("-d", "--directory", default='.',
                        help="directory to store raw log and data files in")
    parser.add_argument("-s", "--serial", default=None,
                        help="Serial device that spits out raw data")

    # Used for the SpaceX data stream format
    parser.add_argument("--spacex-host", default=None,
                        help="IP of the SpaceX data reciever (192.168.0.1)")
    parser.add_argument("--spacex-port", default=3000, type=int,
                        help="The SpaceX data reciever port")
    parser.add_argument("--team-id", default=0, type=int,
                        help="The team id assigned by spacex")

    # HTTP Server Arguments
    parser.add_argument("--http-host", default='0.0.0.0',
                        help="The hostname/ip to bind the HTTP Server to")
    parser.add_argument("--http-port", default=7777, type=int,
                        help="The port to bind the HTTP Server to")

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

    parser.add_argument("--web-root", default='../web/src',
                        help="Path to the Pod Web Static Files")

    parser.add_argument("--pod-addr", default='192.168.0.10',
                        help="IP of the pod")

    parser.add_argument("--pod-port", default=7779, type=int,
                        help="Command Port on the pod")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.serial:
        print("Starting raw serial reader on: %s" % args.serial)
        raw = RawReader(filename=args.serial)
        threading.Thread(target=raw.run_safe).start()

    # Create connection to influx database
    influx = InfluxDBClient(args.influx_host, args.influx_port,
                            args.influx_user, args.influx_pass,
                            args.influx_name)

    influx.create_database(args.influx_name)

    spacex_addr = None
    # Setup the data handler, tell it about the spacex server
    if args.spacex_host:
        print(("Forwarding Telemetry to %s:%d" % (args.spacex_host,
                                                  args.spacex_port)))
        spacex_addr = (args.spacex_host, args.spacex_port)

    print(("Starting ODS Server on udp://0.0.0.0:%d" % args.port))
    server = ODSServer(("", args.port), args.team_id, spacex_addr, influx)
    set_ods(server)

    pod_addr = (args.pod_addr, args.pod_port)
    pod = Pod(pod_addr)

    set_pod(pod)

    print("Connecting to pod tcp://%s:%d" % pod_addr)
    while not pod.is_connected():
        try:
            pod.connect()
        except Exception as e:
            print(e)
        time.sleep(1)

    http_addr = (args.http_host, args.http_port)
    print("Starting HTTP Server on tcp://%s:%d" % http_addr)

    WEB_ROOT = args.web_root

    heart = Heart(10, pod.ping)

    t1 = threading.Thread(target=server.run)
    t2 = threading.Thread(target=app.run, args=list(http_addr))
    t3 = threading.Thread(target=heart.start)

    t1.start()
    t2.start()
    t3.start()

    # Maintain Connection if it fails
    while not pod.is_connected():
        try:
            pod.connect()
        except Exception as e:
            print(e)
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt as e:
        pass
