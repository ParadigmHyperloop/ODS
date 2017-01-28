# OpenLoop Data Shuttle [![Build Status](https://travis-ci.org/openloopalliance/ODS.svg?branch=master)](https://travis-ci.org/openloopalliance/ODS)

_All the Telemetry_

This service runs at the Control Point and is the direct recipient of all
telemetry data from all PODs on the PODNET

# Overview

The ODS is a required service to operate the OpenLoop Pod. Without a valid
telemetry server connection, the OpenLoop Pod will refuse to proceed to a
Post-boot stage.  See
[hyperloop-core](https://github.com/openloopalliance/hyperloop-core).

## The 5 second ASCII diagram

_This is far from the actual diagram... it is meant to give you a 10,000 foot
picture_

```
             Control Point

+-------------+
|             |
| Grafana GUI |
|             |
+-------------+
      ^
      |
+------------+ +-------------+ +-------------+
|            | |             | |             |
| ODS Server | | Command CLI | | Command GUI |     More Control Point
|            | |             | |             |
+------------+ +----------+--+ +----+--------+
      ^                   |         |
===== | ================= | ======= | ========= Network Boundary (NAP)
      |                   |         |
+--------------------+ +--+---------+---+
|                    | |                |
| POD Logging Client | | Command Server |
|                    | |                |
+--------------------+ +-------+--------+
     ^                         |
     |       OpenLoop Pod      |
     |                         |
+------------------------------+--------+
|                                       |
|           Core Controller             |
|                                       |
+---------------------------------------+
```

# Setup and Usage

## Prerequisites

* A sane python 2.7 environment.
* InfluxDB
* Grafana

## Running

If you have Influxdb running on your localhost and the pod is on the same
network as your computer, then you can just run `./server.py`.  Otherwise,
use the following arguments to tell the ODS server where you have InfluxDB
running so that it can dump the incoming telemetry data.

```
$ ./server.py --help
usage: server.py [-h] [-v] [-p PORT] [-d DIRECTORY]
                 [--influx-host INFLUX_HOST] [--influx-port INFLUX_PORT]
                 [--influx-user INFLUX_USER] [--influx-pass INFLUX_PASS]
                 [--influx-name INFLUX_NAME]

OpenLoop Data Shuttle

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose
  -p PORT, --port PORT  Server listen port
  -d DIRECTORY, --directory DIRECTORY
                        directory to store raw log and data files in
  --influx-host INFLUX_HOST
                        Influxdb hostname
  --influx-port INFLUX_PORT
                        Influxdb port
  --influx-user INFLUX_USER
                        Influxdb username
  --influx-pass INFLUX_PASS
                        Influxdb password
  --influx-name INFLUX_NAME
                        Influxdb database name
```

# License

See the [LICENSE](LICENSE) for full licensing details.

In summary, (you still need to read the whole thing), this code is for
OpenLoop and OpenLoop only. It is shared with the world for the benefit of
observers and potential developers. If you wish to utilize this code in any
way, you must contact us first and receive written permission to utilize the
source for the purpose you require.

Lastly, DON'T trust this code to work for your HyperLoop pod, or your project.
This code is only being verified and tested on the OpenLoop platform.
