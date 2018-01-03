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
"""All loopchain configure value can set by system environment.
But before set by system environment, loopchain use this default values.

configure 의 default 값으로 지정하여 사용한다.
이곳에서 직접 대입하거나 export 로 값을 지정할 수 있다.
configure 에서 사용되기 전에 다른 값을 이용하여 가공되어야 하는 경우 이 파일내에서 가공하면
configure 에서는 그대로 사용된다. (기존과 같은 방식을 유지할 수 있다.)

configure_user.py 파일을 생성하여 일부 default 값을 로컬에서 변경하여 사용할 수 있다.
configure_user.py 는 git 에서는 관리하지 않는다.
"""

import logging
import sys
from enum import IntEnum

import os

LOOPCHAIN_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PATH_PROTO_BUFFERS = "loopchain/protos"
PATH_PROTO_BUFFERS_TEST = "../../loopchain/protos"

if os.path.exists(PATH_PROTO_BUFFERS):
    sys.path.append(PATH_PROTO_BUFFERS)
else:
    sys.path.append(PATH_PROTO_BUFFERS_TEST)


#############
# LOGGING ###
#############
LOOPCHAIN_LOG_LEVEL = os.getenv('LOOPCHAIN_LOG_LEVEL', 'DEBUG')
LOG_LEVEL = logging.getLevelName(LOOPCHAIN_LOG_LEVEL)
LOG_FILE_PATH = "/var/tmp/loop_service.log"
LOG_FORMAT = "'%(asctime)s [PEER_ID] %(levelname)s %(message)s'"
LOG_FORMAT_DEBUG = "%(asctime)s %(process)d [PEER_ID] %(levelname)s %(message)s"

MONITOR_LOG = False
MONITOR_LOG_HOST = 'localhost'
MONITOR_LOG_PORT = 24224
MONITOR_LOG_MODULE = 'fluent'


###################
# MULTI PROCESS ###
###################
ENABLE_PROFILING = False


##########
# GRPC ###
##########
class SSLAuthType(IntEnum):
    none = 0
    server_only = 1
    mutual = 2


class KeyLoadType(IntEnum):
    FILE_LOAD = 0
    KMS_LOAD = 1
    RANDOM_TABLE_DERIVATION = 2


IP_LOCAL = '127.0.0.1'
IP_BLOCKGENERATOR = IP_LOCAL
IP_PEER = IP_LOCAL
IP_RADIOSTATION = IP_LOCAL
IP_RADIOSTATION_SUB = IP_LOCAL
INNER_SERVER_BIND_IP = '127.0.0.1'
DOCKER_HOST = os.getenv('DOCKER_HOST')
LOOPCHAIN_HOST = os.getenv('LOOPCHAIN_HOST', DOCKER_HOST)

PORT_PEER = 7100
PORT_INNER_SERVICE = 0
PORT_DIFF_INNER_SERVICE = 10000  # set inner_service_port to (peer_service_port + this value)
PORT_BLOCKGENERATOR = 7101
PORT_RADIOSTATION = 7102
PORT_RADIOSTATION_SUB = 7102
PORT_SCORE_CONTAINER = 7103
PORT_DIFF_SCORE_CONTAINER = 20021  # peer service 가 score container 를 시작할 때 자신과 다른 포트를 사용하도록 차이를 설정한다.
PORT_DIFF_BETWEEN_SCORE_CONTAINER = 30
PORT_DIFF_TX_CONTAINER = 10051
PORT_DIFF_BROADCAST_CONTAINER = 10081
MAX_WORKERS = 100
SLEEP_SECONDS_IN_SERVICE_LOOP = 0.1  # 0.05  # multi thread 동작을 위한 최소 대기 시간 설정
SLEEP_SECONDS_IN_SERVICE_NONE = 2  # _아무일도 하지 않는 대기 thread 의 대기 시간 설정
GRPC_TIMEOUT = 30  # seconds
GRPC_TIMEOUT_BROADCAST_RETRY = 6  # seconds
GRPC_TIMEOUT_TEST = 30  # seconds
GRPC_CONNECTION_TIMEOUT = GRPC_TIMEOUT * 2  # seconds, Connect Peer 메시지는 처리시간이 좀 더 필요함
STUB_REUSE_TIMEOUT = 60  # minutes

