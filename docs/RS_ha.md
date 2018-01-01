# Radio Station high availabillity (이중화)

#### 구조
 * Active-Standby
 * Stanby 일때는 Outer 서비스 중단
 * Stanby 로 시작 다른 RS 가 살아 있지 않으면 Active 로 전환
 * Stanby 일때는 다른 RS 가 살아 있는지 heartbeat
 * Master(high priority) 가 살아 나면 Slave(low priority)는 Active 에서 Stanby 로 전환.


#### TODO
 * (done) rs_service 에서 outer service 와 inner service (admin service) 둘다 띄우기
 * (done) gtool 로 admin servcie 접속하기
 * RS 가 재시작 되었을때 Peer 와 연결 오류 발생하는 문제 해결하기
 * Standby 옵션으로 start 하기
 * Standby mode 일때 다른 rs 로 heartbeat 하기
 * 다른 rs 가 응답 없을시 Active mode 로 전환하기
 * peer 는 configure 를 통해서 두개의 RS 주소 얻기 (IP:port 는 L4 로 해결하나?, 이 경우도 우선 두개의 RS 를 처리할 수 있는 기능은 구현)
 * 현재 RS 장애시 Standby RS 로 대체 되는지 확인하기
 