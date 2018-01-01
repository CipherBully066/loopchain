# LFT 구현

#### 구현 참고 자료
 * https://docs.google.com/presentation/d/1-MwNHEuzfHJk5gfDa3y93PikGGB_PPOAWMkrifi9NLA/edit#slide=id.g22f2c693ec_0_0
 * LTF 백서 
    - https://drive.google.com/file/d/0BwM9dwe3uTQeR3k2c2t3VW1ObEk/view

#### Consensus
 * tx broadcast
 	- tx 를 broadcast 한다.
 	- leader 가 아닌 peer 는 tx 를 저장하였다가 block add 시 저장된 tx 를 삭제한다.
 	
 	
 	- ? 저장한 tx 를 block 검증에 활용 하여야 하나
 	- ? timer....
 	
 * vote broadcast 

#### Leader 순회
 * peer_list 정보를 block 에 담기 (현재 구현은 RS 에서 받거나, DB에서 로드한다.)
 
     - peer_manager block 을 별도로 전송한다.
     - peer_manager block 은 최종 전체 peer list 를 가진다
     - peer_manager blcok 은 SCORE container 의 invoke 를 타지 않고 peer_service 에서 처리한다.
     - 기록을 blockcahin_db 에 한다.
     
 * next leader 는 block header 에 리더가 담아서 보낸다. <- vote 완료후 spinning (리더 자동 순회)
        
#### Leader Complain
 * Leader 의 응답지연 시
 * Leader 의 종료 또는 재시작시
 
 
#### Block Height Sync
 * 처음 참여하는 Peer (Block Height=0) 일때 (Peer 목록을 RS에서 받을 수 밖에 없다.)
 * 재시작하는 Peer (Block Height<Current) 일때 (자신의 Peer 목록이 현재 상태와 다를 수 있다.)

 
#### Peer Healthy Check
 * ????? 
 
#### vote
 * vote 에 signature 추가.


#### complain timeout 
 * 리더 : 전 라운드 리더는 자신이 block을 만든 시점 부터 timeout (일반 노드보다 길어야한다)
 * 일반 노드 : 자신이 마지막으로 vote를 한 시점 부터 timeout 
 * block이 broadcast 되면 timeout check 종료 

 1. Tx가 남아 있으나 리더가 Timeout 내에 block을 생성하지 않으면 리더를 교체하기 위해 leader complain vote를 Broadcasting 한다. (3f +1 = 전체 노드 수)
 2. 사전에 Peer List에 의해 선정된 다음 리더는 f + 1 이상의 동일한 leader complain vote와 block vote를 합해 2f+1 이상의 투표를 포함한 block을 생성한다. 
 이때 이전 라운드에 대한 2f+1 이상의 vote를 포함한다.
 3. 블록을 받은 각 노드들은 실패 투표와 이전 블록 block vote를 검증하여 해당 block에 대한 투표를 Broadcast하고 이전 라운드 블록을 자신의 블록체인에 추가한다. 
