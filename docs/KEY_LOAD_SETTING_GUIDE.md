## KeyLoad 설정 방법
### Loopchain Key 구성요소
Loopchain에서는 보안 통신, 트랜잭션 서명등을 위하여 인증서와 키 옵션을 설정해 주어야한다.
Loopchain에서 사용하는 키는 다음과 같다.

* Channel 별 서명 키
    * ecdsa secp256k
    * X.509 인증서, Publickey

* Peer - Peer TLS/SSL용 인증서
    * RSA 2048bit 256 hash
    * X.509 인증서
    * 같은 채널 내의 Peer들은 같은 CA에서 발급한 인증서를 사용해야함

* Peer - Client TLS/SSL 인증서
    * RSA 2048bit 256 hash
    * X.509 인증서
    * 인증서 상호 검증

### Channel 별 서명 키 옵션 설정

Loopchain에서는 트랜잭션 생성 및 블록 생성시 각 Peer를 검증하기위하여 공개키 기반 암호화 알고리즘을 통해 인증 서명 사용.

이때 사용하는 알고리즘은 ecdsa secp256k를 사용하고 인증서 형태와 Publickey 형태를 지원.

Loopchain Peer는 키를 로드 하기 위해 공개키의 형태와(cert, publickey), 키세트 로드방식 키 위치등을 설정하여야 함.

json형태로 옵션을 설정해야하며 다음 예제는 키 옵션별로 세팅해야될 세팅을 설명.

    ex)
    * channel1 = key_file을 통해 load
    * channel2 = kms를 통해 load
    * channel3 = random table을 통해 키 생성

KMS_AGENT_PASSWORD는 -a 옵션을 통해 실행시 집어넣어야 함.

특수문자가 들어갈 경우 -a '{KMS_AGENT_PASSWORD}' 형태로 추가해야 함.

```json
{
    "KMS_AGENT_PASSWORD" : "{kms agent password}",
    "CHANNEL_OPTION" : {
        "channel1" : {
            "load_cert" : false // load할 인증서의 type 이 cert 면 true, publickey 면 false
            "consensus_cert_use" : false, // block 및 투표 서명에 사용할 공개키 타입 (true : cert false : publickey)
            "tx_cert_use" : false, // 트랜잭션 서명 및 검증에 사용할 공개키 타입 (true : cert false : publickey)

            "key_load_type": 0, //file_load
            "public_path" : "{public_key path}",
            "private_path" : "{private_key path}",
            "private_password" : "{private_key password}"
        },
        "channel2" : {
            // 현재 kms load 방식은 인증서 타입만 load 할 수 있음
            "load_cert" : true // load할 인증서의 type 이 cert 면 true, publickey 면 false
            "consensus_cert_use" : false, // block 및 투표 서명에 사용할 공개키 타입 (true : cert false : publickey)
            "tx_cert_use" : false, // 트랜잭션 서명 및 검증에 사용할 공개키 타입 (true : cert false : publickey)

            "key_load_type": 1, //kms load
            "key_id": "{load 할 Key id}"
        },
        // Random Table 방식 현재 사용 불가능
        "channel3": {
            // 현재 random table derivation 방식은 false만 동작(cert 생성 불가능)
            "load_cert" : false // load할 인증서의 type 이 cert 면 true, publickey 면 false
            // 현재 random table derivation 방식은 false만 동작(cert 생성 불가능)
            "consensus_cert_use" : false, // block 및 투표 서명에 사용할 공개키 타입 (true : cert false : publickey)
            // 현재 random table derivation 방식은 false만 동작(cert 생성 불가능)
            "tx_cert_use" : false, // 트랜잭션 서명 및 검증에 사용할 공개키 타입 (true : cert false : publickey)

            "key_load_type": 2, //random table load
            // first_seed + second_seed 데이터를 통해 Private key derivation
            "first_seed" : 50, // Random table을 이용해 key를 생성할때 사용합니다. table 50번째 데이터
            "second_seed" : 25 // Random table을 이용해 key를 생성할때 사용합니다. table 25번째 데이터
        }
    }
}

```

### Peer-Peer TLS/SSL 옵션
TODO : GRPC - TLS 설정 완료하면 설명 기입
Loopchain에서는 피어들간의 폐쇄 네트워크를 구성하기위해 TLS를 설정합니다.


### Peer-Client TLS/SSL 옵션