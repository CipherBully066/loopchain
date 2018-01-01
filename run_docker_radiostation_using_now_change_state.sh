#!/usr/bin/env bash

# dev image have only dependencies, you should volume LoopChain
echo "run loopchain path : ${PWD}"
docker run -it -v ${PWD}:/LoopChain -p 7102:7102 loop-dev:lastest bin/bash -c "cd /LoopChain; source init_kms_env.sh /LoopChain; python3 loopchain.py rs -d"
