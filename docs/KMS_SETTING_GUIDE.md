## KMS 사용환경
* Linux 기반 서버

## 인증서 주입
* certificate_tool을 이용하여 인증서 생성
* 윈도우 머신에서 관리도구를 통하여 주입

## KMS 라이브러리 설정시 고려 사항

* KMS Library 파일
    * **모든 Peer가 같은 Library를 공유**

* Agent 인증서
    * **피어 별로 다른 Agent 인증서를 사용**
        * 서로 다른 Peer가 같은 Agent 인증서를 사용할 경우, 다른 Peer의 인증서에 접근할 수 있음.
    * **관리도구를 이용하여 생성 및 주입**

* 설정 파일 (sgkms_pkcs11.ini)
    * **KMS Library 파일과 같은 위치에 있어야 함**
    * **Peer 별로 내용이 상이**


### KMS 연동을 위한 시스템 구성요소
* KMS Library 파일
    * **모든 Peer가 같은 Library를 공유**
    * 구성요소
        * libcis_cc-3.2.so
        * libcis_ce-3.2.so
        * libsgkms_cryptoki.so

* Agent 인증서
    * **피어 별로 다른 Agent 인증서를 사용**
        * 서로 다른 Peer가 같은 Agent 인증서를 사용할 경우, 다른 Peer의 인증서에 접근할 수 있음.
    * **관리도구를 이용하여 생성 및 주입**
    * 구성요소
        * SITE 인증서
        * CERT 인증서
        * 인증서 키파일
        * SPIN

* 설정 파일 작성법 (sgkms_pkcs11.ini)
    * **KMS Library 파일과 같은 위치에 있어야 함**
    * **Peer 별로 내용이 상이**
```
#scpdb_agent.ini
[SERVER]
ServerIP={kms1 ip ex:111.222.333.4}
ServerPort=2525
[SERVER2]
ServerIP={kms2 ip ex:111.222.333.4}
ServerPort=2525
[TIMEOUT]
ConnectTimeout=2
SendTimeout=10
RecvTimeout=10
[AGENT]
AgentID={관리도구를 이용해 생성한 AGENT의 이름}
AgentIP={접속하는 AGENT(PEER)의 IP  ex:111.222.333.4}
LogDir=
#LogLevel=0.NO / 2.LEVEL2_ALERT / 4.LEVEL4_ERROR / 6.LEVEL6_NOTICE / 8.LEVEL8_DEBUG
LogLevel=0
CacheMax=0
SiteCertFilePath={Site 인증서 위치 절대경로 ex:/damo-site_KOF-KOF-TEST.cer}
CertFilePath={Cert 인증서 위치 절대경로 ex : /damo-scp_KOF-TEST-VAGRANT.cer}
KeyFilePath={인증서 Key 위치 절대경로 ex : /damo-scp_KOF-TEST-VAGRANT.key}
SPIN={Agent 인증서의 SPIN 데이터를 붙여 넣는다 ex : WtQilki46Lvr0G/lvF8FwvEK}
```

### 연동시 고려 사항
* KMS Library 파일과 설정파일은 같은 위치에 있어야 함
* 환경변수 KMS_LIB_PATH를 만들어 KMS Library 폴더 위치를 명시하고 LD_LIBRARY_PATH에 추가해야 함
```
export KMS_LIB_PATH={LoopChainPath}/resources/kms/kms_libs
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$KMS_LIB_PATH
```
* KMS 서버의 시간대와 Agent(Peer)의 시간대가 같아야 함


