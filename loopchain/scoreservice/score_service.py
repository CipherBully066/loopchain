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
""" A class for gRPC service of Score service"""

import logging
import setproctitle
import timeit

from loopchain.baseservice import ObjectManager
from loopchain.container import CommonService
from loopchain.protos import loopchain_pb2_grpc
from loopchain.scoreservice import ScoreOuterService

# loopchain_pb2 를 아래와 같이 import 하지 않으면 broadcast 시도시 pickle 오류가 발생함
import loopchain_pb2


class ScoreService:
    """Score service for stand alone start. It has gRPC interface for peer_service can invoke and query to score.
    """

    def __init__(self, channel, score_package, peer_target):
        """Score service init
        """

        self.__common_service = CommonService(loopchain_pb2)

        # gRPC service for Score Service
        self.__outer_service = ScoreOuterService(channel, score_package, peer_target)

        setproctitle.setproctitle(f"{setproctitle.getproctitle()} {channel}")
        ObjectManager().score_service = self

    @property
    def common_service(self):
        return self.__common_service

    def service_stop(self):
        self.__common_service.stop()

    def serve(self, port):
        """Run Score Service with port

        :param port:
        """

        stopwatch_start = timeit.default_timer()

        loopchain_pb2_grpc.add_ContainerServicer_to_server(self.__outer_service, self.__common_service.outer_server)

        logging.info("Start Score service at port: " + str(port))

        self.__common_service.start(port)

        stopwatch_duration = timeit.default_timer() - stopwatch_start
        logging.info(f"Start Score Service start duration({stopwatch_duration})")

        # service 종료를 기다린다.
        self.__common_service.wait()
