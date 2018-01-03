#!/usr/bin/env python
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
"""Test Vote Object"""

import logging
import unittest
import loopchain.utils as util
import testcase.unittest.test_util as test_util
from loopchain.peer import Vote
from loopchain.baseservice import PeerManager, PeerInfo
from loopchain.protos import loopchain_pb2
from loopchain import configure as conf
from loopchain.tools.signature_helper import PublicVerifier

util.set_log_level_debug()


class TestVote(unittest.TestCase):

    __cert = None

    def setUp(self):
        test_util.print_testname(self._testMethodName)
        if self.__cert is None:
            with open(conf.CHANNEL_OPTION[list(conf.CHANNEL_OPTION)[0]][PublicVerifier.PUBLIC_PATH], "rb") as der:
                cert_byte = der.read()
                self.__cert = cert_byte

    def tearDown(self):
        pass

    def __make_peer_info(self, peer_id, group_id):
        peer_info = loopchain_pb2.PeerRequest()
        peer_info.peer_target = peer_id + "_target"
        peer_info.peer_type = loopchain_pb2.PEER
        peer_info.peer_id = peer_id
        peer_info.group_id = group_id
        peer_info.cert = self.__cert
        return peer_info

    def test_vote_init_from_audience(self):
        # GIVEN
        peer_info1 = self.__make_peer_info("peerid-1", "groupid-1")
        peer_info2 = self.__make_peer_info("peerid-2", "groupid-2")
        audience = {peer_info1.peer_id: peer_info1, peer_info2.peer_id: peer_info2}

        # WHEN
        vote = Vote("block_hash", audience)
        logging.debug("votes: " + str(vote.votes))

        # THEN
        self.assertTrue(vote.check_vote_init(audience))

    def test_vote_init_from_peer_list(self):
        # GIVEN
        peer_manager = PeerManager()
        self.__add_peer_to_peer_manager(peer_manager, 2)

        # WHEN
        vote = Vote("block_hash", peer_manager)
        logging.debug("votes: " + str(vote.votes))

        # THEN
        self.assertTrue(vote.check_vote_init(peer_manager))

    def __add_peer_to_peer_manager(self, peer_manager: PeerManager, number_of_peer):
        for i in range(1, number_of_peer + 1):
            number = str(i)
            peer_data = PeerInfo("peerid-" + number, "groupid-" + number, "peerid-" + number + "_target",
                                 cert=self.__cert)
            peer_manager.add_peer(peer_data)

    def test_vote_init_from_different_source(self):
        # GIVEN
        peer_info1 = self.__make_peer_info("peerid-1", "groupid-1")
        peer_info2 = self.__make_peer_info("peerid-2", "groupid-2")
        audience = {peer_info1.peer_id: peer_info1, peer_info2.peer_id: peer_info2}
        peer_manager = PeerManager()
        self.__add_peer_to_peer_manager(peer_manager, 2)

        # WHEN
        vote = Vote("block_hash", audience)
        logging.debug("votes: " + str(vote.votes))

        # THEN
        self.assertTrue(vote.check_vote_init(peer_manager))

    def test_add_vote(self):
        # GIVEN
        peer_manager = PeerManager()
        self.__add_peer_to_peer_manager(peer_manager, 3)
        peer_manager.add_peer(PeerInfo("peerid-4", "groupid-3", "peerid-4_target", cert=self.__cert))
        peer_manager.add_peer(PeerInfo("peerid-5", "groupid-3", "peerid-5_target", cert=self.__cert))

        vote = Vote("block_hash", peer_manager)
        logging.debug("votes: " + str(vote.votes))

        # WHEN
        vote.add_vote("groupid-1", "peerid-1", None)
        self.assertFalse(vote.get_result("block_hash", 0.51))

        # THEN
        vote.add_vote("groupid-2", "peerid-2", None)
        self.assertTrue(vote.get_result("block_hash", 0.51))

    def test_add_vote_fail_before_add_peer(self):
        # GIVEN
        peer_manager = PeerManager()
        self.__add_peer_to_peer_manager(peer_manager, 3)
        peer_manager.add_peer(PeerInfo("peerid-4", "groupid-3", "peerid-4_target", cert=self.__cert))
        peer_manager.add_peer(PeerInfo("peerid-5", "groupid-3", "peerid-5_target", cert=self.__cert))

        vote = Vote("block_hash", peer_manager)
        logging.debug("votes: " + str(vote.votes))

        # WHEN
        vote.add_vote("groupid-1", "peerid-1", None)
        vote.add_vote("groupid-3", "peerid-4", None)
        ret1 = vote.add_vote("groupid-4", "peerid-1", None)
        ret2 = vote.add_vote("groupid-1", "peerid-9", None)
        self.assertFalse(ret1)
        self.assertFalse(ret2)

        # THEN
        ret = vote.get_result_detail("block_hash", 0.51)
        self.assertEqual(ret[5], 5)

    def test_fail_vote(self):
        # GIVEN
        peer_manager = PeerManager()
        self.__add_peer_to_peer_manager(peer_manager, 3)
        peer_manager.add_peer(PeerInfo("peerid-4", "groupid-3", "peerid-4_target", cert=self.__cert))
        peer_manager.add_peer(PeerInfo("peerid-5", "groupid-3", "peerid-5_target", cert=self.__cert))

        vote = Vote("block_hash", peer_manager)
        logging.debug("votes: " + str(vote.votes))

        # WHEN
        vote.add_vote("groupid-1", "peerid-1", conf.TEST_FAIL_VOTE_SIGN)
        vote.add_vote("groupid-3", "peerid-4", conf.TEST_FAIL_VOTE_SIGN)
        vote.add_vote("groupid-3", "peerid-5", conf.TEST_FAIL_VOTE_SIGN)
        vote.get_result("block_hash", 0.51)

        # THEN
        self.assertTrue(vote.is_failed_vote("block_hash", 0.51))


if __name__ == '__main__':
    unittest.main()
