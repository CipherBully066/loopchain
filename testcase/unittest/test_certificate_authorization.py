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
"""Test Certificate authorization"""

import logging
import sys
import unittest

import os
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding, ec

import loopchain.utils as util
import testcase.unittest.test_util as test_util
from loopchain.configure_default import KeyLoadType
from loopchain.peer import PeerAuthorization
from loopchain.radiostation import CertificateAuthorization, RadioStationService
from loopchain import configure as conf

sys.path.append('../')

util.set_log_level_debug()


class TestCertificateAuthorization(unittest.TestCase):
    __ca = CertificateAuthorization()

    def setUp(self):
        test_util.print_testname(self._testMethodName)
        cert_path = os.path.join(os.path.dirname(__file__), "../../resources/unittest/CA")
        cert_pass = None
        self.__ca.load_pki(cert_path, cert_pass)

    def tearDown(self):
        """ Changed Option Reset
        """
        channel0 = conf.LOOPCHAIN_DEFAULT_CHANNEL
        channel1 = conf.LOOPCHAIN_TEST_CHANNEL

        conf.CHANNEL_OPTION = {
            channel0: {
                "load_cert": False,
                "consensus_cert_use": False,
                "tx_cert_use": False,
                "key_load_type": KeyLoadType.FILE_LOAD,
                "public_path": os.path.join(conf.LOOPCHAIN_ROOT_PATH, 'resources/default_pki/public.der'),
                "private_path": os.path.join(conf.LOOPCHAIN_ROOT_PATH, 'resources/default_pki/private.der'),
                "private_password": b'test'
            },
            channel1: {
                "load_cert": False,
                "consensus_cert_use": False,
                "tx_cert_use": False,
                "key_load_type": KeyLoadType.FILE_LOAD,
                "public_path": os.path.join(conf.LOOPCHAIN_ROOT_PATH, 'resources/default_pki/public.der'),
                "private_path": os.path.join(conf.LOOPCHAIN_ROOT_PATH, 'resources/default_pki/private.der'),
                "private_password": b'test'
            }
        }

    def test_ca_certificate(self):
        """
        CA인증서 로딩 및 Peer 서명 검증
        radiostation/certificate_authorization.py 테스트
        """

        # CA 인증서 서명/검증 테스트
        data = b"Test"
        ca_sign_data = self.__ca.sign_data(data=data)
        ca_sign_validation = self.__ca.verify_data(data=data, signature=ca_sign_data)
        logging.debug("CA Signature Validation : %s", ca_sign_validation)

        peer_pw = None
        peer = self.read_file("TestPeer1", peer_pw)
        peer_cert = peer['cert']
        peer_priv = peer['private_key']

        # Peer 인증서 서명 검증
        peer_cert_validation = self.__ca.verify_certificate(peer_cert=peer_cert)
        logging.debug("Peer Cert Validation : %s", peer_cert_validation)

        # Peer가 생성한 서명 검증 및 Peer인증서 검증
        peer_sign = self.__generate_sign(pri_key=peer_priv, data=data)
        peer_sign_validation = self.__ca.verify_data_with_cert(cert=peer_cert, data=data, signature=peer_sign)
        logging.debug("Peer Signature Validation : %s", peer_sign_validation)
        self.assertTrue(peer_sign)

    def test_subject_certificate(self):
        """
        상위 인증서로 인증한 하위 인증서 검증
        """
        # 인증서/키 파일로드
        ca_cert = self.read_file('CA', None)

        # 값 인증
        data = b"TEST"
        signature = self.__generate_sign(pri_key=ca_cert['private_key'], data=data)
        self.assertTrue(
            self.__ca.verify_data_with_cert(
                cert=ca_cert['cert'],
                data=data,
                signature=signature
            )
        )

    def __generate_sign(self, pri_key, data):
        """
        전자서명 생성

        :param pri_key: 서명에 사용할 개인 키
        :param data: 서명 원문 데이터
        :return: 생성된 서명 데이터
        """
        _signature = None
        # 개인키의 Type(RSA, ECC)에 따라 서명 방식 분리
        if isinstance(pri_key, ec.EllipticCurvePrivateKeyWithSerialization):
            # ECDSA 서명
            logging.debug("Sign ECDSA")

            signer = pri_key.signer(ec.ECDSA(hashes.SHA256()))
            signer.update(data)
            _signature = signer.finalize()
        elif isinstance(pri_key, rsa.RSAPrivateKeyWithSerialization):
            # RSA 서명
            logging.debug("Sign RSA")

            _signature = pri_key.sign(
                data,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
        else:
            logging.debug("Unknown PrivateKey Type : %s", type(pri_key))

        return _signature

    def read_file(self, subject_name, pw=None):
        """
        파일로드 메소드
        
        :param subject_name: 로드할 테스트 인증서 타입
        :return: 테스트 인증서
        """
        pem_path = os.path.join(os.path.dirname(__file__),
                                "../../resources/unittest/" + subject_name + "/cert.pem")
        f = open(pem_path, "rb")
        cert_pem = f.read()
        f.close()
        cert = x509.load_pem_x509_certificate(cert_pem, default_backend())

        key_path = os.path.join(os.path.dirname(__file__),
                                "../../resources/unittest/" + subject_name + "/key.pem")
        f = open(key_path, "rb")
        cert_key = f.read()
        f.close()

        private_key = serialization.load_pem_private_key(cert_key, pw, default_backend())
        return {'cert': cert, 'private_key': private_key}

    @unittest.skip("지금 사용하지 않는 feature, RS Admin 설계를 다시하여 옵션에따라 Channel 별로 RandomTable을 리턴하도록 수정해야한다. 작업 Load가 많이 걸림")
    def test_load_pki_by_seed(self):
        """GIVEN random table conf.KMS = TRUE
        WHEN create two PeerAuthorization
        THEN create PeerAuthorization success
        THEN both PeerAuthorization sign and verify can both signature
        """

        # GIVEN
        conf.CHANNEL_OPTION = {
                                    "kofia_certificate": {
                                        "key_load_type": KeyLoadType.RANDOM_TABLE_DERIVATION,
                                        "seed1": 50,
                                        "seed2": 25
                                    },
                                    "kofia_fine": {
                                        "key_load_type": KeyLoadType.RANDOM_TABLE_DERIVATION,
                                        "seed1": 50,
                                        "seed2": 25
                                    }
                                }

        seed = 1234
        rs_service = RadioStationService(rand_seed=seed)
        rand_table = rs_service._RadioStationService__random_table

        # WHEN THEN
        peer_auth = PeerAuthorization("kofia_certificate")
        peer_auth.load_from_rand_table(rand_table)
        peer_auth2 = PeerAuthorization("kofia_fine")
        peer_auth2.load_from_rand_table(rand_table)

        # THEN
        sign = peer_auth.sign_data(b'a')
        sign2 = peer_auth2.sign_data(b'a')
        # both public key must same
        self.assertEqual(peer_auth.peer_cert, peer_auth2.peer_cert)
        # both peer_auth can verify signature
        self.assertTrue(peer_auth.verify_data(b'a', sign2))
        self.assertTrue(peer_auth2.verify_data(b'a', sign))

        # if have another seed can't verify
        conf.MY_SEED = 100
        peer_auth3 = PeerAuthorization(rand_table=rand_table)
        self.assertFalse(peer_auth3.verify_data(b'a', sign))

    def test_load_cert(self):
        """GIVEN conf.PEER_CERT_AUTH = True and GIVEN Sample ECDSA Certificate
        WHEN PeerAuthorization create using cert set
        THEN PeerAuthorization can create by cert
        """
        # GIVEN
        channel_name = "cert_channel"
        conf.CHANNEL_OPTION = {
            channel_name: {
                "load_cert": True,
                "consensus_cert_use": False,
                "tx_cert_use": False,
                "key_load_type": KeyLoadType.FILE_LOAD,
                "public_path": os.path.join(conf.LOOPCHAIN_ROOT_PATH, 'resources/default_certs/cert.pem'),
                "private_path": os.path.join(conf.LOOPCHAIN_ROOT_PATH, 'resources/default_certs/key.pem'),
                "private_password": None
            }
        }

        # WHEN THEN
        peer_auth = PeerAuthorization(channel_name)


if __name__ == '__main__':
    unittest.main()
