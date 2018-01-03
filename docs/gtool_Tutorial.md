Tutorial for gtool
==================

## 소개
gtool은 **loopchain Radiostation Admin용 command line 관리툴**입니다.
gtool을 통해서 채널과 각 채널에 대한 score package, peer target에 대한 데이터를 관리할 수 있고 특정 채널을 재시작할 수 있습니다.


## Index
1. [시작하기](#시작하기)
2. [channel manage data 가져오기](#channel-manage-data-가져오기)
3. [peer를 추가 / 삭제하기](#peer-추가-혹은-삭제하기)
4. [channel을 추가 / 삭제하기](#channel-추가-혹은-삭제하기)
5. [수정된 channel manage data를 Radiostation으로 전송](#수정된-channel-manage-data를-Radiostation으로-전송)
6. [채널 재시작](#채널-재시작)

## 시작하기
다음 명령을 통해 gtool을 실행합니다. 메인 메뉴 화면은 다음과 같습니다.
```buildoutcfg
$ python3.6 gtool.py
...
TheLoop LoopChain Admin Command Tools

Choose menu number you want
---------------------
1. Connect to Radiostation Admin service
2. Get Radiostation Admin status
3. Get all channel manage data
4. Add peer
5. Add channel
6. Delete peer
7. Delete channel
8. Dump current data to json
9. Send channel manage info to Radiostation
10. Restart channel
0. Quit
```

## channel manage data 가져오기

channel manage data란 RS Admin 데이터를 json 형태로 저장한 파일로, **채널 정보와 각 채널에 대한 score, peer 정보**를 담고 있습니다.
만약 특정 채널에 대한 peer target, score 정보 등을 변경하고 싶다면, gtool을 실행하여 모든 channel manage data를 직접 관리할 수 있습니다. 

> channel manage data 작성 방법, 데이터 형식, 저장위치 등에 대한 설명은 [여기](../README_KR.md#multichannel)를 참고하시면 됩니다.

> 사용자 지정 환경변수를 저장한 configure.json파일의 경로 설정은 다음과 같이 -o 옵션으로 추가하실 수 있습니다.

```
$ python3.6 gtool.py -o "/loopchain/configure.json"
```

메인 메뉴에서 3번을 선택하여 현재 channel manage data를 가져오는 메뉴를 실행해봅시다.
```buildoutcfg
$ python3.6 gtool.py
 >> 3
 
Get all channel manage data
{
 "channel1": {
     "score_package": "loopchain/default",
     "peers": [
         {
             "peer_target": "1.1.1.1:1111"
         },
         {
             "peer_target": "2.2.2.2:2222"
         },
         {
             "peer_target": "3.3.3.3:3333"
         }
     ]
 },
 "channel2": {
     "score_package": "loopchain/default",
     "peers": [
         {
             "peer_target": "1.1.1.1:1111"
         },
         {
             "peer_target": "2.2.2.2:2222"
         },
         {
             "peer_target": "3.3.3.3:3333"
         }
     ]
 }
}
0.back
```

## peer 추가 혹은 삭제하기

### 1. peer 추가

먼저, 메인 메뉴 4번인 "Add peer"를 선택하여 추가하고 싶은 peer의 IP 주소와 PORT 번호를 형식에 맞게 입력합니다. 
예시로는 '9.9.9.9:9999'를 추가해보겠습니다.
    
```buildoutcfg
$ python3.6 gtool.py
 >> 4
Add peer
Enter the peer target in the following format:
[IP of peer]:[port]
 >> 9.9.9.9:9999
 
Do you want to add a new peer to channel: channel1? Y/n (Enter: Y)
 >> Y
     
Do you want to add a new peer to channel: channel2? Y/n (Enter: Y)
 >> Y

Added peer(9.9.9.9:9999), Current multichannel configuration is: {'channel1': {'score_package': 'loopchain/default', 'peers': [{'peer_target': '1.1.1.1:1111'}, {'peer_target': '2.2.2.2:2222'}, {'peer_target': '3.3.3.3:3333'}, {'peer_target': '9.9.9.9:9999'}]}, 
'channel2': {'score_package': 'loopchain/default', 'peers': [{'peer_target': '1.1.1.1:1111'}, {'peer_target': '2.2.2.2:2222'}, {'peer_target': '3.3.3.3:3333'}, {'peer_target': '9.9.9.9:9999'}]}}
```

peer target 정보를 입력하면, 위와 같이 채널마다 해당 peer target을 추가할지 여부를 묻습니다. 추가하고 싶은 채널은 Enter 혹은 'Y'를, 
skip하고 싶은 채널은 'n'을 입력하면 됩니다.

### 2. peer 삭제
    
메인 메뉴 화면으로 돌아가 6번인 "Delete peer"를 선택하여 삭제하고 싶은 peer의 IP 주소와 PORT 번호를 형식에 맞게 입력합니다.
    
```buildoutcfg
$ python3.6 gtool.py
 >> 6
Delete peer
Enter the peer target in the following format:
[IP of peer]:[port]
 >> 9.9.9.9:9999
 
Here is the channel list that peer(9.9.9.9:9999) is included:
['channel1, 'channel2']
 >> new_channel
     
Do you want to delete peer(9.9.9.9:9999) in channel: channel1? Y/n (Enter: Y)
 >> Y

         
Do you want to delete peer(9.9.9.9:9999) in channel: channel2? Y/n (Enter: Y)
 >> Y
Deleted peer(9.9.9.9:9999), Current multichannel configuration is:: {'channel1': {'score_package': 'loopchain/default', 'peers': [{'peer_target': '1.1.1.1:1111'}, {'peer_target': '2.2.2.2:2222'}, {'peer_target': '3.3.3.3:3333'}]}, 
'channel2': {'score_package': 'loopchain/default', 'peers': [{'peer_target': '1.1.1.1:1111'}, {'peer_target': '2.2.2.2:2222'}, {'peer_target': '3.3.3.3:3333'}]}}
```

마찬가지로, 해당 peer target이 속해 있는 채널마다 삭제할 지 여부를 묻습니다. 삭제하고 싶은 채널은 Enter 혹은 'Y'를, 
skip하고 싶은 채널은 'n'을 입력합니다. 
    
    
## channel 추가 혹은 삭제하기

한 채널을 추가하기 위해서는 **채널명, 해당 채널이 사용할 score package** 정보가 필요합니다. 
(새로운 채널에 peer target을 추가하는 것은 [peer를 추가 / 삭제하기](#peer-추가-혹은-삭제하기)를 이용하시면 됩니다.)

### 1. channel 추가

메인 메뉴 화면에서 5번인 "Add channel"을 선택하여 새로 추가할 채널명을 입력합니다. 
예시로는 채널명을 `new_channel`, score는 `loopchain/default`로 지정해주겠습니다.
```buildoutcfg
$ python3.6 gtool.py
 >> 5
Add channel
Enter the new channel name:
 >> new_channel
 
Please enter the name of score_package:
 >> loopchain/default
     
Added channel2, Current multichannel configuration is: {'channel1': {'score_package': 'loopchain/default', 'peers': [{'peer_target': '1.1.1.1:1111'}, {'peer_target': '2.2.2.2:2222'}, {'peer_target': '3.3.3.3:3333'}]}, 
'channel2': {'score_package': 'loopchain/default', 'peers': [{'peer_target': '1.1.1.1:1111'}, {'peer_target': '2.2.2.2:2222'}, {'peer_target': '3.3.3.3:3333'}]}, 
'new_channel': {'score_package': 'loopchain/default', 'peers': []}}
```
입력이 완료되면 위와 같이 변동된 channel manage data 결과를 확인할 수 있습니다.

### 2. channel 삭제
    
한 채널을 삭제할 경우, 해당 채널에 속한 score package 정보와 모든 peer target 정보가 같이 삭제됩니다.

메인 메뉴에서 7번인 "Delete channel"을 선택합니다. 
```buildoutcfg
$ python3.6 gtool.py
 >> 7
Delete channel
Here is the all channel list:
 ['channel1', 'channel2', 'new_channel']
 
If you delete a channel, all peers in that channel will be removed.
Are you sure to proceed?  Y/n (Enter: Y)
 >> Y

Do you want to delete the channel(channel1) and all of its peers? Y/n
...
```
각 채널마다 삭제할 지 여부를 묻습니다. 삭제하고 싶은 채널은 Enter 혹은 'Y'를, skip하고 싶은 채널은 'n'을 입력합니다.

## 수정된 channel manage data를 Radiostation으로 전송

gtool에 의해 수정된 channel manage data를 현재 띄워져 있는 Radiostation에 바로 전송할 수 있습니다. 

### 1. Radiostation Admin service에 접속
    
메인 메뉴에서 1번인 "Connect to RS admin service"를 선택하고, Radiostation의 IP와 PORT를 형식에 맞게 입력합니다.
local PC에서 올렸을 경우 Enter를 누르면 바로 접속할 수 있습니다.

```buildoutcfg
$ python3.6 gtool.py
 >> 1

Connect to Radiostation admin service
Enter the Radiostation target in the following format:
[IP of Radiostation]:[port] (default '' -> 127.0.0.1:17102, [port] -> 127.0.0.1:[port])
 >> 
```

Radiostation을 띄운 terminal에 다음과 같은 로그가 나타난다면, gtool이 Radiostation에 정상적으로 접속이 된 것입니다.

```buildoutcfg
[TIMESTAMP] [PROCESS_ID] radiostation SPAM rs_admin_service:__handler_status (connect from gtool)
```

### 2. Radiostation으로 channel manage data 전송
    
메인 메뉴로 돌아가 9번인 "Send channel manage info to Radiostation"를 선택합니다.

```buildoutcfg
$ python3.6 gtool.py
 >> 9

Send channel manage info to RS
response: code: 0
```
위와 같은 화면이 뜬다면 정상적으로 channel manage data가 전송이 된 것입니다.

## 채널 재시작

특정 채널을 재시작하고 싶을 경우, gtool을 통해 다른 채널에 영향을 주지 않고 재시작할 수 있습니다. 

### 1. Radiostation admin service에 접속
    
메인 메뉴에서 1번인 "Connect to RS admin service"를 선택하고, Radiostation의 IP와 PORT를 형식에 맞게 입력합니다.
local PC에서 올렸을 경우 Enter를 누르면 바로 접속할 수 있습니다.

```buildoutcfg
$ python3.6 gtool.py
 >> 1

Connect to Radiostation admin service
Enter the Radiostation target in the following format:
[IP of Radiostation]:[port] (default '' -> 127.0.0.1:17102, [port] -> 127.0.0.1:[port])
 >> 
```

Radiostation을 띄운 terminal에 다음과 같은 로그가 나타난다면, gtool이 Radiostation에 정상적으로 접속이 된 것입니다.

```buildoutcfg
[TIMESTAMP] [PROCESS_ID] radiostation SPAM rs_admin_service:__handler_status (connect from gtool)
```
    
### 2. Restart channel

메인 메뉴에서 10번인 "Restart channel"을 선택하여 재시작할 채널 번호를 입력합니다.
```buildoutcfg
$ python3.6 gtool.py
 >>  10

Restart peer by channel
Choose channel number for restart
0: channel1
1: channel2
 >>
```

채널이 정상적으로 재시작이 되었는지 확인하는 기능을 gtool에 추가할 예정입니다. 현재로서는 각 peer의 로그를 보며 확인하실 수 있습니다.
    