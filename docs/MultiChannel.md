# Multi Channel 구현

#### 구현 범위
 * proto
 * consensus
 * block chain
 * peer_manager


#### RadioStation
 * channel_manager
  - 어떤 peer 가 허가 받았는지, 어떤 peer 가 어떤 채널에 대한 권한이 있는지 기록한 데이터
  - peer 가 어떤 channel 에 속하는지 관리한다.
  - 이중화된 rs 와 공유한다.
  
 * 기존 ConnectPeer 로직을 유지하기 위해 사용하려는 channel 별로 ConnectPeer 로 로그인 하여야 한다.
  - 응답에 channels 정보가 추가된다.
  - peer 는 최초 default channel 에 접속하게 되며
  - 이때 ConnectPeerReply 값으로 channels 정보를 받게 된다.
  - default channel 외에 사용할 channel 별로 다시 ConnectPeer 를 요청하면 channel 별로 블록 네트워크에 참여하게 된다.

 * Peer 에서는 Block Manager 가 채널별로 생성되어야 한다.


#### TODO