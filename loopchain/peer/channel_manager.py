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
""" A class for Manage Channels """
import json
import leveldb
import logging
import pickle
import time

import loopchain.utils as util
from loopchain import configure as conf
from loopchain.baseservice import PeerManager, StubManager, ObjectManager, BroadcastProcess
from loopchain.container import CommonService, ScoreService
from loopchain.peer import BlockManager, SendToProcess
from loopchain.protos import loopchain_pb2_grpc, message_code, loopchain_pb2


class ChannelManager:
    """어떤 Peer가 loopchain network 에 접속할 권한을 가지고 있는지 어떤 채널에 속할 권한을 가지고 있는지 관리한다.
    이 데이터는 RS Admin site 를 통해서 설정될 수 있으며, 이중화 또는 3중화된 복수의 RS가 존재할 경우 이 데이터를 동기되어야한다.
    key 생성을 위한 난수표는 메모리상에만 존재해야 하며 나머지 데이터는 level DB 를 사용한다.
    """

    def __init__(self, common_service: CommonService, level_db_identity="station"):
        self.__common_service = common_service
        self.__level_db_identity = level_db_identity
        self.__peer_managers = {}  # key(channel_name):value(peer_manager)
        self.__block_managers = {}  # key(channel_name):value(block_manager), This available only peer
        self.__tx_send_to_process_thread = {}  # key(channel_name):value(thread), This available only peer
        self.__tx_processes = {}  # key(channel_name):value(tx_process), This available only peer
        self.__broadcast_processes = {}  # key(channel_name):value(broadcast_process)
        self.__score_containers = {}  # key(channel_name):value(score containers)
        self.__score_stubs = {}  # key(channel_name):value(score stub)
        self.__score_infos = {}  # key(channel_name):value(score info)
        self.__peer_auths = {}  # key(channel_name):value(peer_auth)
        self.__init_peer_auths()

        if ObjectManager().rs_service is not None:
            self.__init_rs_channel_manager()

    def start_broadcast_process(self, peer_id, peer_target, inner_target, channel):
        if inner_target is not None:
            #  rs has no tx process
            self.__tx_send_to_process_thread[channel] = SendToProcess()
            self.start_process(
                process_name=conf.TX_PROCESS_NAME,
                self_target=peer_target,
                notify_target=inner_target,
                channel=channel)
            self.__tx_send_to_process_thread[channel].start()

        self.start_process(
            process_name=conf.BROADCAST_PROCESS_NAME,
            self_target=peer_target,
            notify_target=inner_target,
            channel=channel)

        if peer_id is not None:
            self.__broadcast_processes[channel].set_to_process(
                BroadcastProcess.PROCESS_INFO_KEY, f"peer_id({peer_id})")

        return True

    def __init_peer_auths(self):
        for channel in list(conf.CHANNEL_OPTION):
            from loopchain.peer import PeerAuthorization
            self.__peer_auths[channel] = PeerAuthorization(channel)

    def start_process(self, process_name, self_target, notify_target, channel, is_audience_update=False):
        process = BroadcastProcess(process_name=process_name, channel=channel, self_target=notify_target)
        process.start()

        wait_times = 0
        wait_for_process_start = None

        # TODO process wait loop 를 살리고 시간을 조정하였음, 이 상태에서 tx process 가 AWS infra 에서 시작되는지 확인 필요.
        # time.sleep(conf.WAIT_SECONDS_FOR_SUB_PROCESS_START)

        while wait_for_process_start is None:
            time.sleep(conf.SLEEP_SECONDS_FOR_SUB_PROCESS_START)
            logging.debug(f"wait start {process_name}({channel})....")
            process.send_to_process(("status", ""))
            wait_for_process_start = process.get_receive("status")

            if wait_for_process_start is None and wait_times > conf.WAIT_SUB_PROCESS_RETRY_TIMES:
                util.exit_and_msg(f"{process_name} start Fail!({channel})")

            wait_times += 1

        logging.debug(f"{process_name} start({wait_for_process_start}) channel({channel})")

        if len(process_name.split(conf.TX_PROCESS_NAME)) > 1:
            self.__tx_send_to_process_thread[channel].set_process(process)
            self.__tx_processes[channel] = process
            process.send_to_process((BroadcastProcess.SUBSCRIBE_COMMAND, self_target))
        else:
            self.__broadcast_processes[channel] = process

        util.logger.spam(f"channel_manager:start_process notify_target({notify_target})")
        if notify_target is not None:
            # TODO Restart 시 아래 로직이 동작하지 않는다.
            process.send_to_process(
                (BroadcastProcess.MAKE_SELF_PEER_CONNECTION_COMMAND, notify_target))

        if is_audience_update:
            audience_dump = self.__peer_managers[channel].dump()
            process.send_to_process((BroadcastProcess.UPDATE_AUDIENCE_COMMAND, audience_dump))

        return process

    def load_block_manager(self, peer_id=None, channel=None):
        if channel is None:
            channel = conf.LOOPCHAIN_DEFAULT_CHANNEL
        logging.debug(f"load_block_manager_each channel({channel})")
        try:
            self.__block_managers[channel] = BlockManager(
                channel_manager=self,
                common_service=self.__common_service,
                peer_id=peer_id,
                channel_name=channel,
                level_db_identity=self.__level_db_identity
            )
        except leveldb.LevelDBError as e:
            util.exit_and_msg("LevelDBError(" + str(e) + ")")

    def get_channel_list(self) -> list:
        return list(self.__peer_managers)

    def get_peer_manager(self, channel_name=None) -> PeerManager:
        if channel_name is None:
            channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL
        return self.__peer_managers[channel_name]

    def get_block_manager(self, channel_name=None) -> BlockManager:
        if channel_name is None:
            channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL
        try:
            return self.__block_managers[channel_name]
        except KeyError as e:
            logging.warning(f"channel_manager:get_block_manager there is no channel({channel_name})")
            return None

    def get_broadcast_process(self, channel) -> BroadcastProcess:
        if channel is None:
            channel = conf.LOOPCHAIN_DEFAULT_CHANNEL
        try:
            return self.__broadcast_processes[channel]
        except KeyError as e:
            logging.warning(f"channel_manager:get_broadcast_process there is no channel({channel})")
            return None

    def get_peer_auth(self, channel):
        if channel is None:
            channel = conf.LOOPCHAIN_DEFAULT_CHANNEL
        try:
            return self.__peer_auths[channel]
        except KeyError as e:
            logging.warning(f"channel_manager:get_peer_auth there is no channel({channel})")
            return None

    def send_to_tx_process(self, channel, job):
        if channel in self.__tx_send_to_process_thread.keys():
            return self.__tx_send_to_process_thread[channel].send_to_process(job)
        else:
            logging.warning(f"channel_manager:get_tx_send_to_process_thread there is no channel({channel})")
            return False

    def add_audience(self, channel: str, peer_target: str):
        if channel in self.__tx_processes.keys():
            self.__tx_processes[channel].send_to_process((BroadcastProcess.SUBSCRIBE_COMMAND, peer_target))
        else:
            logging.debug(f"channel_manager:add_audience no channel({channel}) in tx_processes")
        if channel in self.__broadcast_processes.keys():
            self.__broadcast_processes[channel].send_to_process((BroadcastProcess.SUBSCRIBE_COMMAND, peer_target))
        else:
            logging.debug(f"channel_manager:add_audience no channel({channel}) in broadcast_processes")

    def remove_audience(self, channel, peer_target):
        if channel in self.__tx_processes.keys():
            self.__tx_processes[channel].send_to_process((BroadcastProcess.UNSUBSCRIBE_COMMAND, peer_target))
        else:
            logging.debug(f"channel_manager:remove_audience no channel({channel}) in tx_processes")
        if channel in self.__broadcast_processes.keys():
            self.__broadcast_processes[channel].send_to_process((BroadcastProcess.UNSUBSCRIBE_COMMAND, peer_target))
        else:
            logging.debug(f"channel_manager:remove_audience no channel({channel}) in broadcast_processes")

    def update_audience(self, channel, peer_manager_dump):
        if channel in self.__broadcast_processes.keys():
            self.__broadcast_processes[channel].send_to_process(
                (BroadcastProcess.UPDATE_AUDIENCE_COMMAND, peer_manager_dump))
        else:
            logging.debug(f"channel_manager:update_audience no channel({channel}) in broadcast_processes")

    def broadcast(self, channel, method_name, method_param, response_handler=None):
        """등록된 모든 Peer 의 동일한 gRPC method 를 같은 파라미터로 호출한다.
        """
        # logging.warning("broadcast in process ==========================")
        # logging.debug("pickle method_param: " + str(pickle.dumps(method_param)))
        if channel in self.__broadcast_processes.keys():
            self.__broadcast_processes[channel].send_to_process(
                (BroadcastProcess.BROADCAST_COMMAND, (method_name, method_param)))
        else:
            logging.debug(f"channel_manager:broadcast no channel({channel}) in broadcast_processes")

    def broadcast_audience_set(self, channel):
        if channel in self.__broadcast_processes.keys():
            self.__broadcast_processes[channel].send_to_process((BroadcastProcess.STATUS_COMMAND, "audience set"))
        else:
            logging.debug(f"channel_manager:broadcast_audience_set no channel({channel}) in broadcast_processes")

    def subscribe(self, channel, subscribe_target):
        if channel in self.__broadcast_processes.keys():
            self.__broadcast_processes[channel].send_to_process((BroadcastProcess.SUBSCRIBE_COMMAND, subscribe_target))
        else:
            logging.debug(f"channel_manager:subscribe no channel({channel}) in broadcast_processes")

    def tx_process_connect_to_leader(self, channel, leader_target):
        if channel in self.__tx_processes.keys():
            self.__tx_processes[channel].send_to_process((BroadcastProcess.CONNECT_TO_LEADER_COMMAND, leader_target))
            self.__tx_processes[channel].send_to_process((BroadcastProcess.SUBSCRIBE_COMMAND, leader_target))
        else:
            logging.debug(f"channel_manager:tx_process_connect_to_leader no channel({channel}) in tx_processes")

    def start_block_manager(self, channel):
        self.__block_managers[channel].start()

    def stop_block_manager(self, channel):
        self.__block_managers[channel].stop()

    def stop_block_managers(self):
        for channel in list(self.__block_managers.keys()):
            self.__block_managers[channel].stop()

    def remove_peer(self, peer_id, group_id):
        for peer_manager in self.__peer_managers:
            self.__peer_managers[peer_manager].remove_peer(peer_id, group_id)

    def set_peer_type(self, peer_type):
        """Set peer type when peer start only

        :param peer_type:
        :return:
        """
        for block_manager in self.__block_managers:
            self.__block_managers[block_manager].set_peer_type(peer_type)

    def save_peer_manager(self, peer_manager, channel_name=None):
        """peer_list 를 leveldb 에 저장한다.

        :param peer_manager:
        :param channel_name:
        """
        if channel_name is None:
            channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL
        level_db_key_name = str.encode(conf.LEVEL_DB_KEY_FOR_PEER_LIST)

        try:
            dump = peer_manager.dump()
            level_db = self.__block_managers[channel_name].get_level_db()
            level_db.Put(level_db_key_name, dump)
            # 아래의 audience dump update 는 안정성에 문제를 야기한다. (원인 미파악)
            # self.update_audience(dump)
        except AttributeError as e:
            logging.warning("Fail Save Peer_list: " + str(e))

    def __init_rs_channel_manager(self):
        for channel in ObjectManager().rs_service.admin_manager.get_channel_list():
            self.load_peer_manager(channel)
            self.start_broadcast_process(peer_id=None, peer_target=None, inner_target=None, channel=channel)

    def load_peer_manager(self, channel=None):
        """leveldb 로 부터 peer_manager 를 가져온다.

        :return: peer_manager
        """

        if channel is None:
            channel = conf.LOOPCHAIN_DEFAULT_CHANNEL
        peer_manager = PeerManager(channel)

        level_db_key_name = str.encode(conf.LEVEL_DB_KEY_FOR_PEER_LIST)

        if conf.IS_LOAD_PEER_MANAGER_FROM_DB:
            try:
                level_db = self.__block_managers[channel].get_level_db()
                peer_list_data = pickle.loads(level_db.Get(level_db_key_name))
                peer_manager.load(peer_list_data)
                logging.debug("load peer_list_data on yours: " + peer_manager.get_peers_for_debug())
            except KeyError:
                logging.warning("There is no peer_list_data on yours")

        self.__peer_managers[channel] = peer_manager

    def authorized_channels(self, peer_id) -> list:
        authorized_channels = []

        # TODO 실제 코드는 아래와 같아야 한다.
        # rs_admin_site 를 통해 형성된 peer auth manager 에서 peer 가 속한 channel 을 구해야 한다.
        # for channel in self.__peer_managers:
        #     logging.warning(f"channel is ({channel})")
        #     peer_manager = self.__peer_managers[channel]
        #
        #     if peer_manager is not None and peer_manager.get_peer(peer_id):
        #         authorized_channels.append(channel)

        # TODO 하지만 테스트를 위해서 우선 아래와 같이 모든 채널에 권한이 있는 것으로 리턴한다.
        for channel in list(self.__peer_managers):
            logging.warning(f"channel is ({channel})")
            authorized_channels.append(channel)

        logging.warning(f"authorized channels ({authorized_channels})")

        return authorized_channels

    def load_score_container(self, channel: str, score_package: str, container_port: int, peer_target: str):
        """create score container and save score_info and score_stub

        :param channel: channel name
        :param score_package: load score package name
        :param container_port: score container port
        :param peer_target: peer_target
        """
        score_info = None
        retry_times = 1

        start_param_set = dict()
        start_param_set["channel_name"] = channel
        start_param_set["score_package"] = score_package
        start_param_set["container_port"] = container_port
        start_param_set["peer_target"] = peer_target

        while score_info is None:
            if util.check_port_using(conf.IP_PEER, container_port) is False:
                util.logger.spam(f"channel_manager:load_score_container_each init ScoreService port({container_port})")
                self.__score_containers[channel] = ScoreService(container_port, channel, start_param_set)
                self.__score_stubs[channel] = StubManager.get_stub_manager_to_server(
                    conf.IP_PEER + ':' + str(container_port),
                    loopchain_pb2_grpc.ContainerStub,
                    is_allow_null_stub=True,
                    ssl_auth_type=conf.SSLAuthType.none
                )
            score_info = self.__load_score(score_package, self.get_score_container_stub(channel), peer_target)

            if score_info is not None or retry_times >= conf.SCORE_LOAD_RETRY_TIMES:
                break
            else:
                util.logger.spam(f"channel_manager:load_score_container_each score_info load fail retry({retry_times})")
                retry_times += 1
                time.sleep(conf.SCORE_LOAD_RETRY_INTERVAL)

        if score_info is None:
            return False

        self.__score_infos[channel] = score_info

        return True

    def __load_score(self, score_package_name: str, score_container_stub: StubManager, peer_target: str):
        """스코어를 로드한다.

        :param score_package_name: score package name
        """
        util.logger.spam(f"peer_service:__load_score --start--")
        logging.info("LOAD SCORE AND CONNECT TO SCORE SERVICE!")
        params = dict()
        params[message_code.MetaParams.ScoreLoad.repository_path] = conf.DEFAULT_SCORE_REPOSITORY_PATH
        params[message_code.MetaParams.ScoreLoad.score_package] = score_package_name
        params[message_code.MetaParams.ScoreLoad.base] = conf.DEFAULT_SCORE_BASE
        params[message_code.MetaParams.ScoreLoad.peer_id] = \
            None if ObjectManager().peer_service is None else ObjectManager().peer_service.peer_id
        meta = json.dumps(params)
        logging.debug(f"load score params : {meta}")

        if score_container_stub is None:
            util.exit_and_msg(f"there is no __stub_to_scoreservice!")

        util.logger.spam(f"peer_service:__load_score --1--")
        # Score Load is so slow ( load time out is more than GRPC_CONNECTION_TIMEOUT)
        response = score_container_stub.call(
            "Request",
            loopchain_pb2.Message(code=message_code.Request.score_load, meta=meta),
            conf.SCORE_LOAD_TIMEOUT
        )
        logging.debug("try score load on score service: " + str(response))
        if response is None:
            return None

        util.logger.spam(f"peer_service:__load_score --2--")
        response_connect = score_container_stub.call(
            "Request",
            loopchain_pb2.Message(code=message_code.Request.score_connect, message=peer_target),
            conf.GRPC_CONNECTION_TIMEOUT
        )
        logging.debug("try connect to score service: " + str(response_connect))
        if response_connect is None:
            return None

        if response.code == message_code.Response.success:
            logging.debug("Get Score from Score Server...")
            score_info = json.loads(response.meta)
        else:
            util.exit_and_msg("Fail Get Score from Score Server...")
        logging.info("LOAD SCORE DONE!")

        util.logger.spam(f"peer_service:__load_score --end--")

        return score_info

    def get_score_container_stub(self, channel_name=None) -> StubManager:
        """get score_stub corresponding to channel_name

        :param channel_name: channel_name default value is conf.LOOPCHAIN_DEFAULT_CHANNEL
        :return: score stub implements inner service
        :raise: KeyError: not exist stub corresponding to channel_name
        """
        if channel_name is None:
            channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL
        return self.__score_stubs[channel_name]

    def get_score_info(self, channel_name: str = None) -> dict:
        """get score_info corresponding to channel_name

        :param channel_name: channel_name
        :return: score_info
        :raise: KeyError: not exist stub corresponding to channel_name
        """
        if channel_name is None:
            channel_name = conf.LOOPCHAIN_DEFAULT_CHANNEL
        return self.__score_infos[channel_name]

    def stop_score_container(self, channel):
        self.__score_containers[channel].stop()

        # Stop Also Channel Processes
        if channel in self.__tx_processes.keys():
            self.__tx_send_to_process_thread[channel].stop()
            self.__tx_send_to_process_thread[channel].wait()

            self.__tx_processes[channel].stop()
            self.__tx_processes[channel].wait()

        if channel in self.__broadcast_processes.keys():
            self.__broadcast_processes[channel].stop()
            self.__broadcast_processes[channel].wait()

    def stop_score_containers(self):
        """stop all score containers and init all properties and this also stop broadcast processes

        :return:
        """
        for channel in self.__score_containers.keys():
            self.stop_score_container(channel)

        self.__score_containers = {}
        self.__score_infos = {}
        self.__score_stubs = {}
