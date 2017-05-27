#!/bin/bash


SERVER="python3 ./ods.py"
SERVER_OUT="server.out"
SERVER_ERR="server.err"
PORT=7778

MOCK_POD="python3 ./tests/mock_pod.py"
FIFO="./data-fifo"
N_ENTRIES=1000
MEASUREMENTS="test test2"
TEST_DATA_FILE="./tests/assets/hyperloop-telemetry.log.bin"

( $MOCK_POD )&
mock_pid=$!

# start the server in the background
# ( $SERVER -p $PORT > $SERVER_OUT 2> $SERVER_ERR )&
( $SERVER -p $PORT )&
server_pid=$!

sleep 1
kill -0 $server_pid

if [ $? -eq 0 ]; then
  function cleanup {
    echo "cleanup: Sending SIGTERM to pid $server_pid"
    kill -SIGTERM $server_pid
    kill -SIGTERM $mock_pid
  }
  trap cleanup EXIT

  # Run with the test data
  cat $TEST_DATA_FILE | nc -u -4 -w 1 localhost $PORT

  echo "=== Test Complete ==="
else
  echo "Server failed to start!"
  echo "make sure there isn't one runing in the background"
  exit 1
fi
