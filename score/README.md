# Loopchain SCORE 개발가이드

## Loopchain Score 란
* Loopchain의 스마트 컨트렉트를 통칭합니다.
* 각 피어에서 독립적으로 실행되며, Block 이 확정되는 시점에서 실행됩니다.
* Block별로 실행하며, 블록체인으로 구성하는 비지니스로직을 구현한다.
* Python 언어로 개발되며, Loopchain의 dependency 를 따릅니다.

## SCORE 개발
스코어의 개발은 3단계로 나뉠수 있습니다.
1. 비지니스 모델 타당성 검증
2. 모델 구현 및 유닛테스트
3. 인티그레이션 테스트 및 모델 배포

### 1. 비지니스 모델 타당성 검증
 스코어 안에서는 다음과 같은 내용을 통한 비지니스는 불가합니다.

#### 1. 랜덤값에 의존하는 비지니스 모델
 스코어 안에서 랜덤값을 생성하거나, 실행하는 모델은 불가하나, 블록의 해쉬 혹은 트랜잭션을 이용한 랜덤값 이용은 가능합니다.
#### 2. 외부의 데이터에 의존성이 있는 비지니스 모델
 스코어 안에서 다른 사이트를 호출하거나, 외부의 데이터를 요구하는 모델은 아직 불가능하나 향후 고려되고 있습니다.
#### 3. 시간에 따라 행동하는 혹은 실행시간에 따라 내용이 바뀌는 모델
 **현재 시간(실행시간)은 사용 불가능**하며, 블록의 시간 혹은 트랜잭션 시간으로 대체는 가능합니다.

### 폴더 및 실행구조
  * / score / 회사명(기관명) / 패키지명
  > ex) /score/loopchain/default/
  * __`deploy` 폴더명은 사용 불가__
  * 원격 리파지토리를 사용하지 않을 경우 다음과 같이 가능합니다.
    - `회사명(기관명)_패키지명.zip` 으로 리파지토리 전체를 압축하여 score에 저장하여 실행
  * 패키지 설명 및 실행에 대한 상세내용은 `package.json` 파일로 정의 하며, `package.json` 정의에 대한 내용은 [다른 가이드에서 설명합니다.](PACKAGE_GUIDE.md)

## 2. SCORE 테스트
* 스코어를 작성하거나, 개발할때는 **coverage 90%** 이상을 목표로 개발 하여야 하며, 퍼포먼스도 고려되어야 합니다.
* 모든 테스트 코드는 스코어의 패키지 루트에 있어야 하며, 차후 리파지토리 등록전에 실행됩니다.

### SCORE의 테스트 방법
```
# TEST 실행은 loopchain root 폴더에서 실행
$>python3 -m unittest score/회사명(기관명)/패키지명/테스트파일
ex)
$>python3 -m unittest score/theloop/chain_message_score/test_chain_message.py
```
__IDE에서 테스트시 Working Directory 를 Loopchain root로 설정하여 테스트 바랍니다.__

## 3. SCORE 배포 및 관리

### <1> local develop folder 를 사용하는 방법
* configure_user.py 파일을 추가합니다. (configure_default.py 와 같은 위치)
```
ALLOW_LOAD_SCORE_IN_DEVELOP = 'allow'
DEVELOP_SCORE_PACKAGE_ROOT = 'develop'
DEFAULT_SCORE_PACKAGE = 'develop/[package]'
```
* /score/develop/[package] 폴더를 만듭니다 [package] 는 원하는 이름으로 작성합니다. (sample 을 사용하는 경우 test_score 로 합니다.)
* /score/sample-test_score/* 파일을 새로운 폴더로 복사합니다.
* loopchain 네트워크를 실행하여 확인합니다.

### <2> zip 파일을 사용하는 방법

#### a) 임의의 폴더를 만들고 그 안에서 새롭게 SCORE를 작성한 경우 (From scratch) ####
* 임의의 폴더에서 score 를 작성합니다. (<1> 에서 작성한 SCORE 복사하여도 됩니다.)
* package.json 의 ```id``` 값을 "[company_name]-[package]" 로 수정합니다. 이 id값대로 repository를 만들고 압축파일을 만들것입니다.
* ```$ git init . ```으로 해당 폴더를 local git repository 로 설정합니다.
* ```$ git add . ``` 으로 폴더의 모든 파일을 repository 에 추가 합니다.
* ```$ git commit -a -m 'initialized commit' ``` 로 SCORE 파일들을 git 에 commit 합니다.
* ```$ zip -r ../${id}.zip ./ ```으로 repository 를 zip 으로 압축합니다. ```[company_name]-[package].zip```이라고 상위 폴더에 생성될 것입니다.


#### b) 기존에 Git repository에서 SCORE를 만들고 가지고 있는 경우 ####
* ``` $ git clone %{SCORE_REPOSITORY_URL}```로 SCORE project를 가져옵니다. 
* ``` $ cd %SCORE_FOLDER% ```로 해당 SCORE project folder로 이동합니다. 
* ``` $ git remote remove origin ``` 으로 기존의 origin등 remote repository설정을 없앱니다.
* package.json 의 ```id``` 값을 확인합니다. "[company_name]-[package]" 로 수정합니다. 이 id값대로 repository를 만들고 압축파일을 만들것입니다.
* ```$ zip -r ../${id}.zip ./ ```으로 repository 를 zip 으로 압축합니다. ```[company_name]-[package].zip```이라고 상위 폴더에 생성될 것입니다.
* zip 파일을 ```${CURRENT_LOOPCHAIN_FOLDER}/score/``` 아래에 둡니다.
   예) ```${CURRENT_LOOPCHAIN_FOLDER}/score/[company_name]-[package].zip```)


### <3> repository 를 사용하는 방법
* SCORE의 배포는 특별히 관리되는 repository 를 사용할 수 있습니다.
  - 차후 다수의 repository 를 검색하여, 순위별로 배포하는 방안도 검토 중입니다.
* remote repository 에서 관리하지 않는 스코어는 내부 repository가 포함된 zip 파일에서 관리 할 수 있습니다.

### <4> SCORE를 Blockchan network상에서 사용하는 방법
* 앞서 있는 [README.md](../README_KR.md)에 있는 multichannel을 참조 바랍니다. 

