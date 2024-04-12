# KOSTYA -> Get player image (jpg)
import os
import time
import json
import base64
import csv


def generate_file_details(player_url):
    name_part = player_url.rsplit('/', 1)[-1]
    return f'../resources/data/parsed_players/{name_part}/',\
        f'../resources/data/parsed_players/{name_part}/' + name_part + ".json",\
        f'../resources/data/parsed_players/{name_part}/' + name_part + ".jpeg",\
        f'../resources/data/parsed_players/{name_part}/' + name_part + '_wiki' + ".jpeg"


class PlayerRepository:
    def exists(self, player_url):
        directory_filepath, data_filepath, *_ = generate_file_details(player_url)

        if os.path.exists(''.join(directory_filepath.split('/').pop())):
            modification_time = os.path.getmtime(data_filepath)
            current_time = time.time()
            one_hour_ago = current_time - (1 * 3600)

            if modification_time > one_hour_ago:
                return True
        return False

    # Refactor to return dictionary for named destructuring
    def get_player_data(self, player_url):
        directory_filepath, data_filepath, *_ = generate_file_details(player_url)

        if not os.path.exists(directory_filepath):
            return {}

        with open(data_filepath, 'r') as file:
            data = json.load(file)

        return data

    def write_dataset(self, header, data):
        resource_dir = '../resources/data'

        if not os.path.exists(resource_dir):
            os.makedirs(resource_dir)

        with open(resource_dir + '/players_data.csv', 'w', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)

            # write the header
            writer.writerow(header)

            # write multiple rows
            writer.writerows(data)

    def write_data(self, player_url, player_data, player_img_base64, elem):
        directory_filepath, data_filepath, img_data_filepath, elem_path = generate_file_details(player_url)

        if not os.path.exists(directory_filepath):
            os.makedirs(directory_filepath)

        with open(data_filepath, 'w+') as f:
            json.dump(player_data, f, indent=4)

        with open(img_data_filepath, "wb") as fh:
            fh.write(base64.decodebytes(player_img_base64.encode('utf-8')))

        if elem:
            with open(elem_path, "wb") as fh:
                fh.write(base64.decodebytes(elem.encode('utf-8')))

        return
