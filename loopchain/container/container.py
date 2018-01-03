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
"""A module for containers on the loopchain """

import logging
import setproctitle
from concurrent import futures
from enum import Enum

import grpc

import loopchain.utils as util
from loopchain import configure as conf
from loopchain.baseservice import CommonProcess, MonitorAdapter, ObjectManager, Monitor
from loopchain.protos import loopchain_pb2, loopchain_pb2_grpc, message_code
from loopchain.rest_server import RestServer, RestServerRS
from loopchain.tools.grpc_helper import GRPCHelper


class ServerType(Enum):
    REST_RS = 1
    REST_PEER = 2
    GRPC = 3


class Container(CommonProcess, MonitorAdapter):

    def __init__(self,
                 port,
                 server_type=ServerType.GRPC,
                 peer_ip=None,
                 process_name="",
                 channel="",
                 start_param_set=None):

        CommonProcess.__init__(self)
        if server_type == ServerType.GRPC:
            # monitoring gRPC Container
            MonitorAdapter.__init__(self, channel=channel, process_name=f"{process_name}")
        self._port = port
        self._type = server_type
        self._peer_ip = peer_ip
        self._process_name = process_name
        self._channel = channel
        self._start_param_set = start_param_set
        self._service_stub = None

    def is_alive(self):
        try:
            # util.logger.spam(f"{self._process_name} is_alive")
            response = self._service_stub.call(
                "Request",
                loopchain_pb2.Message(code=message_code.Request.is_alive))
            return True if response is not None else False
        except Exception as e:
            if self._service_stub is None:
                util.logger.spam(f"container:is_alive service_stub set now! ignore this exception({e})")
                peer_service = ObjectManager().peer_service
                if peer_service is not None:
                    self._service_stub = peer_service.channel_manager.get_score_container_stub(self._channel)
                return True
            logging.warning(f"container:is_alive has exception({e})")
            return False

    def re_start(self):
        # TODO 현재 상태에서는 Score Container 재시작중 Block 생성 요청이 들어오면 해당 피어가 비정상 동작을 하게 된다.
        # Score Container 의 재시작을 위해서는 스코어 무결성및 관련 기능의 추가 구현이 필요하다.
        # 우선은 Score Container 의 종료가 발견되면 전체 Peer 를 다운 시킨다.

        # ObjectManager().peer_service.channel_manager.load_score_container_each(**self._start_param_set)

        Monitor().stop_wait_monitoring()
        ObjectManager().peer_service.channel_manager.stop_score_containers()
        ObjectManager().peer_service.service_stop()
        util.exit_and_msg(f"Score Container({self._channel}) Down!")

    def run(self, conn):
        logging.debug("Container run...")

        if self._type == ServerType.GRPC:
            setproctitle.setproctitle(f"{setproctitle.getproctitle()} {self._process_name}")
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=conf.MAX_WORKERS))
            loopchain_pb2_grpc.add_ContainerServicer_to_server(self, server)
            GRPCHelper().add_server_port(server, '[::]:' + str(self._port), conf.SSLAuthType.none)
        elif self._type == ServerType.REST_PEER:
            server = RestServer(self._port, self._peer_ip)
            server.start()
        else:
            server = RestServerRS(self._port)
            server.start()

        command = None
        while command != "quit":
            try:
                command, param = conn.recv()  # Queue 에 내용이 들어올 때까지 여기서 대기 된다. 따라서 Sleep 이 필요 없다.
                logging.debug("Container got: " + str(param))
            except Exception as e:
                logging.warning("Container conn.recv() error: " + str(e))

        if self._type == ServerType.GRPC:
            server.stop(0)
        else:
            server.stop()

        logging.info("Server Container Ended.")
