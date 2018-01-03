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
""" A class for gRPC service of Radio station """
import json
import logging

import loopchain.utils as util
from loopchain.baseservice import ObjectManager
from loopchain.protos import loopchain_pb2_grpc, message_code

# loopchain_pb2 를 아래와 같이 import 하지 않으면 broadcast 시도시 pickle 오류가 발생함
import loopchain_pb2


class AdminService(loopchain_pb2_grpc.RadioStationServicer):
    """Radiostation의 gRPC service를 구동하는 Class.
    """

    def __init__(self, admin_manager):
        self.__admin_manager = admin_manager
        self.__handler_map = {
            message_code.Request.status: self.__handler_status,
            message_code.Request.rs_send_channel_manage_info_to_rs: self.__handler_rs_send_channel_manage_info_to_rs,
            message_code.Request.rs_restart_channel: self.__handler_restart_channel
        }

    def __handler_status(self, request: loopchain_pb2.Message, context):
        util.logger.spam(f"rs_admin_service:__handler_status ({request.message})")
        return loopchain_pb2.Message(code=message_code.Response.success)

    def __handler_rs_send_channel_manage_info_to_rs(self, request, context):
        """

        :param request.code: message_code.Request.rs_send_channel_manage_info_to_rs
        :param request.meta: channel_manage_info
        :param request.message: from gtool or another rs
        """
        util.logger.spam(f"rs_admin_service:__handler_rs_send_channel_manage_info_to_rs")

        self.__admin_manager.save_channel_manage_data(json.loads(request.meta))
        logging.debug(f"rs_admin_service:__handler_rs_send_channel_manage_info_to_rs "
                      f"new channel_manage_data({self.__admin_manager.json_data})")

        # TODO 이 메시지가 gtool 에서 왔다면, 다른 rs 에도 전송한다.(rs 이중화 완료까지 보류)
        # TODO 이때는 메시지를 변경하여 출처를 gtool 이 아닌 rs 로 수정한다.

        return loopchain_pb2.Message(code=message_code.Response.success)

    def __handler_restart_channel(self, request, context):
        """

        :param request:
        :param context:
        :return:
        """
        util.logger.spam(f"rs_admin_service:__handler_restart_channel")

        message = loopchain_pb2.Message(
            code=message_code.Request.peer_restart_channel,
            channel=request.channel,
            message="restart channel"
        )

        ObjectManager().rs_service.channel_manager.broadcast(request.channel, "Request", message)

        return loopchain_pb2.Message(code=message_code.Response.success)

    def Request(self, request, context):
        logging.debug(f"rs_admin_service:Request({request})")
        logging.debug(f"get context : {context}")

        if request.code in self.__handler_map.keys():
            return self.__handler_map[request.code](request, context)

        logging.warning(f"rs_admin_service:Request not treat message code({request.code})")
        return loopchain_pb2.Message(code=message_code.Response.not_treat_message_code)