GRPC_SSL_TYPE = SSLAuthType.none
GRPC_SSL_KEY_LOAD_TYPE = KeyLoadType.FILE_LOAD
GRPC_SSL_DEFAULT_CERT_PATH = 'resources/ssl_grpc_test_cert/ssl.crt'
GRPC_SSL_DEFAULT_KEY_PATH = 'resources/ssl_grpc_test_cert/ssl.key'
GRPC_SSL_DEFAULT_TRUST_CERT_PATH = 'resources/ssl_grpc_test_cert/root_ca.crt'


##########
# TEST ###
##########
TEST_FAIL_VOTE_SIGN = "test_fail_vote_sign"


###################
# BLOCK MANAGER ###
###################
class ConsensusAlgorithm(IntEnum):
    none = 0
    default = 1
    siever = 2
    lft = 3


# 블록 생성 간격, tx 가 없을 경우 다음 간격까지 건너 뛴다.
INTERVAL_BLOCKGENERATION = 1
# Interval for Wait peer's vote
INTERVAL_WAIT_PEER_VOTE = 0.1  # 0.05
# blockchain 용 level db 생성 재시도 횟수, 테스트가 아닌 경우 1로 설정하여도 무방하다.
MAX_RETRY_CREATE_DB = 10
# default level db path
DEFAULT_LEVEL_DB_PATH = "./db"
# peer_id (UUID) 는 최초 1회 생성하여 level db에 저장한다.
LEVEL_DB_KEY_FOR_PEER_ID = str.encode("peer_id_key")
# String Peer Data Encoding
PEER_DATA_ENCODING = 'UTF-8'
# Hash Key Encoding
HASH_KEY_ENCODING = 'UTF-8'
# Consensus Algorithm
CONSENSUS_ALGORITHM = ConsensusAlgorithm.siever
# 블럭의 최대 크기 (kbytes), gRPC 최대 메시지는 4MB (4096) 이므로 그보다 작게 설정할 것
MAX_BLOCK_KBYTES = 3000  # default: 3000
# 블럭의 담기는 트랜잭션의 최대 갯수, 메시지 크기를 계속 dump 로 비교하는 것은 성능에 부담이 되므로 tx 추가시에는 갯수로만 방지한다.
# tx -> block 상황을 체크하는 것이므로 (블럭 나누기의 기준은 아니므로) 실제 블럭에는 설정값 이상의 tx 가 블럭에 담길 수 있다.
# 실제 블럭에 담기는 tx 를 이 값으로 제어하려면 코드가 추가 되어야 한다. (이 경우 성능 저하 요인이 될 수 있다.)
MAX_BLOCK_TX_NUM = 1000  # default: 1000
MAX_CREATE_TX_QUEUE = MAX_BLOCK_TX_NUM / 10  # 한 peer 의 queue 에 최대로 보관 가능한 tx 갯수, 로드 상태에서 부하를 조절한다.
# 블럭이 합의 되는 투표율 1 = 100%, 0.5 = 50%
VOTING_RATIO = 0.65
# Block Height 를 level_db 의 key(bytes)로 변환할때 bytes size
BLOCK_HEIGHT_BYTES_LEN = 12
# Leader 의 block 생성 갯수
LEADER_BLOCK_CREATION_LIMIT = 20000000
# Block vote timeout
BLOCK_VOTE_TIMEOUT = 60 * 10  # seconds
# default storage path
DEFAULT_STORAGE_PATH = os.getenv('DEFAULT_STORAGE_PATH', os.path.join(LOOPCHAIN_ROOT_PATH, '.storage'))


