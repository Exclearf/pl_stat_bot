import csv
import re
import sys
from os import path
from unidecode import unidecode
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from src.webScraper.scraper import *
from src.repository.players_repository import *


class DataAnalyzer:
    def __init__(self):
        self.csv_file_path = "../../resources/data/players_data.csv"

    def search_players(self, partial_name):
        found_players = []
        #{} - partial_name, r - substring match, format - insert in {}
        name_pattern = re.compile(r'{}'.format(partial_name), re.IGNORECASE)
        # open in read 'r' mode, using utf8
        with open(self.csv_file_path, 'r', encoding='UTF8') as csvfile:
            #CSV reader obj, column headers for iteration
            csv_reader = csv.DictReader(csvfile)
            #array of arrays, smaller array - [name, url] of every matched player
            for row in csv_reader:
                row['name'] = unidecode(row['name'])
                if name_pattern.search(row['name']):
                    found_players.append([row['name'], row['url']])

        if not found_players:
            return ({'name': 'No players found matching the provided partial name.', 'url': ''})

        return found_players


    #name -> path for easier movements
    def player_path(self, player_name):
        changed_player_name = player_name.replace(' ', '-')
        path = '../../resources/data/parsed_players/' + changed_player_name + '/' + changed_player_name
        return path

    #Get data from json created by scraper
    def get_player_data(self, player_name):
        path = DataAnalyzer().player_path(player_name) + '.json'
        with open(path, 'r', encoding='UTF8') as file:
            data = json.load(file)
            return data


    def player_graph_attack(self, player_data):
        seasons = []
        goals_scored = []
        assists_made = []
        exp_goals = []
        exp_assists = []
        for season, stats in player_data["all_stats_standard"].items():
            seasons.append(season)
            goals_scored.append(int(stats["goals"]))
            assists_made.append(int(stats["assists"]))
            performance = stats.get("performance", {})
            expected_goals_str = performance.get("expectedGoals", "0")
            expected_assists_str = performance.get("expectedAssists", "0")
            exp_goals.append(float(expected_goals_str) if expected_goals_str else 0.0)
            exp_assists.append(float(expected_assists_str) if expected_assists_str else 0.0)

        start_index = seasons.index('2017-2018')

        plt.figure(figsize=(10, 6))
        plt.plot(seasons, goals_scored, linewidth=5, color='red', linestyle='-', label='Goals Scored')
        plt.plot(seasons, assists_made, linewidth=5, color='green', linestyle='-', label='Assists Made')
        plt.plot(seasons, exp_goals, linewidth=5, alpha=0.3,  color='red', linestyle='-', label='Expected Goals')
        plt.plot(seasons, exp_assists, linewidth=5, alpha=0.3, color='green', linestyle='-', label='Expected Assists')

        plt.grid(linestyle='-')
        plt.title("Goals scored by season")
        plt.xlabel("Season")
        plt.ylabel("Stats")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.legend()
        path = DataAnalyzer().player_path(player_data["name"]) + '-attack-graph.png'
        plt.savefig(path)
        plt.show()

    def player_graph_defence(self, player_data):
        seasons = []
        yellow_cards = []
        red_cards = []
        for season, stats in player_data["all_stats_standard"].items():
            seasons.append(season)
            cards = stats.get("cards", {})
            yellow_cards.append(int(cards.get("yellow", "0")))
            red_cards.append(int(cards.get("red", "0")))

        plt.figure(figsize=(10, 6))
        plt.plot(seasons, yellow_cards, linewidth=5, color='yellow', linestyle='-', label='Yellow Cards')
        plt.plot(seasons, red_cards, linewidth=5, color='red', linestyle='-', label='Red Cards')

        plt.grid(linestyle='-')
        plt.title("Cards")
        plt.xlabel("Season")
        plt.ylabel("Cards")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.legend()
        path = DataAnalyzer().player_path(player_data["name"]) + '-defence-graph.png'
        plt.savefig(path)
        plt.show()



repository = PlayerRepository()
analyzer = DataAnalyzer()
player = analyzer.search_players('Adam Smith')
data = DataAnalyzer().get_player_data(player[0][0])
DataAnalyzer().player_graph_attack(data)
