#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2017 theloop Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import logging
import os

import loopchain.utils as util
from loopchain import configure as conf
from loopchain.baseservice import ObjectManager
from loopchain.peer import PeerService
from loopchain.radiostation import RadioStationService
from loopchain.scoreservice import ScoreService


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("service_type", type=str,
                        help="loopchain service to start [rs|peer|score|tool|admin]")
    parser.add_argument("-p", "--port",
                        help="port of Service itself")
    parser.add_argument("-o", "--configure_file_path",
                        help="json configure file path")

    # options for peer
    parser.add_argument("-r", "--radio_station_target",
                        help="[IP Address of Radio Station]:[PORT number of Radio Station], "
                             "[IP Address of Sub Radio Station]:[PORT number of Sub Radio Station] "
                             "or just [IP Address of Radio Station]")
    parser.add_argument("-d", "--develop", action="store_true",
                        help="set log level to SPAM (low develop mode)")
    parser.add_argument("-a", "--agent_pin", help="kms agent pin for kms load")

    # options for radiostation
    parser.add_argument("--cert",
                        help="certificate directory path")
    parser.add_argument("-s", "--seed",
                        help="create random table seed for KMS")

    # options for score service
    parser.add_argument("--channel",
                        help="channel name for score service")
    parser.add_argument("--score_package",
                        help="score package name")
    parser.add_argument("--peer_target",
                        help="peer gRPC target info [IP]:[PORT]")

    args = parser.parse_args(argv)

    if args.configure_file_path:
        conf.Configure().load_configure_json(args.configure_file_path)

    if args.develop:
        util.set_log_level_debug()

    if args.service_type == "peer":
        start_as_peer(args)
    elif args.service_type == "rs" or args.service_type == "radiostation":
        start_as_rs(args)
    elif args.service_type == "score":
        start_as_score(args)
    elif args.service_type == "tool":
        os.system("python3 ./demotool.py")
    elif args.service_type == "admin":
        os.system("python3 ./gtool.py")
    else:
        print(f"not supported service type {args.service_type}\ncheck loopchain help.\n")
        os.system("python3 ./loopchain.py -h")


def check_port_available(port):
    # Check Port is Using
    if util.check_port_using(util.get_private_ip(), int(port)):
        util.exit_and_msg(f"not available port({port})")


def start_as_score(args):
    # apply default configure values
    port = args.port or conf.PORT_SCORE_CONTAINER
    channel = args.channel or conf.LOOPCHAIN_DEFAULT_CHANNEL
    score_package = args.score_package or conf.DEFAULT_SCORE_PACKAGE
    peer_target = args.peer_target or f"{util.get_private_ip()}:{conf.PORT_PEER}"
    check_port_available(int(port))

    ScoreService(channel, score_package, peer_target).serve(port)


def start_as_rs(args):
    # apply default configure values
    port = args.port or conf.PORT_RADIOSTATION
    cert = args.cert or None
    pw = None
    seed = args.seed or None
    check_port_available(int(port))

    if seed:
        try:
            seed = int(seed)
        except ValueError as e:
            util.exit_and_msg(f"seed or s opt must be int \n"
                              f"input value : {seed}")

    RadioStationService(conf.IP_RADIOSTATION, cert, pw, seed).serve(port)


def start_as_peer(args):
    # apply default configure values
    port = args.port or conf.PORT_PEER
    radio_station_ip = conf.IP_RADIOSTATION
    radio_station_port = conf.PORT_RADIOSTATION
    radio_station_ip_sub = conf.IP_RADIOSTATION
    radio_station_port_sub = conf.PORT_RADIOSTATION
    check_port_available(int(port))

    if args.radio_station_target:
        try:
            if ':' in args.radio_station_target:
                target_list = util.parse_target_list(args.radio_station_target)
                if len(target_list) == 2:
                    radio_station_ip, radio_station_port = target_list[0]
                    radio_station_ip_sub, radio_station_port_sub = target_list[1]
                else:
                    radio_station_ip, radio_station_port = target_list[0]
                    # util.logger.spam(f"peer "
                    #                  f"radio_station_ip({radio_station_ip}) "
                    #                  f"radio_station_port({radio_station_port}) "
                    #                  f"radio_station_ip_sub({radio_station_ip_sub}) "
                    #                  f"radio_station_port_sub({radio_station_port_sub})")
            elif len(args.radio_station_target.split('.')) == 4:
                radio_station_ip = args.radio_station_target
            else:
                raise Exception("Invalid IP format")
        except Exception as e:
            util.exit_and_msg(f"'-r' or '--radio_station_target' option requires "
                              f"[IP Address of Radio Station]:[PORT number of Radio Station], "
                              f"or just [IP Address of Radio Station] format. error({e})")

    # run peer service with parameters
    logging.info(f"loopchain peer run with: port({port}) "
                 f"radio station({radio_station_ip}:{radio_station_port})")

    ObjectManager().peer_service = PeerService(radio_station_ip=radio_station_ip,
                                               radio_station_port=radio_station_port)

    ObjectManager().peer_service.serve(port=port, agent_pin=args.agent_pin, json_conf_path=args.configure_file_path)
