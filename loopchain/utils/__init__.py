# Copyright [theloop]
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
""" A module for utility"""

import datetime
import importlib.machinery
import json
import leveldb
import logging
import os.path as osp
import re
import signal
import socket
import time
import timeit
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from subprocess import PIPE, Popen, TimeoutExpired

import coloredlogs
import os
import verboselogs
from fluent import event
from fluent import sender

from loopchain import configure as conf
from loopchain.protos import loopchain_pb2, message_code
from loopchain.tools.grpc_helper import GRPCHelper

# for verbose logs
logger = verboselogs.VerboseLogger("dev")
apm_event = None
logger_reset = None


def set_colored_log_level():
    global logger
    coloredlogs.install(fmt=conf.LOG_FORMAT_DEBUG, datefmt="%m%d %H:%M:%S", level=verboselogs.SPAM)
    logging.basicConfig(format=conf.LOG_FORMAT_DEBUG, level=verboselogs.SPAM)
    logger = verboselogs.VerboseLogger("dev")


def set_log_level(peer_id=""):
    global logger_reset
    if peer_id != "":
        log_format = conf.LOG_FORMAT.replace("[PEER_ID]", peer_id)
        log_format_debug = conf.LOG_FORMAT_DEBUG.replace("[PEER_ID]", peer_id)

        conf.set_configuration("LOG_FORMAT", log_format)
        conf.set_configuration("LOG_FORMAT_DEBUG", log_format_debug)

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(handlers=[logging.FileHandler(conf.LOG_FILE_PATH, 'w', 'utf-8'), logging.StreamHandler()],
                        format=conf.LOG_FORMAT, level=conf.LOG_LEVEL)

    # This code is for adding peer_id to all log, and '-d' option loses influence about log by it.
    if logger_reset is not None and logger_reset.__name__ != "set_log_level":
        set_colored_log_level()

    # monitor setting
    if conf.MONITOR_LOG:
        sender.setup('loopchain', host=conf.MONITOR_LOG_HOST, port=conf.MONITOR_LOG_PORT)


# for logger color reset during test
logger_reset = set_log_level


def exit_and_msg(msg):
    exit_msg = "Service Stop by " + msg
    logging.error(exit_msg)
    os.killpg(0, signal.SIGKILL)


def load_user_score(path):
    """file path 로 부터 사용자 score object를 구한다.

    :param path: 사용자 score의 python 파일 (*.py)
    :return: 사용자 score 에 정의된 UserScore Object
    """
    user_module = importlib.machinery.SourceFileLoader('UserScore', path).load_module()
    return user_module.UserScore


coloredlogs.DEFAULT_FIELD_STYLES = {
    'hostname': {'color': 'magenta'},
    'programname': {'color': 'cyan'},
    'name': {'color': 'blue'},
    'levelname': {'color': 'black', 'bold': True},
    'asctime': {'color': 'magenta'}}


def set_log_color_set(is_leader=False):
    # level SPAM value is 5
    # level DEBUG value is 10
    if is_leader:
        coloredlogs.DEFAULT_LEVEL_STYLES = {
            'info': {},
            'notice': {'color': 'magenta'},
            'verbose': {'color': 'green'},
            'success': {'color': 'green', 'bold': True},
            'spam': {'color': 'cyan'},
            'critical': {'color': 'red', 'bold': True},
            'error': {'color': 'red'},
            'debug': {'color': 'blue'},
            'warning': {'color': 'yellow'}}
    else:
        coloredlogs.DEFAULT_LEVEL_STYLES = {
            'info': {},
            'notice': {'color': 'magenta'},
            'verbose': {'color': 'blue'},
            'success': {'color': 'green', 'bold': True},
            'spam': {'color': 'cyan'},
            'critical': {'color': 'red', 'bold': True},
            'error': {'color': 'red'},
            'debug': {'color': 'green'},
            'warning': {'color': 'yellow'}}


def set_log_level_debug():
    global logger_reset
    set_log_color_set()
    set_colored_log_level()
    logger_reset = set_colored_log_level

    # set for debug
    # conf.CONNECTION_RETRY_INTERVAL = conf.CONNECTION_RETRY_INTERVAL_TEST
    # conf.CONNECTION_RETRY_TIMEOUT_TO_RS = conf.CONNECTION_RETRY_TIMEOUT_TO_RS_TEST
    # conf.GRPC_TIMEOUT = conf.GRPC_TIMEOUT_TEST


def change_log_color_set(is_leader=False):
    set_log_color_set(is_leader)
    logger_reset()


