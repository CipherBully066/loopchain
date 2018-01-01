# certificate_tool
Loopchain에서 사용하는 인증서를 생성해주는 툴입니다.

## 주요기능
* 서명용 인증서 발급용 CA 인증서 발급
* 서명용 CA 발급 인증서 발급
* 서명용 Self Signed 인증서 발급

## 예정된 기능
* TLS 인증서 발급용 CA 인증서 생성
* TLS 인증서 생성

## WARNIGN: 주의 사항
* **이미 인증서가 만들어진 폴더에서는 CA인증서 생성기능을 통해 인증서를 발급하면 안됩니다.**
    * CA를 여러개 만들경우 이전에 만든 CA가 삭제 될 수 있습니다.
* **CA 인증서와 Self Signed 인증서는 다른폴더에서 생성하여야 합니다.**
    * CA를 통해 발급하는 인증서와 Self Signed 인증서의 Serial Number 발급 방식의 차이점이 있습니다.

## Dependencies
* Python3.5 이상

## 툴 사용 환경 설정
1. certificate_tool 폴더로 이동
2. python 가상환경 설정  [link](https://tutorial.djangogirls.org/ko/django_installation/) (가상환경)
3. pip3 install -r requirements.txt를 통해 Dependency 설치

## CA 발급 인증서 발급
1. certificate_tool 폴더로 이동
2. python 가상환경 실행
3. ./certificate_util.py 를 통해 tool 실행
4. Change CA Based Cert Path 옵션을 통해 인증서 생성 위치 설정
    * Self Signed 인증서와 위치가 같으면 안됨 - 인증서의 SerialNumber가 섞임
5. CA 인증서 생성 (1번) (cn, ou, o, 유효기간 설정)
    * COUNTRY_NAME은 kr로 고정
    * {인증서생성위치}/CA 에 CA 인증서 생성
6. 발급 종료

## Self Signed Peer 인증서 발급
1. certificate_tool 폴더로 이동
2. python 가상환경 실행
3. ./certificate_util.py 를 통해 tool 실행
4. Change Self Signed Cert Path 옵션을 통해 인증서 생성 위치 설정
    * CA 발급 인증서와 위치가 같으면 안됨 - 인증서의 SerialNumber가 섞임
5. Self Signed 인증서 생성(5번) (cn, ou, o, 유효기간 설정)
    * COUNTRY_NAME은 kr로 고정
    * {인증서생성위치}/cn 에 Self Signed 인증서 생성
6. 5를 반복하여 필요한 만큼 인증서 발급
7. 발급 종료

## CA 발급 Peer 인증서 발급
1. certificate_tool 폴더로 이동
2. python 가상환경 실행
3. ./certificate_util.py 를 통해 tool 실행
4. Change CA Based Cert Path 옵션을 통해 인증서 생성 위치 설정
    * 사전에 CA 인증서가 생성된 폴더로 설정하여야 함.
5. 생성한 CA 인증서로 인증서 생성 (cn, 유효기간 설정)
    * {인증서생성위치}/cn 에 Peer 인증서 생성
6. 5를 반복하여 필요한 만큼의 인증서 발급
7. 발급 종료

## 인증서 생성 위치
* CA 인증서는 파일생성위치/CA 폴더에 저장
* 개인 인증서는 생성시 지정한 CN이름에 따라 파일생성위치/CN이름 폴더에 저장
