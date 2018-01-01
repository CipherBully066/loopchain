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
"""Signature Helper for Tx, Vote, Block Signature verify"""

import logging

import binascii
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils, rsa, padding
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from cryptography.x509 import Certificate
from loopchain import configure as conf


class PublicVerifier:
    """provide signature verify function using public key"""

    # KEY OPTION JSON NAME
    LOAD_CERT = "load_cert"
    CONSENSUS_CERT_USE = "consensus_cert_use"
    TX_CERT_USE = "tx_cert_use"
    PUBLIC_PATH = "public_path"
    PRIVATE_PATH  = "private_path"
    PRIVATE_PASSWORD = "private_password"
    KEY_LOAD_TYPE = "key_load_type"
    KEY_ID = "key_id"

    def __init__(self, channel):
        """init members to None and set verify function you must run load_key function

        :param channel: using channel name
        """

        self._public_key: EllipticCurvePublicKey = None
        self._cert: Certificate = None
        self._public_der: bytes = None
        self._cert_der: bytes = None

        self._channel = channel
        self._channel_option = conf.CHANNEL_OPTION[self._channel]

        self._tx_verifier_load_function = None
        self._consensus_verifier_load_function = None

        if self._channel_option[self.CONSENSUS_CERT_USE]:
            self._consensus_verifier_load_function = PublicVerifier._load_cert_from_der
        else:
            self._consensus_verifier_load_function = PublicVerifier._load_public_from_der

        if self._channel_option[self.TX_CERT_USE]:
            self._tx_verifier_load_function = PublicVerifier._load_cert_from_der
        else:
            self._tx_verifier_load_function = PublicVerifier._load_public_from_der

    def load_public_for_tx_verify(self, public):
        """load public for tx signature verify

        :param public: der format public key or der format cert
        :return:
        """
        self._tx_verifier_load_function(self, public)

    def load_public_for_peer_verify(self, public):
        """load public for peer signature verify

        :param public: der format public key or der format cert
        :return:
        """
        self._consensus_verifier_load_function(self, public)

    @property
    def public_der(self):
        if self._public_der is None:
            self._public_der = self._public_key.public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        return self._public_der

    @property
    def cert_der(self):
        if self._cert_der is None:
            self._cert_der = self._cert.public_bytes(
                encoding=serialization.Encoding.DER
            )
        return self._cert_der

    @property
    def tx_cert(self):
        if self._channel_option[self.TX_CERT_USE]:
            return self.cert_der
        return self.public_der

    @property
    def peer_cert(self):
        if self._channel_option[self.TX_CERT_USE]:
            return self.cert_der
        return self.public_der

    def _load_public_from_der(self, public_der: bytes):
        """load public key using der format public key

        :param public_der: der format public key
        :raise ValueError: public_der format is wrong
        """
        self._public_key = serialization.load_der_public_key(
            public_der,
            backend=default_backend()
        )

    def _load_public_from_object(self, public: EllipticCurvePublicKey):
        """load public key using public object

        :param public: der format public key
        :raise ValueError: public type is not EllipticCurvePublicKey
        """
        if isinstance(public, EllipticCurvePublicKey):
            self._public_key = public
        else:
            raise ValueError("public must EllipticCurvePublicKey Object")

    def _load_public_from_pem(self, public_pem: bytes):
        """load public key using pem format public key

        :param public_pem: der format public key
        :raise ValueError: public_der format is wrong
        """
        self._public_key = serialization.load_pem_public_key(
            public_pem,
            backend=default_backend()
        )

    def _load_cert_from_der(self, cert_der):
        cert: Certificate = x509.load_der_x509_certificate(cert_der, default_backend())
        self._cert = cert
        self._public_key = cert.public_key()

    def _load_cert_from_pem(self, cert_pem):
        cert: Certificate = x509.load_pem_x509_certificate(cert_pem, default_backend())
        self._cert = cert
        self._public_key = cert.public_key()

    def verify_data(self, data, signature) -> bool:
        """개인키로 서명한 데이터 검증

        :param data: 서명 대상 원문
        :param signature: 서명 데이터
        :return: 서명 검증 결과(True/False)
        """
        pub_key = self._public_key
        return self.verify_data_with_publickey(public_key=pub_key, data=data, signature=signature)

    def verify_hash(self, digest, signature) -> bool:
        """개인키로 서명한 해시 검증

        :param digest: 서명 대상 해시
        :param signature: 서명 데이터
        :return: 서명 검증 결과(True/False)
        """
        # if hex string
        if isinstance(digest, str):
            try:
                digest = binascii.unhexlify(digest)
            except Exception as e:
                logging.warning(f"verify hash must hex or bytes {e}")
                return False

        return self.verify_data_with_publickey(public_key=self._public_key,
                                               data=digest,
                                               signature=signature,
                                               is_hash=True)

    @staticmethod
    def verify_data_with_publickey(public_key, data: bytes, signature: bytes, is_hash: bool=False) -> bool:
        """서명한 DATA 검증

        :param public_key: 검증용 공개키
        :param data: 서명 대상 원문
        :param signature: 서명 데이터
        :param is_hash: 사전 hashed 여부(True/False
        :return: 서명 검증 결과(True/False)
        """
        hash_algorithm = hashes.SHA256()
        if is_hash:
            hash_algorithm = utils.Prehashed(hash_algorithm)

        if isinstance(public_key, ec.EllipticCurvePublicKeyWithSerialization):
            try:
                public_key.verify(
                    signature=signature,
                    data=data,
                    signature_algorithm=ec.ECDSA(hash_algorithm)
                )
                return True
            except InvalidSignature:
                logging.debug("InvalidSignatureException_ECDSA")
        else:
            logging.debug("Invalid PublicKey Type : %s", type(public_key))

        return False

    @staticmethod
    def verify_data_with_publickey_rsa(public_key, data: bytes, signature: bytes, is_hash: bool=False) -> bool:
        """서명한 DATA 검증

        :param public_key: 검증용 공개키
        :param data: 서명 대상 원문
        :param signature: 서명 데이터
        :param is_hash: 사전 hashed 여부(True/False
        :return: 서명 검증 결과(True/False)
        """
        hash_algorithm = hashes.SHA256()
        if is_hash:
            hash_algorithm = utils.Prehashed(hash_algorithm)

        if isinstance(public_key, rsa.RSAPublicKeyWithSerialization):
            try:
                public_key.verify(
                    signature,
                    data,
                    padding.PKCS1v15(),
                    hash_algorithm
                )
                return True
            except InvalidSignature:
                logging.debug("InvalidSignatureException_RSA")
        else:
            logging.debug("Unknown PublicKey Type : %s", type(public_key))

        return False


