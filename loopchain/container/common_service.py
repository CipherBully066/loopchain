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
"""Class for managing Peer and Radio station """

import logging
import queue
import time
from concurrent import futures

import grpc

import loopchain.utils as util
from loopchain import configure as conf
from loopchain.baseservice import BroadcastProcess, CommonThread, ObjectManager
from loopchain.protos import loopchain_pb2, message_code
from loopchain.tools.grpc_helper import GRPCHelper

# loopchain_pb2 를 아래와 같이 import 하지 않으면 broadcast 시도시 pickle 오류가 발생함
import loopchain_pb2


class CommonService(CommonThread):
    """Manage common part of 'Peer' and 'Radio station' especially broadcast service"""

    def __init__(self, gRPC_module, inner_service_port=None):
        super().__init__()
        self.__peer_id = None if ObjectManager().peer_service is None else ObjectManager().peer_service.peer_id

        # for peer_service, it refers to peer_inner_service / for rs_service, it refers to rs_admin_service
        self.inner_server = grpc.server(futures.ThreadPoolExecutor(max_workers=conf.MAX_WORKERS))
        self.outer_server = grpc.server(futures.ThreadPoolExecutor(max_workers=conf.MAX_WORKERS))

        # members for private, It helps simplicity of code intelligence
        self.__gRPC_module = gRPC_module
        self.__port = 0
        self.__inner_service_port = inner_service_port
        self.__peer_target = None
        if inner_service_port is not None:  # It means this is Peer's CommonService not RS.
            peer_port = inner_service_port - conf.PORT_DIFF_INNER_SERVICE
            self.__peer_target = util.get_private_ip() + ":" + str(peer_port)
        self.__subscriptions = queue.Queue()  # tuple with (channel, stub)
        self.__group_id = ""

        self.__loop_functions = []

    def getstatus(self, block_manager):
        """블럭체인의 상태 조회

        :param block_manager:
        :return:
        """
        logging.debug("CommonService.getstatus")

        block_height = 0
        total_tx = 0

        status_data = dict()

        if block_manager is not None:
            status_data["made_block_count"] = block_manager.get_blockchain().made_block_count
            if block_manager.get_blockchain().last_block is not None:
                block_height = block_manager.get_blockchain().last_block.height
                logging.debug("getstatus block hash(block_manager.get_blockchain().last_block.block_hash): "
                              + str(block_manager.get_blockchain().last_block.block_hash))
                logging.debug("getstatus block hash(block_manager.get_blockchain().block_height): "
                              + str(block_manager.get_blockchain().block_height))
                logging.debug("getstatus block height: " + str(block_height))
                # Score와 상관없이 TransactionTx는 블럭매니저가 관리 합니다.
                total_tx = block_manager.get_total_tx()

            status_data["status"] = "Service is online: " + str(block_manager.peer_type)
            status_data["peer_type"] = str(block_manager.peer_type)
        else:
            status_data["status"] = "Service is online: 2"
            status_data["peer_type"] = "2"

        # TODO 더이상 사용하지 않는다. REST API 업데이트 후 제거할 것
        status_data["audience_count"] = "0"

        status_data["consensus"] = str(conf.CONSENSUS_ALGORITHM.name)
        status_data["peer_id"] = str(self.__peer_id)
        status_data["block_height"] = block_height
        status_data["total_tx"] = total_tx
        status_data["peer_target"] = self.__peer_target
        if ObjectManager().peer_service is not None:
            # TODO tx service 는 더이상 사용되지 않는다. 아래 코드는 의도에 맞게 다시 작성되어야 한다.
            # status_data["leader_complaint"] = ObjectManager().peer_service.tx_service.peer_status.value
            status_data["leader_complaint"] = 1

        return status_data

    def __subscribe(self, channel, port, subscribe_stub, is_unsubscribe=False):
        # self.__peer_target = util.get_private_ip() + ":" + str(port)
        # logging.debug("peer_info: " + self.__peer_target)
        # logging.debug("subscribe_stub type: " + str(subscribe_stub.stub.__module__))

        # Subscribe 는 peer 의 type 정보를 사용하지 않지만, PeerRequest 의 required 값이라 임의의 type 정보를 할당한다.
        subscribe_peer_type = loopchain_pb2.PEER

        try:
            if is_unsubscribe:
                subscribe_stub.call(
                    "UnSubscribe",
                    self.__gRPC_module.PeerRequest(
                        channel=channel,
                        peer_target=self.__peer_target, peer_type=subscribe_peer_type,
                        peer_id=self.__peer_id, group_id=self.__group_id
                    ),
                    is_stub_reuse=True
                )
            else:
                subscribe_stub.call(
                    "Subscribe",
                    self.__gRPC_module.PeerRequest(
                        channel=channel,
                        peer_target=self.__peer_target, peer_type=subscribe_peer_type,
                        peer_id=self.__peer_id, group_id=self.__group_id
                    ),
                    is_stub_reuse=True
                )

            logging.info(("Subscribe", "UnSubscribe")[is_unsubscribe])
        except Exception as e:
            logging.info("gRPC Exception: " + type(e).__name__)
            logging.error("Fail " + ("Subscribe", "UnSubscribe")[is_unsubscribe])

    def __un_subscribe(self, channel, port, subscribe_stub):
        self.__subscribe(channel, port, subscribe_stub, True)

    def start(self, port, peer_id="", group_id=""):
        self.__port = port
        if self.__inner_service_port is None:
            self.__inner_service_port = port + conf.PORT_DIFF_INNER_SERVICE
        self.__peer_id = peer_id
        self.__group_id = group_id
        CommonThread.start(self)

    def subscribe(self, channel, subscribe_stub, peer_type=None):
        if subscribe_stub is None:
            util.logger.spam(f"common_service:subscribe subscribe_stub is None!")
            return

        self.__subscribe(channel=channel, port=self.__port, subscribe_stub=subscribe_stub)
        self.__subscriptions.put((channel, subscribe_stub))

        if peer_type == loopchain_pb2.BLOCK_GENERATOR or peer_type == loopchain_pb2.PEER:
            # tx broadcast 를 위해서 leader 인 경우 자신의 audience 에 같이 추가를 한다.
            ObjectManager().peer_service.channel_manager.subscribe(
                channel=channel, subscribe_target=subscribe_stub.target)

    def add_loop(self, loop_function):
        self.__loop_functions.append(loop_function)

    def __run_loop_functions(self):
        for loop_function in self.__loop_functions:
            loop_function()

    def run(self):
        target_host = '[::]:' + str(self.__port)
        GRPCHelper().add_server_port(self.outer_server, target_host)

        # Bind Only loopback address (ip4) - TODO IP6
        target_host = conf.INNER_SERVER_BIND_IP + ':' + str(self.__inner_service_port)
        GRPCHelper().add_server_port(self.inner_server, target_host, conf.SSLAuthType.none)

        # Block Generator 에 subscribe 하게 되면 Block Generator 는 peer 에 channel 생성을 요청한다.
        # 따라서 peer 의 gRPC 서버가 완전히 시작된 후 Block Generator 로 subscribe 요청을 하여야 한다.
        time.sleep(conf.WAIT_GRPC_SERVICE_START)

        try:
            while self.is_run():
                self.__run_loop_functions()
                time.sleep(conf.SLEEP_SECONDS_IN_SERVICE_NONE)
        except KeyboardInterrupt:
            logging.info("Server Stop by KeyboardInterrupt")
        finally:
            while not self.__subscriptions.empty():
                channel, subscribe_stub = self.__subscriptions.get()
                logging.info(f"Un subscribe to channel({channel}) server({subscribe_stub.target})")
                self.__un_subscribe(channel, self.__port, subscribe_stub)

            if self.__inner_service_port is not None:
                self.inner_server.stop(0)
            self.outer_server.stop(0)

        logging.info("Server thread Ended.")