def get_stub_to_server(target, stub_class, time_out_seconds=None, is_check_status=True,
                       ssl_auth_type: conf.SSLAuthType=conf.SSLAuthType.none):
    """gRPC connection to server

    :return: stub to server
    """
    if time_out_seconds is None:
        time_out_seconds = conf.CONNECTION_RETRY_TIMEOUT
    stub = None
    channel = None
    start_time = timeit.default_timer()
    duration = timeit.default_timer() - start_time

    while stub is None and duration < time_out_seconds:
        try:
            logging.debug("(util) get stub to server target: " + str(target))
            channel = GRPCHelper().create_client_channel(target, ssl_auth_type, conf.GRPC_SSL_KEY_LOAD_TYPE)
            stub = stub_class(channel)
            if is_check_status:
                stub.Request(loopchain_pb2.Message(code=message_code.Request.status), conf.GRPC_TIMEOUT)
        except Exception as e:
            logging.warning("Connect to Server Error(get_stub_to_server): " + str(e))
            logging.debug("duration(" + str(duration)
                          + ") interval(" + str(conf.CONNECTION_RETRY_INTERVAL)
                          + ") timeout(" + str(time_out_seconds) + ")")
            # RETRY_INTERVAL 만큼 대기후 TIMEOUT 전이면 다시 시도
            time.sleep(conf.CONNECTION_RETRY_INTERVAL)
            duration = timeit.default_timer() - start_time
            stub = None

    return stub, channel


def request_server_in_time(stub_method, message, time_out_seconds=None):
    """서버로 gRPC 메시지를 타임아웃 설정안에서 반복 요청한다.

    :param stub_method: gRPC stub.method
    :param message: gRPC proto message
    :param time_out_seconds: time out seconds
    :return: gRPC response
    """
    if time_out_seconds is None:
        time_out_seconds = conf.CONNECTION_RETRY_TIMEOUT
    start_time = timeit.default_timer()
    duration = timeit.default_timer() - start_time

    while duration < time_out_seconds:
        try:
            return stub_method(message, conf.GRPC_TIMEOUT)
        except Exception as e:
            logging.warning("retry request_server_in_time: " + str(e))
            logging.debug("duration(" + str(duration)
                          + ") interval(" + str(conf.CONNECTION_RETRY_INTERVAL)
                          + ") timeout(" + str(time_out_seconds) + ")")

        # RETRY_INTERVAL 만큼 대기후 TIMEOUT 전이면 다시 시도
        time.sleep(conf.CONNECTION_RETRY_INTERVAL)
        duration = timeit.default_timer() - start_time

    return None


def request_server_wait_response(stub_method, message, time_out_seconds=None):
    """서버로 gRPC 메시지를 타임아웃 설정안에서 응답이 올때까지 반복 요청한다.

    :param stub_method: gRPC stub.method
    :param message: gRPC proto message
    :param time_out_seconds: time out seconds
    :return: gRPC response
    """

    if time_out_seconds is None:
        time_out_seconds = conf.CONNECTION_RETRY_TIMEOUT
    start_time = timeit.default_timer()
    duration = timeit.default_timer() - start_time

    while duration < time_out_seconds:
        try:
            response = stub_method(message, conf.GRPC_TIMEOUT)

            if hasattr(response, "response_code") and response.response_code == message_code.Response.success:
                return response
            elif hasattr(response, "status") and response.status != "":
                return response
        except Exception as e:
            logging.warning("retry request_server_in_time: " + str(e))
            logging.debug("duration(" + str(duration)
                          + ") interval(" + str(conf.CONNECTION_RETRY_INTERVAL)
                          + ") timeout(" + str(time_out_seconds) + ")")

        # RETRY_INTERVAL 만큼 대기후 TIMEOUT 전이면 다시 시도
        time.sleep(conf.CONNECTION_RETRY_INTERVAL)
        duration = timeit.default_timer() - start_time

    return None


def get_private_ip3():
    command = "ifconfig | grep -i \"inet\" | grep -iv \"inet6\" | grep -iv \"127.\" | " + \
              "awk {'print $2'}"
    process = Popen(
        args=command,
        stdout=PIPE,
        shell=True
    )
    return str(process.communicate()[0].decode(conf.HASH_KEY_ENCODING)).strip().split("\n")[0]


def get_private_ip2():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        result = s.getsockname()[0]
        s.close()
    except Exception as e:
        result = "127.0.0.1"
    return result


def check_is_private_ip(ip):
    private_ip_prefix = ["10", "172", "192"]

    if ip.split(".")[0] not in private_ip_prefix:
        return False

    return True


def check_is_json_string(json_string):
    if isinstance(json_string, str):
        try:
            json_object = json.loads(json_string)
            return True
        except json.JSONDecodeError as e:
            logging.warning("Fail Json decode: " + str(e))
            return False
    return False