###########
# SCORE ###
###########
DEFAULT_SCORE_HOST = os.getenv('DEFAULT_SCORE_HOST', 'repo.theloop.co.kr')
DEFAULT_SCORE_BASE = os.getenv('DEFAULT_SCORE_BASE', 'git@'+DEFAULT_SCORE_HOST)
DEFAULT_SCORE_REPOSITORY_PATH = os.path.join(LOOPCHAIN_ROOT_PATH, 'score')
DEFAULT_SCORE_STORAGE_PATH = os.getenv('DEFAULT_SCORE_STORAGE_PATH', os.path.join(DEFAULT_STORAGE_PATH, 'score'))
DEFAULT_SCORE_PACKAGE = 'loopchain/default'
DEFAULT_SCORE_BRANCH_MASTER = 'master'
DEFAULT_SCORE_BRANCH = os.getenv('DEFAULT_SCORE_BRANCH', DEFAULT_SCORE_BRANCH_MASTER)
# DEFAULT USER / PASSWORD
DEFAULT_SCORE_BASE_USER = 'score'
DEFAULT_SCORE_BASE_PASSWORD = 'score'
# FOR SCORE DEVELOP
ALLOW_LOAD_SCORE_IN_DEVELOP = os.getenv('ALLOW_LOAD_SCORE_IN_DEVELOP', 'allow') == 'allow'
DEVELOP_SCORE_PACKAGE_ROOT = 'develop'
DEFAULT_SCORE_REPOSITORY_KEY = os.path.join(LOOPCHAIN_ROOT_PATH, 'resources/loopchain_deploy')
# repository key
DEFAULT_SCORE_REPOSITORY_KEY = os.getenv('DEFAULT_SCORE_REPOSITORY_KEY', DEFAULT_SCORE_REPOSITORY_KEY)
SCORE_LOAD_TIMEOUT = GRPC_TIMEOUT * 180  # seconds, Git repository 접속해서 파일 다운로드 등 시간이 필요함
# REMOTE PULL PACKAGE FLAG
REMOTE_PULL_SCORE = False
INTERVAL_LOAD_SCORE = 1  # seconds
SCORE_RETRY_TIMES = 3
SCORE_QUERY_TIMEOUT = 120
SCORE_INVOKE_TIMEOUT = 60 * 5  # seconds
SCORE_LOAD_RETRY_TIMES = 3  # times
SCORE_LOAD_RETRY_INTERVAL = 25.0  # seconds


##################
# REST SERVICE ###
##################
PORT_DIFF_REST_SERVICE_CONTAINER = 1900  # peer service 가 REST container 를 시작할 때 자신과 다른 포트를 사용하도록 차이를 설정한다.
ENABLE_REST_SERVICE = True
ENABLE_REST_SSL = 0    # Rest server에 SSL 적용 여부를 설정한다. 0: None, 1: Server Auth, 2: Mutual Auth
DEFAULT_SSL_CERT_PATH = 'resources/ssl_test_cert/cert.pem'
DEFAULT_SSL_KEY_PATH = 'resources/ssl_test_cert/key.pem'
DEFAULT_SSL_TRUST_CERT_PATH = 'resources/ssl_test_ca/cert.pem'
REST_ADDITIONAL_TIMEOUT = 30  # seconds
REST_PROXY_DEFAULT_PORT = 5000
USE_GUNICORN_HA_SERVER = False   # Use high aviability gunicorn web server.


# check default stroage path exist
if not os.path.exists(DEFAULT_STORAGE_PATH):
    os.makedirs(DEFAULT_STORAGE_PATH)


##########
# Peer ###
##########
CONNECTION_RETRY_INTERVAL = 2  # seconds
CONNECTION_RETRY_INTERVAL_TEST = 2  # seconds for testcase
CONNECTION_RETRY_TIMEOUT_WHEN_INITIAL = 5  # seconds
CONNECTION_RETRY_TIMEOUT = 60  # seconds
CONNECTION_RETRY_TIMEOUT_TO_RS = 60 * 5  # seconds
CONNECTION_RETRY_TIMEOUT_TO_RS_TEST = 30  # seconds for testcase
CONNECTION_RETRY_TIMES = 3  # times
CONNECTION_RETRY_TIMES_TO_RS = 5  # times
CONNECTION_TIMEOUT_TO_RS = 60 * 2  # seconds
BROADCAST_RETRY_TIMES = 5  # times
REQUEST_BLOCK_GENERATOR_TIMEOUT = 10  # seconds
BLOCK_GENERATOR_BROADCAST_TIMEOUT = 5  # seconds
WAIT_GRPC_SERVICE_START = 5  # seconds
WAIT_SECONDS_FOR_SUB_PROCESS_START = 5  # seconds
SLEEP_SECONDS_FOR_SUB_PROCESS_START = 1  # seconds
WAIT_SUB_PROCESS_RETRY_TIMES = 5
PEER_GROUP_ID = ""  # "8d4e8d08-0d2c-11e7-a589-acbc32b0aaa1"  # vote group id
ENABLE_PROCESS_MONITORING = True
INTERVAL_SECONDS_PROCESS_MONITORING = 30  # seconds
TX_PROCESS_NAME = "Tx Process"
BROADCAST_PROCESS_NAME = "Broadcast Process"
PEER_NAME = "no_name"
IS_BROADCAST_ASYNC = True


