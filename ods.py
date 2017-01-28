#!/usr/bin/env python3
import socket
import struct
import logging
import argparse
from datetime import datetime, timedelta
from influxdb import InfluxDBClient

SKATE_0_MASK = 0x0001
SKATE_1_MASK = 0x0002
SKATE_3_MASK = 0x0004
CLAMP_ENG_0_MASK = 0x0008
CLAMP_REL_0_MASK = 0x0010
CLAMP_ENG_1_MASK = 0x0020
CLAMP_REL_1_MASK = 0x0040
WHEEL_CAL_0_MASK = 0x0080
WHEEL_CAL_1_MASK = 0x0100
WHEEL_CAL_2_MASK = 0x0200
HPFIL_MASK = 0x0400
VENT_MASK = 0x0800
CLAMP_FIL_0_MASK = 0x1000
CLAMP_FIL_1_MASK = 0x2000
LAT_FIL_0_MASK = 0x4000
LAT_FIL_1_MASK = 0x8000

SPACEX_INTERVAL = timedelta(seconds=0.3)


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

    def parse_message(self, msg):
        (state, solenoid_mask, timestamp,
         position_x, position_y, position_z,
         velocity_x, velocity_y, velocity_z,
         acceleration_x, acceleration_y, acceleration_z,
         corner_0, corner_1, corner_2, corner_3,
         wheel_0, wheel_1, wheel_2,
         lateral_0, lateral_1, lateral_2,
         hp_pressure,
         reg_pressure_0, reg_pressure_1, reg_pressure_2, reg_pressure_3,
         clamp_pressure_0, clamp_pressure_1,
         skate_pressure_0, skate_pressure_1,
         lateral_pressure_0, lateral_pressure_1,
         hp_thermo,
         reg_thermo_0, reg_thermo_1, reg_thermo_2, reg_thermo_3,
         reg_surf_thermo_0, reg_surf_thermo_1,
         reg_surf_thermo_2, reg_surf_thermo_3,
         power_thermo_0, power_thermo_1, power_thermo_2, power_thermo_3,
         clamp_thermo_0, clamp_thermo_1,
         frame_thermo,
         voltage_0, voltage_1, voltage_2,
         current_0, current_1, current_2,
         rpm_0, rpm_1, rpm_2,
         stripe_count) = struct.unpack("<IIQ55fI", msg)

        params = {
            "state": state,
            "solenoid_mask": solenoid_mask,
            "SOL_SKATE_0": 1 if (solenoid_mask & SKATE_0_MASK) else 0,
            "SOL_SKATE_1": 1 if (solenoid_mask & SKATE_1_MASK) else 0,
            "SOL_SKATE_3": 1 if (solenoid_mask & SKATE_3_MASK) else 0,
            "SOL_CLAMP_ENG_0": 1 if (solenoid_mask & CLAMP_ENG_0_MASK) else 0,
            "SOL_CLAMP_REL_0": 1 if (solenoid_mask & CLAMP_REL_0_MASK) else 0,
            "SOL_CLAMP_ENG_1": 1 if (solenoid_mask & CLAMP_ENG_1_MASK) else 0,
            "SOL_CLAMP_REL_1": 1 if (solenoid_mask & CLAMP_REL_1_MASK) else 0,
            "SOL_WHEEL_CAL_0": 1 if (solenoid_mask & WHEEL_CAL_0_MASK) else 0,
            "SOL_WHEEL_CAL_1": 1 if (solenoid_mask & WHEEL_CAL_1_MASK) else 0,
            "SOL_WHEEL_CAL_2": 1 if (solenoid_mask & WHEEL_CAL_2_MASK) else 0,
            "SOL_HPFIL": 1 if (solenoid_mask & HPFIL_MASK) else 0,
            "SOL_VENT": 1 if (solenoid_mask & VENT_MASK) else 0,
            "SOL_CLAMP_FIL_0": 1 if (solenoid_mask & CLAMP_FIL_0_MASK) else 0,
            "SOL_CLAMP_FIL_1": 1 if (solenoid_mask & CLAMP_FIL_1_MASK) else 0,
            "SOL_LAT_FIL_0": 1 if (solenoid_mask & LAT_FIL_0_MASK) else 0,
            "SOL_LAT_FIL_1": 1 if (solenoid_mask & LAT_FIL_1_MASK) else 0,
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
            "corner_0": corner_0,
            "corner_1": corner_1,
            "corner_2": corner_2,
            "corner_3": corner_3,
            "wheel_0": wheel_0,
            "wheel_1": wheel_1,
            "wheel_2": wheel_2,
            "lateral_0": lateral_0,
            "lateral_1": lateral_1,
            "lateral_2": lateral_2,
            "hp_pressure": hp_pressure,
            "reg_pressure_0": reg_pressure_0,
            "reg_pressure_1": reg_pressure_1,
            "reg_pressure_2": reg_pressure_2,
            "reg_pressure_3": reg_pressure_3,
            "clamp_pressure_0": clamp_pressure_0,
            "clamp_pressure_1": clamp_pressure_1,
            "skate_pressure_0": skate_pressure_0,
            "skate_pressure_1": skate_pressure_1,
            "lateral_pressure_0": lateral_pressure_0,
            "lateral_pressure_1": lateral_pressure_1,
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
            "voltage_2": voltage_2,
            "current_0": current_0,
            "current_1": current_1,
            "current_2": current_2,
            "rpm_0": rpm_0,
            "rpm_1": rpm_1,
            "rpm_2": rpm_2,
            "stripe_count": stripe_count
        }

        return params

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        sock.bind(self.addrport)
        sock.listen(1)

        while True:
            conn, addr = sock.accept()
            print("New Connection from {}".format(addr))

            while True:
                message = conn.recv(512)
                length = len(message)
                if length == 240:
                    results = self.parse_message(message)
                    print(results)
                    self.store_metrics(results)

                    self.state = results

                    if datetime.now() - self.last_spacex_packet > SPACEX_INTERVAL:
                        pkt = self.make_spacex_packet()
                        self.send_to_spacex(pkt)

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
        self.spacex_sock.sendto(pkt.to_bytes(), self.spacex_addr)

    def make_spacex_packet(self):
        state_mapper = [
            1,  # POST = 0,
            1,  # Boot = 1,
            1,  # LPFill = 2,
            1,  # HPFill = 3,
            1,  # Load = 4,
            1,  # Standby = 5,
            2,  # Armed = 6,
            3,  # Pushing = 7,
            4,  # Coasting = 8,
            5,  # Braking = 9,
            1,  # Vent = 10,
            1,  # Retrieval = 11,
            0,  # Emergency = 12,
            1   # Shutdown = 13,
        ]

        return SpaceXPacket(
            team_id=self.team_id,
            status=state_mapper[self.state['state']],
            position=int(self.state['position_x']) * 100,
            velocity=int(self.state['velocity_x']) * 100,
            acceleration=int(self.state['acceleration_x']) * 100,
            battery_voltage=int(self.state['voltage_0']) * 1000,
            battery_current=int(self.state['current_0']) * 1000,
            battery_temperature=int(self.state['power_thermo_0']) * 10,
            pod_temperature=int(self.state['frame_thermo']) * 10,
            stripe_count=int(self.state['stripe_count'])
        )


def main():
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
    print(("Starting ODS Server on 0.0.0.0:{}".format(args.port)))
    server = ODSServer(("", args.port), args.team_id, spacex_addr, influx)

    # Startup the main main reciever
    server.run()


if __name__ == "__main__":
    main()
