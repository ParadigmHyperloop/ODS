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
import time
import socket
import logging
import argparse
import sys
import select
import threading
import traceback
from openloop.ansi import Ansi
from datetime import datetime, timedelta
from openloop.pod import Pod
from openloop.heart import Heart


PROMPT_TRACK = 0
LAST_PROMPT = ""


def progress():
    global PROMPT_TRACK
    PROMPT_TRACK = (PROMPT_TRACK + 1) % 5
    return "." * PROMPT_TRACK + " " * (4-PROMPT_TRACK)


def user_write(txt):
    if txt is not None:
        sys.stdout.write(txt)
        sys.stdout.flush()


def make_prompt(pod, extra="> "):
    global LAST_PROMPT

    details = "%s:%d" % pod.addr
    if pod.state is not None:
        details += " %s" % pod.state.short()
        if pod.state.is_fault():
            details = Ansi.make_red(details)
        else:
            details = Ansi.make_green(details)
    else:
        walker = progress()
        details = Ansi.make_yellow(details + " " + walker)

    text = Ansi.make_bold("Pod(%s)%s" % (details, extra))
    raw = Ansi.strip(text)

    if len(Ansi.strip(LAST_PROMPT)) > len(raw):
        text += " " * (len(LAST_PROMPT) - len(raw))

    LAST_PROMPT = text.rstrip()
    return text


def loop(pod):
    cached_state = None
    user_write("\r" + make_prompt(pod))

    while not pod.is_connected():
        try:
            logging.debug("Attempting Connection")
            pod.connect()
        except Exception as e:
            logging.debug("Connection Exception: %s" % e)
            user_write("\r" + make_prompt(pod, " ! {} ".format(e)))
        time.sleep(1)
    logging.debug("Connected")

    # Welcome Prompt
    user_write("\n")
    user_write(pod.run("help"))
    user_write(make_prompt(pod))

    while pod.is_connected():
        (ready, _, _) = select.select([sys.stdin], [], [], 0.1)

        if sys.stdin in ready:
            try:
                cmd = input()
            except EOFError:
                logging.debug("EOF")
                sys.exit(0)

            print(pod.run(cmd))
            user_write(make_prompt(pod))

        if pod.state != cached_state:
            user_write("\r" + make_prompt(pod))
            cached_state = pod.state


def main():
    parser = argparse.ArgumentParser(description="Openloop Command Client",
                                     add_help=False)

    parser.add_argument("-v", "--verbose", action="store_true", default=False)

    parser.add_argument("-p", "--port", type=int, default=7779,
                        help="Pod server port")

    parser.add_argument("-h", "--host", default="127.0.0.1",
                        help="Pod server hostname")

    parser.add_argument("-i", "--heartbeat-interval", default="200", type=int,
                        help="heartbeat interval (ms)")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Debug Logging Enabled")
    else:
        logging.basicConfig(level=logging.WARN)

    pod = Pod((args.host, args.port))

    def handle_timeout():
        user_write("\r" + make_prompt(pod, Ansi.make_bold("> Ping Timeout!")))
    pod.timeout_handler = handle_timeout

    heart = Heart(args.heartbeat_interval / 1000.0, pod.ping)

    threading.Thread(target=heart.start).start()

    while True:
        try:
            loop(pod)
        except SystemExit:
            heart.stop()
            raise
        except KeyboardInterrupt:
            print("Keyboard Interupt... shutdown")
            heart.stop()
            sys.exit(1)
        except Exception as e:
            print("[ERROR] %s" % e)
            traceback.print_exc()


if "__main__" == __name__:
    main()
