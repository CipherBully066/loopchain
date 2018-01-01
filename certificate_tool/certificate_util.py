#!/usr/bin/env python3
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

import getpass
import logging
import os
import sys

from ca_service import CAService


def set_log_level(level):
    logging.basicConfig(level=level)


_DEFAULT_PATH = "testcerts/"
_DEFAULT_SELF_SIGNED_CERTS_PATH = "test_self_signed_path/"


# Main menu
def main_menu(show=True):
    if show:
        print("\nTheLoop LoopChain Certificate Authority Command Tools\n")
        print("Choose menu number you want")
        print("Default CA Cert Directory : \"" + _DEFAULT_PATH + "\"")
        print("Default Self Signed Cert Directory : \"" + _DEFAULT_SELF_SIGNED_CERTS_PATH + "\"")
        print("---------------------")
        print("1. Generate CA Certificate")
        print("2. Show CA Certificate")
        print("---------------------")
        print("3. Generate CA Signed Peer Certificate")
        print("4. List Peer Certificate(s)")
        print("---------------------")
        print("5. Generate Self Signed Peer Certificate")
        print("6. List Self Signed Peer Certificate(s)")
        print("---------------------")
        print("7. Change CA Based Cert Path")
        print("8. Change Self Signed Cert Path")
        print("0. Quit")

    choice = input(" >>  ")
    exec_menu(choice)

    return


# Excute menu
def exec_menu(choice):
    ch = choice.lower()
    if ch == '':
        main_menu(True)
    else:
        try:
            menu_actions[ch]()
        except KeyError:
            print("Invalid selection, please try again.\n")
            main_menu(True)


def menu1():
    def ca_cert_creation(params, period):
        ca = CAService(_DEFAULT_PATH, None)
        ca.generate_ca_cert(cn=params[1], ou=params[2], o=params[3], expire_period=period, password=None)
        print("\n----- CA 인증서 생성 완료 -----")

    print("\n##### CA 정보 #####")
    receive_signed_certificate_params(ca_cert_creation)


def menu1_1():
    print("\n----- 주체(subject) 정보 -----")
    print("Common Name(eg, your name) [Default CN] : ")
    cn = input(" >> ")
    if cn == "":
        cn = "CN"

    print("Organization Unit Name(eg, section) [Default DEV] : ")
    ou = input(" >> ")
    if ou == "":
        ou = "DEV"

    print("Organization Name(eg, company) [Default TheLoop] : ")
    o = input(" >> ")
    if o == "":
        o = "TheLoop"

    print("[cn=" + cn + ", ou=" + ou + ", o=" + o + ", c=kr] OK? (Y/N) : ")
    ok = input(" >> ")
    return [ok, cn, ou, o]


def menu1_2():
    print("\n----- 인증서 유효기간 -----")
    print("Expire Period(eg, 1years) [Default 5] : ")
    period = input(" >> ")
    if period == "":
        period = 5
    return period


def menu2():
    print("\n##### CA 인증서 #####")
    ca = CAService(_DEFAULT_PATH, None)
    ca.show_ca_certificate()
    main_menu(True)


def menu3():
    print("\n##### CA 인증서/개인키 로딩 #####")
    ca = CAService(_DEFAULT_PATH, None)
    if ca.is_secure is False:
        print("CA 인증서 로딩 실패")
        return

    print("\n##### Peer 인증서/개인키 #####")
    input = menu3_2()
    if input[0] == "Y" or input[0] == "y":
        ca = CAService(_DEFAULT_PATH, None)
        ca.generate_peer_cert(cn=input[1], password=None)

        print("\n----- Peer 인증서/개인키 생성 완료 -----")
        main_menu(True)
    else:
        print("\n##### User Cancel #####")
        main_menu(True)


def menu3_1():
    print("\n----- CA 개인키 비밀번호 -----")
    return getpass.getpass()


def menu3_2():
    print("\n----- 주체(subject) 정보 -----")
    print("Common Name(eg, your name) [Default TestPeer1] : ")
    cn = input(" >> ")
    if cn == "":
        cn = "TestPeer1"

    print("[cn=" + cn + "] OK? (Y/N) : ")
    ok = input(" >> ")
    return [ok, cn]


def menu4():
    print("\n##### Peer 인증서 목록 #####")
    show_certs(_DEFAULT_PATH, True)


def menu5():
    print("\n##### Self Signed 인증서 생성 #####")

    def create_self_sign_cert_for_peer(params, period):
        ca = CAService(_DEFAULT_SELF_SIGNED_CERTS_PATH, None)
        ca.generate_self_signed_certificate(cn=params[1], ou=params[2], o=params[3], expire_period=period,
                                            cert_path=os.path.join(_DEFAULT_SELF_SIGNED_CERTS_PATH, params[1]))

    receive_signed_certificate_params(create_self_sign_cert_for_peer)


def menu6():
    print("\n##### self signed 인증서 목록 #####")
    show_certs(_DEFAULT_SELF_SIGNED_CERTS_PATH, False)


def show_certs(path, is_ca):
    ca = CAService(is_ca=is_ca)
    if ca.is_secure is False:
        ca = CAService(path, None, is_ca=is_ca)
    ca.show_peer_list()
    main_menu(True)


def receive_signed_certificate_params(func_create_cert):
    params = menu1_1()
    if params[0] == "Y" or params[0] == "y":
        print("[cn=" + params[1] + ", ou=" + params[2] + ", o=" + params[3] + ", c=kr]")
        period = int(menu1_2())
        func_create_cert(params, period)
        main_menu(True)
    else:
        print("\n##### User Cancel #####")
        main_menu(True)


def menu7():
    print("인증서 생성 위치 변경")
    global _DEFAULT_PATH
    _DEFAULT_PATH = change_path()
    main_menu(True)


def change_path():
    path = input(" >> ")
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def menu8():
    print("셀프사인 인증서 생성 위치 변경")
    global _DEFAULT_SELF_SIGNED_CERTS_PATH
    _DEFAULT_SELF_SIGNED_CERTS_PATH = change_path()
    main_menu(True)


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
    '0': tool_exit
}


# Main Program
if __name__ == "__main__":

    set_log_level(logging.DEBUG)
    if len(sys.argv) > 1:
        # Run Menu
        print("Have a nice one~ with your number is " + sys.argv[1])
        menu_actions[sys.argv[1]]()
    else:
        # Launch main menu
        main_menu(True)
