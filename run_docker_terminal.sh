#!/usr/bin/env bash
echo "run loopchain path : ${PWD}"
docker run -it -v ${PWD}:/LoopChain loop-dev:lastest bin/bash