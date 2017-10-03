# OpenLoop Data Shuttle [![Build Status](https://travis-ci.org/openloopalliance/ODS.svg?branch=master)](https://travis-ci.org/openloopalliance/ODS)

_All the Telemetry_

This service runs at the Control Point and is the direct recipient of all
telemetry data from all PODs on the PODNET

# Overview

The ODS is a required service to operate the Paradigm Pod. Without a valid
telemetry server connection, the OpenLoop Pod will refuse to proceed to a
Post-boot stage.  See
[the core control code](https://github.com/ParadigmHyperloop/hyperloop).

ODS is responsible for:

* Receiving all telemetry from the vehicle (UDP)
* Storing Telemetry in an InfluxDB server
* Caching and serving telemetry to the [Web UI](https://github.com/ParadigmHyperloop/web)
* Maintaining a persistent heartbeat with the pod
  * Handling network disconnects/failures appropriately
* Relaying Commands from the Web UI to the pod
* Forwarding telemetry to SpaceX using the SpaceX UDP Telemetry Format (a `SpaceXPacket`)

## The 5 second ASCII diagram

_This is far from the actual diagram... it is meant to give you a 10,000 foot
picture_

```
             Control Point

+--------------------+
|                    |
| InfluxDB & Grafana |
|                    |
+--------------------+
      ^
      |
+------------+    +-------------+
|            |    |             |
| ODS Server | -- |   Web GUI   |   
|            |    |             |
+---------+--+    +-------------+
      ^   |                      
===== |   +---------------+ ========= Network Boundary (NAP)
      |                   |         
+--------------------+ +--+-------------+
|                    | |                |
|   Logging Client   | | Command Server |
|                    | |                |
+--------------------+ +-------+--------+
     ^                         |
     |       Paradigm Pod      |
     |                         |
+------------------------------+--------+
|                                       |
|         Core Control Thread           |
|                                       |
+---------------------------------------+
```

# Setup and Usage

## Prerequisites

* A sane python 3 environment (use virtualenv).
* InfluxDB (`brew install influxdb`)
* Grafana (`brew install grafana`)

## Running

If you have Influxdb running on your localhost and the [core control code](https://github.com/ParadigmHyperloop/hyperloop) is running on your computer, then you can just run `./ods.py --pod-addr="127.0.0.1"`.  Otherwise,
use the following arguments to tell the ODS server where you have InfluxDB
running so that it can dump the incoming telemetry data.

```
usage: ods.py [-h] [-v] [-p PORT] [-d DIRECTORY] [-s SERIAL]
              [--spacex-host SPACEX_HOST] [--spacex-port SPACEX_PORT]
              [--team-id TEAM_ID] [--http-host HTTP_HOST]
              [--http-port HTTP_PORT] [--influx-host INFLUX_HOST]
              [--influx-port INFLUX_PORT] [--influx-user INFLUX_USER]
              [--influx-pass INFLUX_PASS] [--influx-name INFLUX_NAME]
              [--web-root WEB_ROOT] [--pod-addr POD_ADDR]
              [--pod-port POD_PORT]

Paradigm (formerly Openloop) Data Shuttle

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose
  -p PORT, --port PORT  Server listen port
  -d DIRECTORY, --directory DIRECTORY
                        directory to store raw log and data files in
  -s SERIAL, --serial SERIAL
                        Serial device that spits out raw data
  --spacex-host SPACEX_HOST
                        IP of the SpaceX data reciever (192.168.0.1)
  --spacex-port SPACEX_PORT
                        The SpaceX data reciever port
  --team-id TEAM_ID     The team id assigned by spacex
  --http-host HTTP_HOST
                        The hostname/ip to bind the HTTP Server to
  --http-port HTTP_PORT
                        The port to bind the HTTP Server to
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
  --web-root WEB_ROOT   Path to the Pod Web Static Files
  --pod-addr POD_ADDR   IP of the pod
  --pod-port POD_PORT   Command Port on the pod
```


To run ODS for competitions use:

```
./ods.py --pod-addr="192.168.0.10" --spacex-host="192.168.0.1" --spacex-port=3000 --team-id=11
```


To run ODS for testing with the pod:

```
./ods.py --pod-addr="192.168.0.10"
```

To run ODS local full-system HOOTL testing, along with the `packet_test_server.py` script found in Google Drive, along with the core control code.

```
./ods.py --pod-addr="127.0.0.1" --spacex-host="127.0.0.1" --spacex-port=3000 --team-id=11
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
