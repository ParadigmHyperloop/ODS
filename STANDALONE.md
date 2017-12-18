# Standalone Data Shuttle Operation

This mode of ODS is meant for storing arbitrary test data using 
the same grafana, influxdb, and ODS tooling as we use for flights.

For flights, ODS listens on a UDP port and parses UDP packets 
containing telemetry data formated in a pre-determined fashion.

For standalone mode, ODS tails an arbitrary file and parses each 
line as new metrics. For example, to use ODS raw reader (standalone)
mode with an Arduino, all you need is for the arduino to print 
whitespace delimited values to serial.  

```
void loop() {
  ...
  Serial.print(value1);
  Serial.print(" ");
  Serial.print(value2);
  Serial.print("\n");
  ...
}
```

which looks something like this on the computer connnected to the
arduino (tailing /dev/tty0 or thereabouts)

```
10 20
10 20
10 20
```

You would then launch ODS and tell it to read from `/dev/tty0` 
for raw data.

In this case, ODS just sees lines with number in them, and therefore
it autoassigns names to each value.  Column 0 (value 10) will get assigned
the name `raw_0`, and column 1 (value 20) will be assigned `raw_1`.  This
dataset will then be pushed into influxdb with a timestamp taken from the
host machine.

You can then browse grafana and create queries with the `raw_0` and `raw_1`
metrics.

However, `raw_0` and `raw_1` is ambiguous, and therefore, ODS standalone mode
will parse metrics given in `key=value` form as well. We can instead have the
arduino print out the keys along with the value, or we can have a wrapper script 
process the serial stream for ODS to consume (either works).  Lets say we just have
the arduino output the keys and values.

```
void loop() {
  ...
  Serial.print("belt_temp_0=");
  Serial.print(value1);
  Serial.print(" belt_rpm=");
  Serial.print(value2);
  Serial.print("\n");
  ...
}
```

which manifests as:

```
belt_temp_0=10 belt_rpm=20
belt_temp_0=10 belt_rpm=20
belt_temp_0=10 belt_rpm=20
```

and now we have something that is genuinely usable by the rest of the team
when the datapoints get pushed into grafana.

## Running ODS Standalone

This is as easy as `./ods.py --serial /dev/tty0` where the arduino shows up
at `/dev/tty0`.




