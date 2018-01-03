#!/usr/bin/env bash

# dev image have only dependencies, you should volume LoopChain
if [[ $# -eq 0 ]]; then
    echo "You Must Put Peer Port"
    exit -1
fi
Port=$1
echo "run loopchain path : ${PWD}"
docker run -it -v ${PWD}:/LoopChain -p ${Port}:${Port} loop-dev:lastest bin/bash -c "cd /LoopChain; source init_kms_env.sh /LoopChain; python3 loopchain.py peer -d  -r 10.130.129.130:7102 -p ${Port}"