##################
# RadioStation ###
##################
ALL_GROUP_ID = "all_group_id"  # "98fad20a-0df1-11e7-bc4b-acbc32b0aaa1"
TEST_GROUP_ID = "test_group_id"  # "ea8f365c-7fb8-11e6-af03-38c98627c586"
LEVEL_DB_KEY_FOR_PEER_LIST = "peer_manager_key"
# RS heartbeat 으로 리더선정 및 무응답피어 제거를 할지 여부를 정한다. False 일때 네트워크는 더 안정적이 된다.
# LFT 에 의한 장애 처리 전까지 임시적으로만 True 로 사용한다. by winDy
ENABLE_RADIOSTATION_HEARTBEAT = True
SLEEP_SECONDS_IN_RADIOSTATION_HEARTBEAT = 30   # 60 * 60  # seconds, RS 의 peer status heartbeat 주기
NO_RESPONSE_COUNT_ALLOW_BY_HEARTBEAT = 5  # 몇번의 RS Heartbeat 무응답까지 감수할 것인지
# Peer 의 중복 재접속을 허용한다.
ALLOW_PEER_RECONNECT = True
# 토큰 유효시간(분)
TOKEN_INTERVAL = 10
# If disconnected state of the peer is maintained, That peer will removed from peer list after this minutes.
TIMEOUT_PEER_REMOVE_IN_LIST = 5  # minutes, replace by NO_RESPONSE_COUNT_ALLOW_BY_HEARTBEAT
IS_LOAD_PEER_MANAGER_FROM_DB = False
LOOPCHAIN_DEFAULT_CHANNEL = "loopchain_default"  # Default Channel Name
LOOPCHAIN_TEST_CHANNEL = "loopchain_test"
CHANNEL_MANAGE_DATA_PATH = os.path.join(LOOPCHAIN_ROOT_PATH, 'channel_manage_data.json')  # Channel Manage Data Path
ENABLE_CHANNEL_AUTH = False  # if this option is true, peer only gets channel infos to which it belongs.


####################
# Authentication ###
####################
TOKEN_TYPE_TOKEN = "00"
TOKEN_TYPE_CERT = "01"
TOKEN_TYPE_SIGN = "02"


###############
# Signature ###
###############
CHANNEL_OPTION = {
    "loopchain_default": {
        "load_cert": False,
        "consensus_cert_use": False,
        "tx_cert_use": False,
        "key_load_type": KeyLoadType.FILE_LOAD,
        "public_path": os.path.join(LOOPCHAIN_ROOT_PATH, 'resources/default_pki/public.der'),
        "private_path": os.path.join(LOOPCHAIN_ROOT_PATH, 'resources/default_pki/private.der'),
        "private_password": b'test'
    },
    "loopchain_test": {
        "load_cert": False,
        "consensus_cert_use": False,
        "tx_cert_use": False,
        "key_load_type": KeyLoadType.FILE_LOAD,
        "public_path": os.path.join(LOOPCHAIN_ROOT_PATH, 'resources/default_pki/public.der'),
        "private_path": os.path.join(LOOPCHAIN_ROOT_PATH, 'resources/default_pki/private.der'),
        "private_password": b'test'
    }
}

# KMS
KMS_AGENT_PASSWORD = ""
KMS_SIGNATURE_KEY_ID = ""
KMS_SIGNATURE_KEY_ID_LIST = {}
KMS_TLS_KEY_ID = ""



####################
# TimerService ###
####################
TIMEOUT_FOR_PEER_VOTE = 20
TIMEOUT_FOR_PEER_BLOCK_GENERATION = TIMEOUT_FOR_PEER_VOTE + 10