def get_private_ip():
    docker_evn = Path("/.dockerenv")
    # IF CONFIGURE IS SETTING
    if conf.LOOPCHAIN_HOST is not None:
        return conf.LOOPCHAIN_HOST

    if docker_evn.is_file():
        # TODO delete aws confgure
        logging.debug("It's working on docker. Trying to find private IP if it is in EC2.")
        command = "curl -s http://169.254.169.254/latest/meta-data/local-ipv4; echo"
        process = Popen(
            args=command,
            stdout=PIPE,
            shell=True
        )
        try:
            output = str(process.communicate(timeout=15)[0].decode(conf.HASH_KEY_ENCODING)).strip()
        except TimeoutExpired:
            logging.debug("Timed out! Docker container is working in local.")
            process.kill()
            return get_private_ip2()
        if check_is_private_ip(output):
            return output
        else:
            return get_private_ip2()
    else:
        ip = str(get_private_ip2())
        logging.debug("ip(with way2): " + ip)
        if check_is_private_ip(ip):
            return ip
        return get_private_ip3()


def dict_to_binary(the_dict):
    # TODO Dict to Binary 를 이렇게 할 수 밖에 없나?
    return str.encode(json.dumps(the_dict))


# Get Django Project get_valid_filename
# FROM https://github.com/django/django/blob/master/django/utils/encoding.py#L8
_PROTECTED_TYPES = (
    type(None), int, float, Decimal, datetime.datetime, datetime.date, datetime.time,
)


def get_time_stamp():
    return int(time.time()*1000000)  # milliseconds


def diff_in_seconds(timestamp):
    return int((get_time_stamp() - timestamp) / 100000)


def get_valid_filename(s):
    """Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; convert other spaces to
    underscores; and remove anything that is not an alphanumeric, dash,
    underscore, or dot.
    >>> get_valid_filename("john's portrait in 2004.jpg")
    'john_sportraitin2004.jpg'
    >>> get_valid_filename("loopchain/default")
    'loopchain_default'
    """
    s = force_text(s).strip().replace(' ', '')
    return re.sub(r'(?u)[^-\w.]', '_', s)


def is_protected_type(obj):
    """Determine if the object instance is of a protected type.
    Objects of protected types are preserved as-is when passed to
    force_text(strings_only=True).
    """
    return isinstance(obj, _PROTECTED_TYPES)


def force_text(s, encoding='utf-8', strings_only=False, errors='strict'):
    """Similar to smart_text, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.
    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first for performance reasons.
    if issubclass(type(s), str):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if isinstance(s, bytes):
            s = str(s, encoding, errors)
        else:
            s = str(s)
    except UnicodeDecodeError as e:
        raise UnicodeEncodeError(s, *e.args)
    return s


def check_port_using(host, port):
    """Check Port is Using

    :param host: check for host
    :param port: check port
    :return: Using is True
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex((host, port)) == 0:
            return True
        else:
            return False


def datetime_diff_in_mins(start):
    diff = datetime.datetime.now() - start
    return divmod(diff.days * 86400 + diff.seconds, 60)[0]


def pretty_json(json_text, indent=4):
    return json.dumps(json.loads(json_text), indent=indent, separators=(',', ': '))


def parse_target_list(targets: str) -> list:
    targets_split_by_comma = targets.split(",")
    target_list = []

    for target in targets_split_by_comma:
        target_split = target.strip().split(":")
        target_list.append((target_split[0], int(target_split[1])))

    return target_list


def init_level_db(level_db_identity, allow_rename_path=True):
    """init Level Db

    :param level_db_identity: identity for leveldb
    :return: level_db, level_db_path
    """
    level_db = None

    db_default_path = osp.join(conf.DEFAULT_STORAGE_PATH, 'db_' + level_db_identity)
    db_path = db_default_path
    logger.spam(f"utils:init_level_db ({level_db_identity})")

    retry_count = 0
    while level_db is None and retry_count < conf.MAX_RETRY_CREATE_DB:
        try:
            level_db = leveldb.LevelDB(db_path, create_if_missing=True)
        except leveldb.LevelDBError:
            if allow_rename_path:
                db_path = db_default_path + str(retry_count)
        retry_count += 1

    if level_db is None:
        logging.error("Fail! Create LevelDB")
        raise leveldb.LevelDBError("Fail To Create Level DB(path): " + db_path)

    return level_db, db_path


def no_send_apm_event(peer_id, event_param):
    pass


def send_apm_event(peer_id, event_param):
    event.Event(peer_id, event_param)


set_log_level()

if not conf.MONITOR_LOG:
    apm_event = no_send_apm_event
else:
    apm_event = send_apm_event
