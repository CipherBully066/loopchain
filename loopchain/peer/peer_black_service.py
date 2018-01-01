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
"""gRPC service for Peer Black Service"""

import re

import grpc
from grpc._channel import _Rendezvous

from loopchain.baseservice import ObjectManager, BroadcastProcess, Monitor
from loopchain.blockchain import *
from loopchain.protos import loopchain_pb2_grpc, message_code

# loopchain_pb2 를 아래와 같이 import 하지 않으면 broadcast 시도시 pickle 오류가 발생함
import loopchain_pb2


class BlackOuterService(loopchain_pb2_grpc.PeerServiceServicer):
    """secure gRPC service for outer Client or other Peer
    """

    def __init__(self):
        self.__handler_map = {
            message_code.Request.status: self.__handler_status,
            message_code.Request.peer_peer_list: self.__handler_peer_list,
            message_code.Request.peer_reconnect_to_rs: self.__handler_reconnect_to_rs
        }

    @property
    def peer_service(self):
        return ObjectManager().peer_service

    def __handler_status(self, request, context):
        util.logger.debug(f"peer_outer_service:handler_status ({request.message})")

        if request.message == "get_stub_manager_to_server":
            # this case is check only gRPC available
            return loopchain_pb2.Message(code=message_code.Response.success)

        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        status = dict()

        status['peer_type'] = '0'
        if ObjectManager().peer_service is not None:
            block_manager = self.peer_service.channel_manager.get_block_manager(channel_name)
            if block_manager is not None:
                status['peer_type'] = block_manager.peer_type

        status_json = json.dumps(status)

        return loopchain_pb2.Message(code=message_code.Response.success, meta=status_json)

    def __handler_peer_list(self, request, context):
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        peer_manager = self.peer_service.channel_manager.get_peer_manager(channel_name)
        message = "All Group Peers count: " + str(len(peer_manager.peer_list[conf.ALL_GROUP_ID]))

        return loopchain_pb2.Message(
            code=message_code.Response.success,
            message=message,
            meta=str(peer_manager.peer_list))

    def __handler_reconnect_to_rs(self, request, context):
        logging.warning(f"RS lost peer info (candidate reason: RS restart)")
        logging.warning(f"try reconnect to RS....")
        ObjectManager().peer_service.connect_to_radiostation(channel=request.channel, is_reconnect=True)

        return loopchain_pb2.Message(code=message_code.Response.success)

    def Request(self, request, context):
        # util.logger.debug(f"Peer Service got request({request.code})")

        if request.code in self.__handler_map.keys():
            return self.__handler_map[request.code](request, context)

        return loopchain_pb2.Message(code=message_code.Response.not_treat_message_code)

    def GetStatus(self, request, context):
        """Peer 의 현재 상태를 요청한다.

        :param request:
        :param context:
        :return:
        """
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        logging.debug("Peer GetStatus : %s", request)
        peer_status = self.peer_service.common_service.getstatus(
            self.peer_service.channel_manager.get_block_manager(channel_name))

        return loopchain_pb2.StatusReply(
            status=json.dumps(peer_status),
            block_height=peer_status["block_height"],
            total_tx=peer_status["total_tx"],
            is_leader_complaining=peer_status['leader_complaint'])

    def GetScoreStatus(self, request, context):
        """Score Service 의 현재 상태를 요청 한다

        :param request:
        :param context:
        :return:
        """
        logging.debug("Peer GetScoreStatus request : %s", request)
        score_status = json.loads("{}")
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        try:
            score_status_response = self.peer_service.channel_manager.get_score_container_stub(channel_name).call(
                "Request",
                loopchain_pb2.Message(code=message_code.Request.status)
            )
            logging.debug("Get Score Status : " + str(score_status_response))
            if score_status_response.code == message_code.Response.success:
                score_status = json.loads(score_status_response.meta)

        except Exception as e:
            logging.debug("Score Service Already stop by other reason. %s", e)

        return loopchain_pb2.StatusReply(
            status=json.dumps(score_status),
            block_height=0,
            total_tx=0)

    def Stop(self, request, context):
        """Peer를 중지시킨다

        :param request: 중지요청
        :param context:
        :return: 중지결과
        """
        if request is not None:
            logging.info('Peer will stop... by: ' + request.reason)

        try:
            # process monitor must stop monitoring before any subprocess stop
            Monitor().stop()

            response = self.peer_service.channel_manager.stop_score_containers()
            logging.debug("try stop score container: " + str(response))
        except Exception as e:
            logging.debug("Score Service Already stop by other reason. %s", e)

        self.peer_service.service_stop()
        return loopchain_pb2.StopReply(status="0")

    def Echo(self, request, context):
        """gRPC 기본 성능을 확인하기 위한 echo interface, loopchain 기능과는 무관하다.

        :return: request 를 message 되돌려 준다.
        """
        return loopchain_pb2.CommonReply(response_code=message_code.Response.success,
                                         message=request.request)

    def CreateTx(self, request, context):
        """make tx by client request and broadcast it to the network

        :param request:
        :param context:
        :return:
        """
        logging.info(f"peer_outer_service::CreateTx request({request.data}), channel({request.channel})")

        tx = Transaction()
        # TODO self.__score 의 id 및 version 은 peer_score 에서 가져오고, expire 시킴

        score_id = ""
        score_version = ""
        result_code = message_code.Response.success
        more_info = ""

        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel

        try:
            # logging.debug("peer_outer_service create tx is have peer service info ")
            score_id = self.peer_service.channel_manager.get_score_info(channel_name)[
                message_code.MetaParams.ScoreInfo.score_id]
            score_version = self.peer_service.channel_manager.get_score_info(channel_name)[
                message_code.MetaParams.ScoreInfo.score_version]
        except KeyError as e:
            logging.debug(f"CreateTX : load score info fail\n"
                          f"cause : {e}")

        tx.init_meta(self.peer_service.peer_id, score_id, score_version, channel_name)
        result_hash = tx.put_data(request.data)
        tx.sign_hash(self.peer_service.auth)
        # logging.debug("peer_outer_service result hash : " + result_hash)

        # TODO 아래 코드는 성능에 영향을 준다. tx 출처를 기록하는 다른 방법을 고려할 것
        try:
            data_log = json.loads(request.data)
        except Exception as e:
            data_log = {'tx_hash': result_hash}

        util.apm_event(self.peer_service.peer_id, {
            'event_type': 'CreateTx',
            'peer_id': self.peer_service.peer_id,
            'peer_name': conf.PEER_NAME,
            'channel_name': channel_name,
            'tx_hash': result_hash,
            'data': data_log})

        self.peer_service.channel_manager.send_to_tx_process(channel_name, (BroadcastProcess.CREATE_TX_COMMAND, tx))

        return loopchain_pb2.CreateTxReply(
            response_code=result_code,
            tx_hash=result_hash,
            more_info=more_info)

    def AddTx(self, request: loopchain_pb2.TxSend, context):
        """Add tx to Block Manager

        :param request:
        :param context:
        :return:
        """
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        # logging.debug(f"peer_outer_service::AddTx channel({channel_name})")

        block_manager = self.peer_service.channel_manager.get_block_manager(channel_name)

        if block_manager.peer_type == loopchain_pb2.BLOCK_GENERATOR and block_manager.consensus.block is None:
            return loopchain_pb2.CommonReply(
                response_code=message_code.Response.fail_made_block_count_limited,
                message="this leader can't make more block")

        block_manager.add_tx_unloaded(request.tx)

        # TODO AddTx 는 성능에 민감한 구간으로 이곳에 기능과 무관한 코드를 삽입하면 성능에 영향을 줍니다.
        # 이 곳에서 tx_hash 를 로그로 남겨야 하면 request 에 tx_hash 를 포함해서 보내도록 코드를 수정해야 합니다.
        tx = pickle.loads(request.tx)

        # logger = sender.FluentSender('app', host=conf.MONITOR_LOG_HOST, port=conf.MONITOR_LOG_PORT)
        # logger.emit('follow', {'from': 'userA', 'to': 'userB'})
        # logger.emit_with_time('follow', time.time(), {'from': 'userA', 'to': 'userB'})
        # if not logger.emit('follow', {'from': 'userA', 'to': 'userB'}):
        #     logging.debug('hrkim>>event_test>>>>' + str(logger.last_error))
        #     logger.clear_last_error()
        # else:
        #     logging.debug('hrkim>>event_test>>success!!')
        #
        # logging.debug('hrkim>>event_test>>anyway passed')

        util.apm_event(self.peer_service.peer_id, {
            'event_type': 'AddTx',
            'peer_id': self.peer_service.peer_id,
            'peer_name': conf.PEER_NAME,
            'channel_name': channel_name,
            'data': {'tx_hash': tx.tx_hash}})

        return loopchain_pb2.CommonReply(response_code=message_code.Response.success, message="success")

    def GetTx(self, request, context):
        """get transaction

        :param request: tx_hash
        :param context:channel_loopchain_default
        :return:
        """
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        # logging.debug(f"peer_outer_service::GetTx channel({channel_name})")
        tx = self.peer_service.channel_manager.get_block_manager(channel_name).get_tx(request.tx_hash)

        # TODO 지금은 일반적인 fail 메시지로만 처리한다. 상세화 여지 있음, 필요시 추가 가능 (by winDy)
        response_code, response_msg = message_code.get_response(message_code.Response.fail)
        response_meta = ""
        response_data = ""
        response_sign = b''
        response_public_key = b''

        if tx is not None:
            response_code, response_msg = message_code.get_response(message_code.Response.success)
            response_meta = json.dumps(tx.meta)
            response_data = tx.get_data().decode(conf.PEER_DATA_ENCODING)
            response_sign = tx.signature
            response_public_key = tx.public_key

        return loopchain_pb2.GetTxReply(response_code=response_code,
                                        meta=response_meta,
                                        data=response_data,
                                        signature=response_sign,
                                        public_key=response_public_key,
                                        more_info=response_msg)

    def GetLastBlockHash(self, request, context):
        """ 마지막 블럭 조회

        :param request: 블럭요청
        :param context:
        :return: 마지막 블럭
        """
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        # Peer To Client
        block_manager = self.peer_service.channel_manager.get_block_manager(channel_name)
        last_block = block_manager.get_blockchain().last_block
        response_code, response_msg = message_code.get_response(message_code.Response.fail)
        block_hash = None

        if last_block is not None:
            response_code, response_msg = message_code.get_response(message_code.Response.success)
            block_hash = last_block.block_hash

        return loopchain_pb2.BlockReply(response_code=response_code,
                                        message=(response_msg +
                                                 (" This is for block height sync",
                                                  " This is for Test Validation")
                                                 [block_manager.peer_type == loopchain_pb2.PEER]),
                                        block_hash=block_hash)

    def GetBlock(self, request, context):
        """Block 정보를 조회한다.

        :param request: loopchain.proto 의 GetBlockRequest 참고
         request.block_hash: 조회할 block 의 hash 값, "" 로 조회하면 마지막 block 의 hash 값을 리턴한다.
         request.block_data_filter: block 정보 중 조회하고 싶은 key 값 목록 "key1, key2, key3" 형식의 string
         request.tx_data_filter: block 에 포함된 transaction(tx) 중 조회하고 싶은 key 값 목록
        "key1, key2, key3" 형식의 string
        :param context:
        :return: loopchain.proto 의 GetBlockReply 참고,
        block_hash, block 정보 json, block 에 포함된 tx 정보의 json 리스트를 받는다.
        포함되는 정보는 param 의 filter 에 따른다.
        """
        # Peer To Client
        block_hash = request.block_hash
        block = None

        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        block_manager = self.peer_service.channel_manager.get_block_manager(channel_name)

        if request.block_hash == "" and request.block_height == -1:
            block_hash = block_manager.get_blockchain().last_block.block_hash

        block_filter = re.sub(r'\s', '', request.block_data_filter).split(",")
        tx_filter = re.sub(r'\s', '', request.tx_data_filter).split(",")
        logging.debug("block_filter: " + str(block_filter))
        logging.debug("tx_filter: " + str(tx_filter))

        block_data_json = json.loads("{}")

        if block_hash != "":
            block = block_manager.get_blockchain().find_block_by_hash(block_hash)
        elif request.block_height != -1:
            block = block_manager.get_blockchain().find_block_by_height(request.block_height)

        if block is None:
            return loopchain_pb2.GetBlockReply(response_code=message_code.Response.fail_wrong_block_hash,
                                               block_hash=block_hash,
                                               block_data_json="",
                                               tx_data_json="")

        for key in block_filter:
            try:
                block_data_json[key] = str(getattr(block, key))
            except AttributeError:
                try:
                    getter = getattr(block, "get_" + key)
                    block_data_json[key] = getter()
                except AttributeError:
                    block_data_json[key] = ""

        tx_data_json_list = []
        for tx in block.confirmed_transaction_list:
            tx_data_json = json.loads("{}")
            for key in tx_filter:
                try:
                    tx_data_json[key] = str(getattr(tx, key))
                except AttributeError:
                    try:
                        getter = getattr(tx, "get_" + key)
                        tx_data_json[key] = getter()
                    except AttributeError:
                        tx_data_json[key] = ""
            tx_data_json_list.append(json.dumps(tx_data_json))

        block_hash = block.block_hash
        block_data_json = json.dumps(block_data_json)

        return loopchain_pb2.GetBlockReply(response_code=message_code.Response.success,
                                           block_hash=block_hash,
                                           block_data_json=block_data_json,
                                           tx_data_json=tx_data_json_list)

    def Query(self, request, context):
        """Score 의 invoke 로 생성된 data 에 대한 query 를 수행한다."""
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel

        # TODO 입력값 오류를 검사하는 방법을 고려해본다, 현재는 json string 여부만 확인
        if util.check_is_json_string(request.params):
            logging.debug(f'Query request with {request.params}')
            try:
                response_from_score_service = \
                    self.peer_service.channel_manager.get_score_container_stub(channel_name).call(
                        method_name="Request",
                        message=loopchain_pb2.Message(code=message_code.Request.score_query, meta=request.params),
                        timeout=conf.SCORE_QUERY_TIMEOUT,
                        is_raise=True
                    )
                response = response_from_score_service.meta

                util.apm_event(self.peer_service.peer_id, {
                    'event_type': 'Query',
                    'peer_id': self.peer_service.peer_id,
                    'peer_name': conf.PEER_NAME,
                    'channel_name': channel_name,
                    'data': {'score_query': json.loads(request.params)}})

            except Exception as e:
                logging.error(f'Execute Query Error : {e}')
                if isinstance(e, _Rendezvous):
                    # timeout 일 경우
                    if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                        return loopchain_pb2.QueryReply(response_code=message_code.Response.timeout_exceed,
                                                        response="")
                return loopchain_pb2.QueryReply(response_code=message_code.Response.fail,
                                                response="")
        else:
            return loopchain_pb2.QueryReply(response_code=message_code.Response.fail_validate_params,
                                            response="")

        if util.check_is_json_string(response):
            # TODO 응답값 오류를 검사하는 방법을 고려해본다, 현재는 json string 여부만 확인
            response_code = message_code.Response.success
        else:
            response_code = message_code.Response.fail

        return loopchain_pb2.QueryReply(response_code=response_code, response=response)

    def GetInvokeResult(self, request, context):
        """get invoke result by tx_hash

        :param request: request.tx_hash = tx_hash
        :param context:
        :return: verify result
        """
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        logging.debug(f"peer_outer_service:GetInvokeResult in channel({channel_name})")

        try:
            invoke_result = \
                self.peer_service.channel_manager.get_block_manager(channel_name).get_invoke_result(request.tx_hash)
            invoke_result_str = json.dumps(invoke_result)
            logging.debug('invoke_result : ' + invoke_result_str)

            util.apm_event(self.peer_service.peer_id, {
                'event_type': 'GetInvokeResult',
                'peer_id': self.peer_service.peer_id,
                'peer_name': conf.PEER_NAME,
                'channel_name': channel_name,
                'data': {'invoke_result': invoke_result, 'tx_hash': request.tx_hash}})
            return loopchain_pb2.GetInvokeResultReply(response_code=message_code.Response.success
                                                      , result=invoke_result_str)
        except Exception as e:
            logging.error(f"get invoke result error : {e}")
            util.apm_event(self.peer_service.peer_id, {
                'event_type': 'Error',
                'peer_id': self.peer_service.peer_id,
                'peer_name': conf.PEER_NAME,
                'channel_name': channel_name,
                'data': {
                    'error_type': 'InvokeResultError',
                    'code': message_code.Response.fail,
                    'message': f"get invoke result error : {e}"}})
            return loopchain_pb2.GetInvokeResultReply(response_code=message_code.Response.fail)

    def AnnounceUnconfirmedBlock(self, request, context):
        """수집된 tx 로 생성한 Block 을 각 peer 에 전송하여 검증을 요청한다.

        :param request:
        :param context:
        :return:
        """
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        logging.debug(f"peer_outer_service::AnnounceUnconfirmedBlock channel({channel_name})")
        unconfirmed_block = pickle.loads(request.block)

        logging.warning("Black Peer makes Fail validate Message by intention!")
        vote_code, message = message_code.get_response(message_code.Response.fail_validate_block)

        block_vote = loopchain_pb2.BlockVote(
            vote_code=vote_code,
            channel=channel_name,
            message=message,
            block_hash=unconfirmed_block.block_hash,
            peer_id=ObjectManager().peer_service.peer_id,
            group_id=ObjectManager().peer_service.group_id)

        self.peer_service.channel_manager.broadcast(channel_name, "VoteUnconfirmedBlock", block_vote)

        return loopchain_pb2.CommonReply(response_code=message_code.Response.success, message="success")

    def AnnounceConfirmedBlock(self, request, context):
        """Block Generator 가 announce 하는 인증된 블록의 대한 hash 를 전달받는다.

        :param request: BlockAnnounce of loopchain.proto
        :param context: gRPC parameter
        :return: CommonReply of loopchain.proto
        """
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel

        # Peer To BlockGenerator
        logging.debug("AnnounceConfirmedBlock block hash: " + request.block_hash)
        response_code, response_msg = message_code.get_response(message_code.Response.fail_announce_block)

        confirmed_block = pickle.loads(request.block)

        logging.debug(f"block \n"
                      f"peer_id({confirmed_block.peer_id})\n"
                      f"made_block_count({confirmed_block.made_block_count})\n"
                      f"is_divided_block({confirmed_block.is_divided_block})")

        if len(request.block) > 0:
            logging.warning("AnnounceConfirmedBlock without Consensus ====================")
            # 아래의 return 값을 확인하지 않아도 예외인 경우 아래 except 에서 확인된다.
            self.peer_service.add_unconfirm_block(request.block, channel_name)

        try:
            self.peer_service.channel_manager.get_block_manager(channel_name).confirm_block(request.block_hash)
            response_code, response_msg = message_code.get_response(message_code.Response.success_announce_block)
        except (BlockchainError, BlockInValidError, BlockError) as e:
            logging.error("AnnounceConfirmedBlock: " + str(e))

        return loopchain_pb2.CommonReply(response_code=response_code, message=response_msg)

    def BlockSync(self, request, context):
        # Peer To Peer
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        logging.info(f"BlockSync request hash({request.block_hash}) channel({channel_name})")
        block_manager = self.peer_service.channel_manager.get_block_manager(channel_name)

        block = block_manager.get_blockchain().find_block_by_hash(request.block_hash)
        if block is None:
            return loopchain_pb2.BlockSyncReply(
                response_code=message_code.Response.fail_wrong_block_hash,
                block_height=-1,
                max_block_height=block_manager.get_blockchain().block_height,
                block=b"")

        dump = pickle.dumps(block)

        return loopchain_pb2.BlockSyncReply(
            response_code=message_code.Response.success,
            block_height=block.height,
            max_block_height=block_manager.get_blockchain().block_height,
            block=dump)

    def Subscribe(self, request, context):
        """BlockGenerator 가 broadcast(unconfirmed or confirmed block) 하는 채널에
        Peer 를 등록한다.

        :param request:
        :param context:
        :return:
        """
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        if request.peer_id == "":
            return loopchain_pb2.CommonReply(
                response_code=message_code.get_response_code(message_code.Response.fail_wrong_subscribe_info),
                message=message_code.get_response_msg(message_code.Response.fail_wrong_subscribe_info)
            )
        else:
            self.peer_service.channel_manager.add_audience(channel_name, request.peer_target)

        return loopchain_pb2.CommonReply(response_code=message_code.get_response_code(message_code.Response.success),
                                         message=message_code.get_response_msg(message_code.Response.success))

    def UnSubscribe(self, request, context):
        """BlockGenerator 의 broadcast 채널에서 Peer 를 제외한다.

        :param request:
        :param context:
        :return:
        """
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        self.peer_service.channel_manager.remove_audience(channel_name, request.peer_target)
        return loopchain_pb2.CommonReply(response_code=0, message="success")

    def AnnounceNewPeer(self, request, context):
        """RadioStation에서 Broadcasting 으로 신규 피어정보를 받아온다

        :param request: PeerRequest
        :param context:
        :return:
        """
        # RadioStation To Peer
        # prevent to show certificate content
        # logging.info('Here Comes new peer: ' + str(request))
        channel = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        # logging.debug(f"peer outer service::AnnounceNewPeer channel({channel_name})")
        peer_manager = self.peer_service.channel_manager.get_peer_manager(channel)

        if len(request.peer_object) > 0:
            peer = pickle.loads(request.peer_object)
            # 서버로부터 발급된 토큰 검증
            # Secure 인 경우 검증에 통과하여야만 peer_list에 추가함
            # TODO KMS 확정 전까지 보류 토큰 사용 안할 가능성이 높음
            # if self.peer_service.auth.is_secure\
            #         and self.peer_service.auth.verify_new_peer(peer, loopchain_pb2.PEER) is False:
            #     # TODO AnnounceNewPeer 과정을 실패로 처리한다.
            #     logging.debug("New Peer Validation Fail")
            # else:
            #     logging.debug("Add New Peer: " + str(peer.peer_id))
            #     self.peer_service.peer_manager.add_peer(peer)
            #     logging.debug("Try save peer list...")
            #     self.peer_service.common_service.save_peer_list(self.peer_service.peer_manager)

            logging.debug("Add New Peer: " + str(peer.peer_id))

            peer_manager.add_peer(peer)
            # broadcast the new peer to the others for adding an audience
            self.peer_service.channel_manager.add_audience(channel, request.peer_target)

            logging.debug("Try save peer list...")
            self.peer_service.channel_manager.save_peer_manager(peer_manager, channel)

        self.peer_service.show_peers(channel)

        # Block generator makes a peer_manager block up when a new peer joins the network.
        if self.peer_service.channel_manager.get_block_manager(channel).peer_type is loopchain_pb2.BLOCK_GENERATOR:
            # TODO leader 가 peer manager tx 를 생성하여 블록에 peer 정보를 담는다면 채널별로 peer manager 를 저장할 필요도 있지
            # 않을까? 현재는 default 채널의 peer 만 announce new peer 와 peer manager tx 생성이 이뤄지고 있다.
            self.add_peer_manager_tx(channel)
            # util.apm_event(self.peer_service.peer_id, {
            #     'event_type': 'AddPeerManagerTx',
            #     'peer_id': self.peer_service.peer_id})

        return loopchain_pb2.CommonReply(response_code=0, message="success")

    def add_peer_manager_tx(self, channel_name):
        """peer_manager block을 생성하기 위한 Transaction을 추가한다
        이 기능은 Block Generator 에서만 동작해야 한다. 일반 Peer 는 이 기능을 사용할 권한을 가져서는 안된다.

        :return:
        """
        tx = Transaction()
        tx.type = TransactionType.peer_list
        tx.put_meta(Transaction.CHANNEL_KEY, channel_name)
        tx.put_meta(Transaction.PEER_ID_KEY, self.peer_service.peer_id)
        tx.put_data(self.peer_service.channel_manager.get_peer_manager(channel_name).dump())

        self.peer_service.channel_manager.send_to_tx_process(channel_name, ("create_tx", tx))

        if self.peer_service.channel_manager.get_block_manager(channel_name).consensus.block is None:
            logging.debug("this leader can't make more block")

        self.peer_service.channel_manager.get_block_manager(channel_name).add_tx_unloaded(pickle.dumps(tx))

    def AnnounceDeletePeer(self, request, context):
        """delete peer by radio station heartbeat, It delete peer info over whole channels.

        :param request:
        :param context:
        :return:
        """
        # TODO 현재 RS heartbeat 은 channel 별로 deletepeer 를 발생하도록 되어 있지만, 우선 하나의 channel 에만
        # 이상이 발생한 peer 도 전체에서 제거하도록 처리하고 있다.

        # channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        # logging.debug(f"AnnounceDeletePeer peer_id({request.peer_id}) group_id({request.group_id})")
        self.peer_service.channel_manager.remove_peer(request.peer_id, request.group_id)

        return loopchain_pb2.CommonReply(response_code=0, message="success")

    def VoteUnconfirmedBlock(self, request, context):
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        block_manager = self.peer_service.channel_manager.get_block_manager(channel_name)
        util.logger.spam(f"peer_outer_service:VoteUnconfirmedBlock ({channel_name})")
        peer_type = loopchain_pb2.PEER
        if block_manager is not None:
            peer_type = block_manager.peer_type

        if conf.CONSENSUS_ALGORITHM != conf.ConsensusAlgorithm.lft:
            if peer_type == loopchain_pb2.PEER:
                # util.logger.warning(f"peer_outer_service:VoteUnconfirmedBlock ({channel_name}) Not Leader Peer!")
                return loopchain_pb2.CommonReply(
                    response_code=message_code.Response.fail_no_leader_peer,
                    message=message_code.get_response_msg(message_code.Response.fail_no_leader_peer))

        logging.info("Peer vote to : " + request.block_hash + " " + str(request.vote_code)
                     + f"from {request.peer_id}")

        block_manager.get_candidate_blocks().vote_to_block(
            request.block_hash, (False, True)[request.vote_code == message_code.Response.success_validate_block],
            request.peer_id, request.group_id)

        return loopchain_pb2.CommonReply(response_code=message_code.Response.success, message="success")

    def ComplainLeader(self, request, context):
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        logging.debug("ComplainLeader: " + request.message)

        # TODO AnnounceComplained 메시지를 브로드 캐스트 하여 ComplainLeader 에 대한 투표를 받는다.
        # 수집후 AnnounceNewLeader 메시지에 ComplainLeader 투표 결과를 담아서 발송한다.
        # 현재 우선 AnnounceNewLeader 를 즉시 전송하게 구현한다. Leader Change 를 우선 확인하기 위한 임시 구현
        self.peer_service.channel_manager.get_peer_manager(channel_name).announce_new_leader(
            request.complained_leader_id, request.new_leader_id)

        return loopchain_pb2.CommonReply(response_code=message_code.Response.success, message="success")

    def AnnounceNewLeader(self, request, context):
        channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL if request.channel == '' else request.channel
        logging.debug(f"AnnounceNewLeader({channel_name}): " + request.message)
        self.peer_service.reset_leader(request.new_leader_id, channel_name)
        return loopchain_pb2.CommonReply(response_code=message_code.Response.success, message="success")
