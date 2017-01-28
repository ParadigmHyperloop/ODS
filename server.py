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
import socket
import struct
from influxdb import InfluxDBClient

BASE_PATH = '.'
PACKET_SIZE = 248

def hexdump(data):
    s = ""
    for b in data:
        s += str(hex(b))
    return s


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


class ODSDataHandler:
    def __init__(self, team_id, spacex_addr, influx, name='default'):
        self.influx = influx
        self.spacex_addr = spacex_addr
        self.spacex_sock = None
        self.spacex_packet = SpaceXPacket(team_id)
        self.connect_spacex()

    def handle(self, data):
        measurements = []
        for name, value in list(data.items()):
            measurements.append({
                    "measurement": name,
                    "tags": {},
                    "time":  datetime.utcnow().isoformat() + "Z",
                    "fields": {"value": value}})
        self.influx.write_points(measurements)

    def connect_spacex(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.spacex_sock = sock

    def send_to_spacex(self, packet):
        raw = packet.to_bytes()
        self.spacex_sock.sendto(raw, self.spacex_addr)


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
            except Exception as e:
                logging.exception(e)


class LoggingHandler(socketserver.StreamRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def send_spacex(self):
        # 0: Fault – If seen, will cause SpaceX to abort the tube run.
        #
        # 1: Idle – Any state where the pod is on, but not ready to be pushed.
        #
        # 2: Ready – Any state where the pod is ready to be pushed.
        #
        # 3: Pushing – Any state when the pod detects it is being pushed.
        #
        # 4: Coast – Any state when the pod detects it has separated from the
        #            pusher vehicle.
        #
        # 5: Braking – Any state when the pod is applying its brakes.

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

        spx = SpaceXPacket(
            team_id=self.data_handler.team_id,
            status=state_mapper[self.server.state['state']],
            position=self.server.state['position_x'] * 100,
            velocity=self.server.state['velocity_x'] * 100,
            acceleration=self.server.state['acceleration_x'] * 100,
            battery_voltage=self.server.state['voltage_0'] * 1000,
            battery_current=self.server.state['current_0'] * 1000,
            battery_temperature=self.server.state['battery_thermo_0'] * 10,
            pod_temperature=self.server.state['frame_thermo'] * 10,
            stripe_count=0
        )

        raw = spx.to_bytes()

        self.server.send_to_spacex(raw)

    def handle(self):
        logging.debug("[NEW] Connection")
        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
        while True:
            self.data = self.rfile.read(PACKET_SIZE)

            # if disconnected, then break
            if not self.data:
                logging.error("[DISCONNECT]")
                break

            print(hexdump(self.data))
            print("len: %d" % len(self.data))

            response = None

            self.handle_data(self.data)

    def handle_data(self, msg):
        (version, length, state, solenoid_mask, timestamp, position_x,
         position_y, position_z, velocity_x, velocity_y, velocity_z,
         acceleration_x, acceleration_y, acceleration_z, corner_0,
         corner_1, corner_2, corner_3, wheel_0, wheel_1, wheel_2,
         lateral_0, lateral_1, lateral_2, hp_pressure, reg_pressure_0,
         reg_pressure_1, reg_pressure_2, reg_pressure_3,
         clamp_pressure_0, clamp_pressure_1, skate_pressure_0,
         skate_pressure_1, hp_thermo, reg_thermo_0, reg_thermo_1,
         reg_thermo_2, reg_thermo_3, reg_surf_thermo_0,
         reg_surf_thermo_1, reg_surf_thermo_2, reg_surf_thermo_3,
         power_thermo_0, power_thermo_1, power_thermo_2,
         power_thermo_3, frame_thermo, voltage_0, voltage_1, voltage_2,
         current_0, current_1, current_2, battery_thermo_0,
         battery_thermo_1, battery_thermo_2, rpm_0, rpm_1, rpm_2,
         stripe_count) = struct.unpack("!bHbHQ54fH", msg)

        """typedef struct telemetry_packet {
          uint8_t version;
          uint16_t length;
          // state
          pod_mode_t state;
          // Solenoids
          relay_mask_t solenoids;
          uint64_t timestamp;
          // IMU
          float position_x;
          float position_y;
          float position_z;

          float velocity_x;
          float velocity_y;
          float velocity_z;

          float acceleration_x;
          float acceleration_y;
          float acceleration_z;

          // Distance sensors
          float corners[N_CORNER_DISTANCE];
          float wheels[N_WHEEL_DISTANCE];
          float lateral[N_LATERAL_DISTANCE];

          // Pressures
          float hp_pressure;
          float reg_pressure[N_REG_PRESSURE];
          float clamp_pressure[N_CLAMP_PRESSURE];
          float skate_pressure[N_SKATE_PRESSURE];

          // Thermocouples
          float hp_thermo;
          float reg_thermo[N_REG_THERMO];
          float reg_surf_thermo[N_REG_SURF_THERMO];
          float power_thermo[POWER_THERMO_MUX];
          float frame_thermo;

          // Batteries
          float voltages[N_BATTERIES]; // hopefully 3
          float currents[N_BATTERIES];
          float battery_thermo[N_BATTERIES];

          // Photo
          float rpms[N_WHEEL_PHOTO];
          uint16_t stripe_count;
        } telemetry_packet_t;
        """

        print("accel: %f %f %f" % (acceleration_x, acceleration_y,
                                   acceleration_z))

        print("clamp psi: %f %d" % (clamp_pressure_0, clamp_pressure_1))

        self.server.state = {
            "version": version,
            "length": length,
            "state": state,
            "solenoid_mask": solenoid_mask,
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
            "power_thermo_3": power_thermo_3,
            "frame_thermo": frame_thermo,
            "voltage_0": voltage_0,
            "voltage_1": voltage_1,
            "voltage_2": voltage_2,
            "current_0": current_0,
            "current_1": current_1,
            "current_2": current_2,
            "battery_thermo_0": battery_thermo_0,
            "battery_thermo_1": battery_thermo_1,
            "battery_thermo_2": battery_thermo_2,
            "rpm_0": rpm_0,
            "rpm_1": rpm_1,
            "rpm_2": rpm_2,
            "stripe_count": stripe_count
        }

        self.server.data_handler.handle(self.server.state)

        return "OK"

    def handle_log(self, msg):
        self.log_file.write(makeLine(msg))

        return "OK: LOGGED"

    def valid(self, s):
        return len(s) >= 4 and s[0] == "POD" and isPositiveInt(s[3])


class ODSTCPServer(socketserver.TCPServer):
    def __init__(self, addr, handler, base_path, data_handler):
        self.data_handler = data_handler
        self.base_path = base_path
        self.state = {}
        self.allow_reuse_address = True
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
