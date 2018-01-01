# gRPC Connection 유실 문제

#### 문제 요약
 * (1) 일정시간 혹은 일정 강도 이상 로드를 받은 배포된(금투협) 루프체인 네트워크에서 gRPC broadcast 가 되지 않는 현상 있음
 * (2) 2017년 12월 5일 (LOOP-324) 구현에서 채널 재시작시 동일한 현상 발생
 * (3) stress test 도구로 테스트시 동일 현상 발생


#### 참고 자료
 * [1] Idle channels sometimes fails RPCs with UNAVAILABLE status
   ( https://github.com/grpc/grpc/issues/11043 )
 * [2] if no request for a long time, server died?
   ( https://github.com/grpc/grpc/issues/5468 )
 * [3] Keep Python gRPC Client Connection Truly Alive
   ( https://blog.jeffli.me/blog/2017/08/02/keep-python-grpc-client-connection-truly-alive/ )


#### 구현 및 확인
 * 채널 재시작으로 기존 현상(2) 확인
 * stub, channel 관련한 구현 수정 (참고 자료 [3])
 * 채널 재시작으로 기존 현상(2) 제거 확인
 * 문제 현상 (1), (3) 모두 확인


#### TODO
 * (done) 채널 재시작시 블록이 초기화 되는 현상 해결
 * (3) ./stress_test.py -c 10000 -d 60 -ipf ip_local.txt 로 테스트시
   Tx Broadcast 메시지만 출력하고 실제로는 전송되지 않는 문제 재현 됨
 * block_manager 에서 level_db 가 None 으로 설정되었을때 (채널 재시작시) 동작 무결성 확인
 * level_db init 에서 retry count 추가하는 로직 방지하기