class PublicVerifierContainer:
    """PublicVerifier Container for often usaged"""

    __public_verifier = {}

    # TODO Private BlockChain은 public key가 제한적이라 다 보관, 그러나 다른경우는 어떻게 해야할지 고민 필요
    # TODO 많이 쓰는 것만 남기는 로직을 추가하면 그 때 그떄 생성하는 것보다 더 느릴 수 있음

    @classmethod
    def get_public_verifier(cls, channel, serialized_public: bytes) -> PublicVerifier:
        try:
            channel_public_verifier_list = cls.__public_verifier[channel]
        except KeyError as e:
            cls.__public_verifier[channel] = {}
            return cls.__create_public_verifier(channel, serialized_public)
        else:
            try:
                return channel_public_verifier_list[serialized_public]
            except KeyError as e:
                return cls.__create_public_verifier(channel, serialized_public)

    @classmethod
    def __create_public_verifier(cls, channel, serialized_public: bytes) -> PublicVerifier:
        """create Public Verifier use serialized_public deserialize public key

        :param serialized_public: der public key
        :return: PublicVerifier
        """

        public_verifier = PublicVerifier(channel)
        public_verifier.load_public_for_tx_verify(serialized_public)
        cls.__public_verifier[channel][serialized_public] = public_verifier

        return public_verifier
