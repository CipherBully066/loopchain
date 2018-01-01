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
"""A management class for peer and channel list."""

from loopchain.blockchain import *


class AdminManager:
    """Radiostation 내에서 Channel 정보와 Peer 정보를 관리한다."""

    def __init__(self, level_db_identity):
        # self.__level_db = None
        # self.__level_db_path = ""
        # self.__level_db, self.__level_db_path = util.init_level_db(f"{level_db_identity}_admin")

        self.__json_data = None
        self.load_json_data(conf.CHANNEL_MANAGE_DATA_PATH)

    def load_json_data(self, channel_manage_data_path):
        """open channel_manage_data json file and load the data
        :param channel_manage_data_path:
        :return:
        """
        try:
            logging.debug(f"try to load channel management data from json file ({channel_manage_data_path})")
            with open(channel_manage_data_path) as file:
                json_data = json.load(file)
                json_string = json.dumps(json_data).replace('[local_ip]', util.get_private_ip())
                self.__json_data = json.loads(json_string)

                logging.info(f"loading channel info : {self.json_data}")
        except FileNotFoundError as e:
            util.exit_and_msg(f"cannot open json file in ({channel_manage_data_path}): {e}")

    @property
    def json_data(self) -> dict:
        return self.__json_data

    def get_channel_list(self) -> list:
        return list(self.json_data)

    def save_channel_manage_data(self, updated_data):
        with open(conf.CHANNEL_MANAGE_DATA_PATH, 'w') as f:
            json.dump(updated_data, f, indent=2)
        self.load_json_data(conf.CHANNEL_MANAGE_DATA_PATH)

    def get_all_channel_info(self) -> str:
        all_channel_info = json.dumps(self.json_data)
        return all_channel_info

    def get_score_package(self, channel):
        """load score packages in loopchain

        :return:
        """
        # TODO score packages를 로드한다.
        pass

    def get_channel_infos_by_peer_target(self, peer_target: str) -> str:
        """get channel infos (channel, score_package, and peer target) that includes certain peer target

        :param peer_target:
        :return: channel_infos
        """
        channel_list = []
        filtered_channel = {}
        loaded_data = self.json_data

        for key in loaded_data.keys():
            target_list = loaded_data[key]["peers"]
            for each_target in target_list:
                if peer_target == each_target["peer_target"]:
                    channel_list.append(key)
        for each_channel in channel_list:
            filtered_channel[each_channel] = loaded_data[each_channel]
        channel_infos = json.dumps(filtered_channel)

        return channel_infos

    def get_peer_list_by_channel(self, channel: str) -> list:
        """get peer list by channel

        :param channel:
        :return:
        """
        loaded_data = self.json_data
        peer_list = []
        peer_infos = loaded_data[channel]["peers"]
        for each in peer_infos:
            peer_list.append(each['peer_target'])
        return peer_list

    def add_channel(self, loaded_data, new_channel, score_package_input):
        loaded_data[new_channel] = {"score_package": score_package_input, "peers": []}
        logging.info(f"Added channel({new_channel}), Current multichannel configuration is: {loaded_data}")
        self.save_channel_manage_data(loaded_data)

    def add_peer_target(self, loaded_data, channel_list, new_peer_target, peer_target_list, i):
        if new_peer_target not in [dict_data['peer_target'] for dict_data in peer_target_list]:
            peer_target_list.append({'peer_target': new_peer_target})
            logging.debug(f"Added peer({new_peer_target}), Current multichannel configuration is: {loaded_data}")
        else:
            logging.warning(f"peer_target: {new_peer_target} is already in channel: {channel_list[i]}")
        return loaded_data

    def delete_channel(self, loaded_data, channel_list, i):
        remove_channel = channel_list[i]
        del loaded_data[channel_list[i]]
        logging.info(f"Deleted channel({remove_channel}), Current multichannel configuration is: {loaded_data}")
        return loaded_data

    def delete_peer_target(self, loaded_data, remove_peer_target, filtered_list, i):
        for peer_target in loaded_data[filtered_list[i]]["peers"]:
            if remove_peer_target in peer_target["peer_target"]:
                loaded_data[filtered_list[i]]["peers"].remove(peer_target)
                logging.debug(f"Deleted peer({remove_peer_target}), Current multichannel configuration is: {loaded_data}")
        return loaded_data
