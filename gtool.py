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

import logging
import os
import sys
import getopt
import json

import coloredlogs

import loopchain.utils as util
from loopchain import configure as conf
from loopchain.radiostation import AdminManager

sys.path.append("loopchain/protos")
from loopchain.protos import loopchain_pb2, loopchain_pb2_grpc, message_code
from loopchain.tools.grpc_helper import GRPCHelper


# Main definition - constants
menu_actions = {}
tool_globals = {}


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "ho:",
                                   ["help",
                                    "configure_file_path="])
    except getopt.GetoptError as e:
        logging.error(e)
        usage()
        sys.exit(1)

    # apply json configure values
    for opt, arg in opts:
        if (opt == "-o") or (opt == "--configure_file_path"):
            conf.Configure().load_configure_json(arg)
            main_menu(True)
        elif (opt == "-h") or (opt == "--help"):
            usage()
            return


def usage():
    print("USAGE: LoopChain Admin Command Tools")
    print("python3.6 gtool.py [option] [value] ...")
    print("-------------------------------")
    print("option list")
    print("-------------------------------")
    print("-o or --configure_file_path : json configure file path")
    print("-h or --help : print this usage")


def set_log_level(level):
    coloredlogs.install(level=level)
    logging.basicConfig(level=level)


admin_manager = None  # AdminManager("station")


# Main menu
def main_menu(show=True):
    global admin_manager
    if not admin_manager:
        admin_manager = AdminManager("station")

    if show:
        print("TheLoop LoopChain Admin Command Tools\n")
        print("Choose menu number you want")
        print("---------------------")
        print("1. Connect to Radiostation admin service")
        print("2. Get Radiostation admin status")
        print("3. Get all channel manage info")
        print("4. Add peer")
        print("5. Add channel")
        print("6. Delete peer")
        print("7. Delete channel")
        print("8. Dump current data to json")
        print("9. Send channel manage info to Radiostation")
        print("10. Restart channel")
        print("0. Quit")

    choice = input(" >>  ")
    exec_menu(choice)

    return


# Execute menu
def exec_menu(choice):
    ch = choice.lower()
    if ch == '':
        menu_actions['main_menu'](True)
    else:
        try:
            menu_actions[ch]()
        except KeyError:
            print("Invalid input, please try again.\n")
            menu_actions['main_menu'](True)
    return


def menu1():
    print("\nConnect to Radiostation Admin Service\n")
    print("\nEnter the peer target in the following format:")
    print(f"[IP of Radiostation]:[port]"
          f"(default '' -> 127.0.0.1:{conf.PORT_RADIOSTATION + conf.PORT_DIFF_INNER_SERVICE}, "
          f"[port] -> 127.0.0.1:[port])")
    choice = input(" >>  ")
    if choice == "":
        choice = f"127.0.0.1:{conf.PORT_RADIOSTATION + conf.PORT_DIFF_INNER_SERVICE}"
    elif choice.find(':') == -1:
        choice = "127.0.0.1:" + choice

    channel = GRPCHelper().create_client_channel(choice)
    rs_stub = loopchain_pb2_grpc.AdminServiceStub(channel)
    tool_globals["rs_stub"] = rs_stub

    response = rs_stub.Request(loopchain_pb2.Message(
        code=message_code.Request.status,
        message="connect from gtool"
    ), conf.GRPC_TIMEOUT)
    print("RS Status: " + str(response))
    main_menu()


def menu2():
    # TODO get rs admin status
    print("\nGet Radiostation Admin status")
    print("0. Back")
    choice = input(" >>  ")
    exec_menu("2-" + choice)
    return


def menu3():
    print("\nGet all channel manage data")
    print(util.pretty_json(admin_manager.get_all_channel_info()))
    print("0. Back")
    choice = input(" >>  ")

    if choice == '0':
        menu_actions['main_menu']()
    return


def menu4():
    print("\nAdd peer")
    print("Enter the peer target in the following format:")
    print("[IP of Peer]:[PORT]")
    new_peer_target = input(" >>  ")
    loaded_data = admin_manager.json_data
    channel_list = list(loaded_data)
    i = 0
    while i < len(channel_list):
        peer_target_list = loaded_data[channel_list[i]]["peers"]
        print(f"Do you want to add a new peer to channel: {channel_list[i]}? Y/n (Enter: Y)")
        choice = input(" >>  ")
        if choice == '' or choice == 'Y':
            admin_manager.add_peer_target(loaded_data, channel_list, new_peer_target, peer_target_list, i)
        else:
            pass
        i += 1
    admin_manager.save_channel_manage_data(loaded_data)

    print("1. Add an additional peer")
    print("0. Back")
    choice = input(" >>  ")

    if choice == '1':
        menu4()
    elif choice == '0':
        menu_actions['main_menu']()
    return


def menu5():
    print("\nAdd channel")
    print("Enter the new channel name:")
    new_channel = input(" >>  ")
    loaded_data = admin_manager.json_data
    channel_list = list(loaded_data)
    if new_channel not in channel_list:
        print(f"Please enter the name of score_package:")
        score_package_input = input(" >>  ")
        admin_manager.add_channel(loaded_data, new_channel, score_package_input)
    else:
        logging.warning(f"channel: {new_channel} already exists.")

    print("0. Back")
    choice = input(" >>  ")

    if choice == '0':
        menu_actions['main_menu']()
    return


