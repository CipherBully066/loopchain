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
"""A management class for blockchain."""

import queue
import shutil

from loopchain.baseservice import CommonThread, ObjectManager, Timer, StubManager
from loopchain.blockchain import *
from loopchain.peer.candidate_blocks import CandidateBlocks
from loopchain.peer.consensus_default import ConsensusDefault
from loopchain.peer.consensus_lft import ConsensusLFT
from loopchain.peer.consensus_none import ConsensusNone
from loopchain.peer.consensus_siever import ConsensusSiever
from loopchain.protos import loopchain_pb2_grpc
from loopchain.tools.grpc_helper import GRPCHelper

# loopchain_pb2 를 아래와 같이 import 하지 않으면 broadcast 시도시 pickle 오류가 발생함
import loopchain_pb2


class BlockManager(CommonThread):
    """P2P Service 를 담당하는 BlockGeneratorService, PeerService 와 분리된
    Thread 로 BlockChain 을 관리한다.
    BlockGenerator 의 BlockManager 는 주기적으로 Block 을 생성하여 Peer 로 broadcast 한다.
    Peer 의 BlockManager 는 전달 받은 Block 을 검증 처리 한다.
    """
    def __init__(self, channel_manager, common_service, peer_id, channel_name, level_db_identity):
        self.__channel_manager = channel_manager
        self.__channel_name = channel_name
        self.__peer_id = peer_id
        self.__level_db = None
        self.__level_db_path = ""
        self.__level_db, self.__level_db_path = util.init_level_db(
            level_db_identity=f"{level_db_identity}_{channel_name}",
            allow_rename_path=False
        )
        self.__txQueue = queue.Queue()
        self.__unconfirmedBlockQueue = queue.Queue()
        self.__candidate_blocks = None
        if ObjectManager().peer_service is not None:
            self.__candidate_blocks = CandidateBlocks(ObjectManager().peer_service.peer_id, channel_name)
        self.__common_service = common_service
        self.__blockchain = BlockChain(self.__level_db, channel_name)
        self.__total_tx = self.__blockchain.rebuild_blocks()
        self.__peer_type = None
        self.__block_type = BlockType.general
        self.__consensus = None
        self.__run_logic = None
        self.__block_height_sync_lock = False
        self.set_peer_type(loopchain_pb2.PEER)

    @property
    def channel_name(self):
        return self.__channel_name

    @property
    def peer_type(self):
        return self.__peer_type

    @property
    def consensus(self):
        return self.__consensus

    @property
    def block_type(self):
        return self.__block_type

    @block_type.setter
    def block_type(self, block_type):
        self.__block_type = block_type

    def get_level_db(self):
        return self.__level_db

    def clear_all_blocks(self):
        logging.debug(f"clear level db({self.__level_db_path})")
        shutil.rmtree(self.__level_db_path)

    def set_peer_type(self, peer_type):
        self.__peer_type = peer_type

        if self.__peer_type == loopchain_pb2.BLOCK_GENERATOR:
            if conf.CONSENSUS_ALGORITHM == conf.ConsensusAlgorithm.none:
                self.__consensus = ConsensusNone(self)
            elif conf.CONSENSUS_ALGORITHM == conf.ConsensusAlgorithm.siever:
                self.__consensus = ConsensusSiever(self)
            elif conf.CONSENSUS_ALGORITHM == conf.ConsensusAlgorithm.lft:
                self.__consensus = ConsensusLFT(self)
            else:
                self.__consensus = ConsensusDefault(self)
            self.__run_logic = self.__consensus.consensus
        else:
            self.__run_logic = self.__do_vote

    def get_run_logic(self):
        try:
            return self.__run_logic.__name__
        except Exception as e:
            return "unknown"

    def get_total_tx(self):
        """
        블럭체인의 Transaction total 리턴합니다.

        :return: 블럭체인안의 transaction total count
        """
        return self.__total_tx

    def get_blockchain(self):
        return self.__blockchain

    def get_candidate_blocks(self):
        return self.__candidate_blocks

    def broadcast_send_unconfirmed_block(self, block):
        """생성된 unconfirmed block 을 피어들에게 broadcast 하여 검증을 요청한다.
        """
        logging.debug("BroadCast AnnounceUnconfirmedBlock...peers: " +
                      str(self.__channel_manager.get_peer_manager(
                          self.__channel_name).get_peer_count()))

        dump = pickle.dumps(block)
        if len(block.confirmed_transaction_list) > 0:
            self.__blockchain.increase_made_block_count()

        self.__channel_manager.broadcast(self.__channel_name,
                                         "AnnounceUnconfirmedBlock",
                                         (loopchain_pb2.BlockSend(
                                             block=dump,
                                             channel=self.__channel_name)))

    def broadcast_announce_confirmed_block(self, block_hash, block=None):
        """검증된 block 을 전체 peer 에 announce 한다.
        """
        logging.info("BroadCast AnnounceConfirmedBlock....")
        if self.__common_service is not None:
            if block is not None:
                dump = pickle.dumps(block)
                self.__channel_manager.broadcast(self.__channel_name,
                                                 "AnnounceConfirmedBlock",
                                                 (loopchain_pb2.BlockAnnounce(
                                                     block_hash=block_hash,
                                                     channel=self.__channel_name,
                                                     block=dump)))
            else:
                self.__channel_manager.broadcast(self.__channel_name,
                                                 "AnnounceConfirmedBlock",
                                                 (loopchain_pb2.BlockAnnounce(
                                                     block_hash=block_hash,
                                                     channel=self.__channel_name)))

    def broadcast_audience_set(self):
        """Check Broadcast Audience and Return Status

        """
        self.__channel_manager.broadcast_audience_set(channel=self.__channel_name)

    def add_tx(self, tx):
        """전송 받은 tx 를 Block 생성을 위해서 큐에 입력한다. txQueue 는 unloaded(dump) object 를 처리하므로
        tx object 는 dumps 하여 입력한다.

        :param tx: transaction object
        """
        tx_unloaded = pickle.dumps(tx)
        self.__txQueue.put(tx_unloaded)

    def add_tx_unloaded(self, tx):
        """전송 받은 tx 를 Block 생성을 위해서 큐에 입력한다. load 하지 않은 채 입력한다.

        :param tx: transaction object
        """
        self.__txQueue.put(tx)

    def get_tx(self, tx_hash):
        """tx_hash 로 저장된 tx 를 구한다.

        :param tx_hash: 찾으려는 tx 의 hash
        :return: tx object or None
        """
        return self.__blockchain.find_tx_by_key(tx_hash)

    def get_invoke_result(self, tx_hash):
        """ get invoke result by tx

        :param tx_hash:
        :return:
        """
        return self.__blockchain.find_invoke_result_by_tx_hash(tx_hash)

    def get_tx_queue(self):
        return self.__txQueue

    def get_count_of_unconfirmed_tx(self):
        """BlockManager 의 상태를 확인하기 위하여 현재 입력된 unconfirmed_tx 의 카운트를 구한다.

        :return: 현재 입력된 unconfirmed tx 의 갯수
        """
        return self.__txQueue.qsize()

    def confirm_block(self, block_hash):
        try:
            self.__total_tx += self.__blockchain.confirm_block(block_hash)
        except BlockchainError as e:
            logging.warning("BlockchainError, retry block_height_sync")
            self.block_height_sync()

    def add_unconfirmed_block(self, unconfirmed_block):
        # siever 인 경우 블럭에 담긴 투표 결과를 이전 블럭에 반영한다.
        if conf.CONSENSUS_ALGORITHM == conf.ConsensusAlgorithm.siever:
            if unconfirmed_block.prev_block_confirm:
                # logging.debug(f"block confirm by siever: "
                #               f"hash({unconfirmed_block.prev_block_hash}) "
                #               f"block.channel({unconfirmed_block.channel_name})")

                self.confirm_block(unconfirmed_block.prev_block_hash)
            elif unconfirmed_block.block_type is BlockType.peer_list:
                logging.debug(f"peer manager block confirm by siever: "
                              f"hash({unconfirmed_block.block_hash}) block.channel({unconfirmed_block.channel_name})")
                self.confirm_block(unconfirmed_block.block_hash)
            else:
                # 투표에 실패한 블럭을 받은 경우
                # 특별한 처리가 필요 없다. 새로 받은 블럭을 아래 로직에서 add_unconfirm_block 으로 수행하면 된다.
                pass
        elif conf.CONSENSUS_ALGORITHM == conf.ConsensusAlgorithm.lft:
            if unconfirmed_block.prev_block_confirm:

                # turn off previous vote's timer when a general peer received new block for vote
                ObjectManager().peer_service.timer_service.stop_timer(unconfirmed_block.prev_block_hash)
                # logging.debug(f"block confirm by lft: "
                #               f"hash({unconfirmed_block.prev_block_hash}) "
                #               f"block.channel({unconfirmed_block.channel_name})")

                self.confirm_block(unconfirmed_block.prev_block_hash)
            elif unconfirmed_block.block_type is BlockType.peer_list:
                logging.debug(f"peer manager block confirm by lft: "
                              f"hash({unconfirmed_block.block_hash}) block.channel({unconfirmed_block.channel_name})")
                self.confirm_block(unconfirmed_block.block_hash)
            else:
                # 투표에 실패한 블럭을 받은 경우
                # 특별한 처리가 필요 없다. 새로 받은 블럭을 아래 로직에서 add_unconfirm_block 으로 수행하면 된다.
                pass

        self.__unconfirmedBlockQueue.put(unconfirmed_block)

    def add_block(self, block):
        self.__total_tx += block.confirmed_transaction_list.__len__()
        self.__blockchain.add_block(block)

        peer_id = ObjectManager().peer_service.peer_id
        util.apm_event(peer_id, {
            'event_type': 'TotalTx',
            'peer_id': peer_id,
            'peer_name': conf.PEER_NAME,
            'channel_name': self.__channel_name,
            'data': {
                'block_hash': block.block_hash,
                'total_tx': self.__total_tx}})

    def block_height_sync(self, target_peer_stub=None):
        """synchronize block height with other peers"""

        # TODO : 멀티쓰레드에서  self.__block_height_sync_lock 이 문제가 될 수 있다
        if self.__block_height_sync_lock is True:
            # ***** 이 보정 프로세스는 AnnounceConfirmBlock 메시지를 받았을때 블럭 Height 차이로 Peer 가 처리하지 못한 경우에도 진행한다.
            # 따라서 이미 sync 가 진행 중일때의 요청은 무시한다.
            logging.warning("block height sync is already running...")
            return

        block_manager = self.__channel_manager.get_block_manager(self.__channel_name)
        peer_manager = self.__channel_manager.get_peer_manager(self.__channel_name)

        self.__block_height_sync_lock = True
        if target_peer_stub is None:
            target_peer_stub = peer_manager.get_leader_stub_manager()

        # The adjustment of block height and the process for data synchronization of peer
        # === Love&Hate Algorithm === #
        logging.info("try block height sync...with love&hate")

        # Make Peer Stub List [peer_stub, ...] and get max_height of network
        # max_height: current max height
        # peer_stubs: peer stub list for block height synchronization
        max_height, peer_stubs = self.__get_peer_stub_list()
        my_height = block_manager.get_blockchain().block_height

        if len(peer_stubs) == 0:
            util.logger.warning("peer_service:block_height_sync there is no other peer to height sync!")
            self.__block_height_sync_lock = False
            return

        logging.info(f"You need block height sync to: {max_height} yours: {my_height}")

        while max_height > my_height:
            for peer_stub in peer_stubs:
                response = None
                try:
                    # 이때 요청 받은 Peer 는 해당 Block 과 함께 자신의 현재 Height 를 같이 보내준다.
                    # TODO target peer 의 마지막 block 보다 높은 Peer 가 있으면 현재 target height 까지 완료 후
                    # TODO Height Sync 를 다시 한다.
                    response = peer_stub.BlockSync(loopchain_pb2.BlockSyncRequest(
                        block_height=my_height + 1,
                        channel=self.__channel_name
                    ), conf.GRPC_TIMEOUT)
                except Exception as e:
                    logging.warning("There is a bad peer, I hate you: " + str(e))

                if response is not None and response.response_code == message_code.Response.success:
                    util.logger.spam(f"response block_height({response.block_height})")
                    dump = response.block
                    block = pickle.loads(dump)

                    logging.debug(f"try add block height: {block.height}")

                    try:
                        block_manager.add_block(block)
                        my_height = block.height
                    except KeyError as e:
                        logging.error("fail block height sync: " + str(e))
                        break
                    except exception.BlockError as e:
                        logging.error("Block Error Clear all block and restart peer.")
                        block_manager.clear_all_blocks()
                        util.exit_and_msg("Block Error Clear all block and restart peer.")
                        break

                    if response.max_block_height > max_height:
                        max_height = response.max_block_height
                        
                else:
                    # 이 반복 요청중 응답 하지 않은 Peer 는 반복중에 다시 요청하지 않는다.
                    # (TODO: 향후 Bad에 대한 리포트 전략은 별도로 작업한다.)
                    peer_stubs.remove(peer_stub)
                    logging.warning("Make this peer to bad (error above or no response): " + str(peer_stub))

                    # update peer_stubs list
                    if len(peer_stubs) < 1:
                        max_height, peer_stubs = self.__get_peer_stub_list()

        if my_height < max_height:
            # block height sync 가 완료되지 않았으면 다시 시도한다.
            logging.warning("it's not completed block height synchronization in once ... try again...")
            self.__block_height_sync_lock = False
            self.block_height_sync(target_peer_stub)

        self.__block_height_sync_lock = False

    def __get_peer_stub_list(self):
        """It updates peer list for block manager refer to peer list on the loopchain network.
        This peer list is not same to the peer list of the loopchain network.

        :return max_height: a height of current blockchain
        :return peer_stubs: current peer list on the loopchain network
        """
        peer_target = ObjectManager().peer_service.peer_target
        peer_manager = self.__channel_manager.get_peer_manager(self.__channel_name)

        # Make Peer Stub List [peer_stub, ...] and get max_height of network
        max_height = 0      # current max height
        peer_stubs = []     # peer stub list for block height synchronization
        target_list = list(peer_manager.get_IP_of_peers_in_group())
        for peer_target_each in target_list:
            target = ":".join(peer_target_each.split(":")[1:])
            if target != peer_target:
                logging.debug(f"try to target({target})")
                channel = GRPCHelper().create_client_channel(target)
                stub = loopchain_pb2_grpc.PeerServiceStub(channel)
                try:
                    response = stub.GetStatus(loopchain_pb2.StatusRequest(
                        request="",
                        channel=self.__channel_name
                    ))
                    if response.block_height > max_height:
                        # Add peer as higher than this
                        max_height = response.block_height
                        peer_stubs.append(stub)
                except Exception as e:
                    logging.warning("Already bad.... I don't love you" + str(e))

        return max_height, peer_stubs

    def __close_level_db(self):
        del self.__level_db
        self.__level_db = None
        self.__blockchain.close_blockchain_db()

    def run(self):
        """Block Manager Thread Loop
        PEER 의 type 에 따라 Block Generator 또는 Peer 로 동작한다.
        Block Generator 인 경우 conf 에 따라 사용할 Consensus 알고리즘이 변경된다.
        """

        logging.info(f"channel({self.__channel_name}) Block Manager thread Start.")

        while self.is_run():
            self.__run_logic()

        # for reuse level db when restart channel.
        self.__close_level_db()

        logging.info(f"channel({self.__channel_name}) Block Manager thread Ended.")

    def __vote_unconfirmed_block(self, block_hash, is_validated, channel):
        logging.debug(f"block_manager:__vote_unconfirmed_block ({channel})")

        if is_validated:
            vote_code, message = message_code.get_response(message_code.Response.success_validate_block)
        else:
            vote_code, message = message_code.get_response(message_code.Response.fail_validate_block)

        block_vote = loopchain_pb2.BlockVote(
            vote_code=vote_code,
            channel=channel,
            message=message,
            block_hash=block_hash,
            peer_id=self.__peer_id,
            group_id=ObjectManager().peer_service.group_id)

        self.__channel_manager.broadcast(channel, "VoteUnconfirmedBlock", block_vote)

    def __do_vote(self):
        """Announce 받은 unconfirmed block 에 투표를 한다.
        """
        if not self.__unconfirmedBlockQueue.empty():
            unconfirmed_block = self.__unconfirmedBlockQueue.get()
            logging.debug("we got unconfirmed block ....")
        else:
            time.sleep(conf.SLEEP_SECONDS_IN_SERVICE_LOOP)
            # logging.debug("No unconfirmed block ....")
            return

        logging.info("PeerService received unconfirmed block: " + unconfirmed_block.block_hash)

        if unconfirmed_block.confirmed_transaction_list.__len__() == 0 and \
                unconfirmed_block.block_type is not BlockType.peer_list:
            # siever 에서 사용하는 vote block 은 tx 가 없다. (검증 및 투표 불필요)
            # siever 에서 vote 블럭 발송 빈도를 보기 위해 warning 으로 로그 남김, 그 외의 경우 아래 로그는 주석처리 할 것
            # logging.warning("This is vote block by siever")
            pass
        else:
            # block 검증
            block_is_validated = False
            try:
                block_is_validated = Block.validate(unconfirmed_block, self.__txQueue)
            except Exception as e:
                logging.error(e)

            if block_is_validated:
                # broadcast 를 받으면 받은 블럭을 검증한 후 검증되면 자신의 blockchain 의 unconfirmed block 으로 등록해 둔다.
                confirmed, reason = self.__blockchain.add_unconfirm_block(unconfirmed_block)
                if confirmed:
                    # block is confirmed
                    # validated 일 때 투표 할 것이냐? confirmed 일 때 투표할 것이냐? 현재는 validate 만 체크
                    pass
                elif reason == "block_height":
                    # Announce 되는 블럭과 자신의 height 가 다르면 Block Height Sync 를 다시 시도한다.

                    self.block_height_sync()

            self.__vote_unconfirmed_block(unconfirmed_block.block_hash, block_is_validated, self.__channel_name)

            if conf.CONSENSUS_ALGORITHM == conf.ConsensusAlgorithm.lft:
                # turn on timer when peer type is general after vote
                # TODO: set appropriate callback function and parameters
                timer = Timer(
                    unconfirmed_block.block_hash,
                    conf.TIMEOUT_FOR_PEER_VOTE,
                    ObjectManager().peer_service.timer_test_callback_function,
                    ["test after vote by block_manager"]
                )
                ObjectManager().peer_service.timer_service.add_timer(unconfirmed_block.block_hash, timer)
