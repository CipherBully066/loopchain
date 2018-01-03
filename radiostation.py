#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2017 theloop Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from loopchain import launcher


if __name__ == "__main__":
    print(f"=====================================================================================")
    print(f"=====================================================================================")
    print(f"=====================================================================================")
    print(f"WARNING!!! This file will be removed later. ")
    print(f"When you launch radiostation, you should launch radiostation in the following format:")
    print(f"./loopchain.py rs [-d] [-o CONFIGURE_FILE_PATH]")
    print(f"=====================================================================================")
    print(f"=====================================================================================")
    print(f"=====================================================================================")
    launch_argv = ["radiostation"] + sys.argv[1:]
    launcher.main(launch_argv)