def menu6():
    print("\nDelete peer")
    print("Enter the peer target in the following format:")
    print("[IP of Peer]:[PORT]")
    remove_peer_target = input(" >>  ")
    loaded_data = admin_manager.json_data
    filtered_channel_infos = admin_manager.get_channel_infos_by_peer_target(remove_peer_target)
    filtered_list = list(json.loads(filtered_channel_infos))
    print(f"\nHere is the channel list that peer({remove_peer_target}) is included:")
    print(f"{filtered_list}")
    i = 0
    while i < len(filtered_list):
        print(f"\nDo you want to delete peer({remove_peer_target}) in channel: {filtered_list[i]}? Y/n (Enter: Y)")
        choice = input(" >>  ")
        if choice == '' or choice == 'Y':
            admin_manager.delete_peer_target(loaded_data, remove_peer_target, filtered_list, i)
        else:
            pass
        i += 1
    admin_manager.save_channel_manage_data(loaded_data)

    print("0. Back")
    choice = input(" >>  ")

    if choice == '0':
        menu_actions['main_menu']()
    return


def menu7():
    print("\nDelete channel")
    channel_list = admin_manager.get_channel_list()
    print(f"\nHere is the all channel list:")
    print(f"{channel_list}")
    print(f"\nIf you delete a channel, all peers in that channel will be removed.")
    print(f"Are you sure to proceed?  Y/n (Enter: Y)")
    choice = input(" >>  ")
    if choice == '' or choice == 'Y':
        loaded_data = admin_manager.json_data
        channel_list = list(loaded_data)
        print(f"\nHere is the all channel list:")
        print(f"{channel_list}")

        i = 0
        while i < len(channel_list):
            print(f"\nDo you want to delete the channel({channel_list[i]}) and all of its peers? Y/n")
            choice = input(" >>  ")
            if choice == '' or choice == 'Y':
                admin_manager.delete_channel(loaded_data, channel_list, i)
            else:
                pass
            i += 1
        admin_manager.save_channel_manage_data(loaded_data)

        print("0. Back")
        choice = input(" >>  ")
        if choice == '0':
            menu_actions['main_menu']()
    else:
        menu_actions['main_menu']()
    return


def menu8():
    print("\nDump current data to json")
    current_data = admin_manager.json_data
    channel_manage_data_path = conf.CHANNEL_MANAGE_DATA_PATH
    admin_manager.save_channel_manage_data(current_data)
    print(f"current channel manage data is now up to date in {channel_manage_data_path}")

    print("0. Back")
    choice = input(" >>  ")

    if choice == '0':
        menu_actions['main_menu']()
    return


def menu9():
    print("\nSend channel manage info to Radiostation")
    if not tool_globals:
        logging.warning(f"you should connect to Radiostation admin service first. Please go back and enter number 1.")
        print("0. Back")
        choice = input(" >>  ")
        if choice == '0':
            menu_actions['main_menu']()
    else:
        channel_infos = admin_manager.get_all_channel_info()
        response = tool_globals["rs_stub"].Request(loopchain_pb2.Message(
            code=message_code.Request.rs_send_channel_manage_info_to_rs,
            meta=channel_infos,
            message="gtool"
        ), conf.GRPC_TIMEOUT)
        print(f"response: {response}")

    print("0. Back")
    choice = input(" >>  ")

    if choice == '0':
        menu_actions['main_menu']()
    return


def menu10():
    print("\nRestart peer by channel")
    if not tool_globals:
        print(f"NOTICE! you should connect to Radiostation admin service first. Please go back and enter number 1.")
        print("0. Back")
        choice = input(" >>  ")
        if choice == '0':
            menu_actions['main_menu']()
    else:
        channel_infos = admin_manager.get_all_channel_info()
        print(f"Choose channel number for restart")
        channel_data = json.loads(channel_infos)

        channel_select = {}
        channel_index = 0
        for channel in channel_data.keys():
            print(f"{channel_index}: {channel}")
            channel_select[str(channel_index)] = channel
            channel_index += 1

        select_channel = input(" >>  ")
        if select_channel not in channel_select.keys():
            print(f"Please enter correct channel number.")
        else:
            response = tool_globals["rs_stub"].Request(loopchain_pb2.Message(
                code=message_code.Request.rs_restart_channel,
                channel=channel_select[select_channel],
                message="restart channel"
            ), conf.GRPC_TIMEOUT)
            print(f"response: {response}")

    print("0. Back")
    choice = input(" >>  ")

    if choice == '0':
        menu_actions['main_menu']()
    return


# Exit program
def tool_exit():
    sys.exit()


# Menu definition
menu_actions = {
    'main_menu': main_menu,
    '1': menu1,
    '2': menu2,
    '3': menu3,
    '4': menu4,
    '5': menu5,
    '6': menu6,
    '7': menu7,
    '8': menu8,
    '9': menu9,
    '10': menu10,
    '0': tool_exit
}


# Main Program
if __name__ == "__main__":
    os.system("source bin/activate")
    set_log_level(logging.DEBUG)
    if len(sys.argv) > 1:
        if '-' in sys.argv[1]:
            main(sys.argv[1:])
        # Run Menu
        else:
            print("Have a nice one~ with your number is " + sys.argv[1])
            menu_actions[sys.argv[1]]()
    else:
        # Launch main menu
        main_menu(True)
