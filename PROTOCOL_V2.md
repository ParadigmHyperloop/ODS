# The OpenLoop Telemetry Protocol (Version 2)

_version 1 of the protocol is a proof of concept, ultra-minimal protocol_

# DRAFT

This document is a draft

# Overview

- Minimal Overhead
- Ensured Packet Delivery
- Multiple PODs Supported

# Spec

A Telemetry session is performed over TCP, this ensures packet delivery, 
congestion control, and much more.  Given that the network hardware is 
somewhat of a black box in this competition, we will not overly optimize, 
nor design our own protocol to deal with congestion control or retransmission.

Telemetry is trasmissed in the context of a session. Sessions are stateful and
long-lived, which is non-traditional when compared to other protocols such as 
HTTP. However, as you will see, the fact that the session is stateful or 
long-lived will not be a hinderance to scaling as the control point will have
complete control over when the session is terminated and will be able to 
orchestrate a session transfer should a certain ODS server become overloaded

A Session is divided into 3 states:

- Session Setup
- Telemetry Transmission / Steady State
- Session Tear Down / Transfer

## Session Setup

A session is initiated by the pod when the onboard controller boots up. A
sucessful boot of the controller is contingent on a successful setup of a
telemetry session.

The POD controller will send an initial request to the control point which 
will be load balanced to the appropriate ODS server.  This initial message
contains one time information about the pod and looks like this:

_Note: Each line is delimited with a `\n`.  There is no `\r` in this protocol_

```
POD 1 ODS/1.0
Name: OpenLoop-0001
State: Boot
Version: 1.0.23
Timestamp: 1479200155000000

```

The blank line signifies the end of the setup section of the connection and
the start of the telemetry stream. You may notice that this is very similar
to HTTP/1.x, because it is, however, their are a few differences


```
<Client> <ID> <PROTO>/<PROTO_VERSION>
<KEY>: <VALUE>
<KEY>: <VALUE2>
<KEY2>: <VALUE2>
Timestamp: 1479200155000000
...
<BLANK LINE>
```

* *Client*: Is one of (`POD`, `SIM`, or another type of client)
* *ID*: Is a unique identifier for the pod. ID must be alphanumeric/containing dashed and underscores
* *PROTO*: Is always `ODS`
* *PROTO_VERSION*: Is the version of the `ODS` protocol, the protocol this paper discusses
* *KEY*: A Header Key, see HTTP
* *VALUE*: A Header Value

### Required Headers

There is currently one required header, which is the Timestamp header. 
This header sets a starting timestamp for the session, for which all telemetry points will be 
relative to. This allows for the size of the telemetry point data to be reduced

## Telemetry Transmission

The data format for the telemetry data is as follows for the time being.  
This format will change to be more compressed

* Each telemetry point starts with an 8 bit header
* The telemetry point is assumed to be transmitted in sequential order
* The telemetry point is composed of 3 fields, a timestamp, a name and a value

| X      | Header | Timestamp         | Name    | Value | Pad |
--------------------------------------------------------------|
| Bits   | 8      | 1-64              | 16      | 0-64  | 0-7 |


The header is used to determine the size and mode of the timestamp field

The length of the value field is determined by the Name field.  A pre-determined
set of Name -> Value length mappings will be stored on the ODS server and on the
Controller.  Likewise, a mapping of Name -> Human Readable Name will be stored to
map the integer names to their string equivalents

_To be continued_
