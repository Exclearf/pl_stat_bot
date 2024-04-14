import csv
import re
import sys
from os import path
from unidecode import unidecode
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from src.webScraper.scraper import *
from src.repository.players_repository import *
repository = PlayerRepository()


class DataAnalyzer:
    def __init__(self):
        self.csv_file_path = "../resources/data/players_data.csv"

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
        return found_players

    #name -> path for easier movements
    def player_path(self, player_name):
        changed_player_name = player_name.replace(' ', '-')
        path = '../resources/data/parsed_players/' + changed_player_name + '/' + changed_player_name
        return path

    #Get data from json created by scraper
    def get_player_data(self, player_name):
        path = DataAnalyzer().player_path(player_name) + '.json'
        with open(path, 'r', encoding='UTF8') as file:
            data = json.load(file)
            return data

    def player_basic_data(self, player_data):

        player_basic_data = {}
        season_2023_2024 = player_data["standard_stats"]["2023-2024"]
        try:
            player_basic_data["fullName"] = player_data["fullName"]
        except:
            player_basic_data["fullName"] = player_data["name"]
        player_basic_data["nationality"] = player_data["nationality"]
        player_basic_data["position"] = player_data["position"]
        try:
            player_basic_data["footed"] = player_data["footed"]
        except:
            player_basic_data["footed"] = ''
        player_basic_data["shortDescription"] = player_data["shortDescription"]
        player_basic_data["squad"] = season_2023_2024["squad"]
        player_basic_data["leagueRank"] = season_2023_2024["leagueRank"]
        player_basic_data["age"] = season_2023_2024["age"]
        player_basic_data["goals"] = season_2023_2024["performance"]["goals"]
        player_basic_data["assists"] = season_2023_2024["performance"]["assists"]

        return player_basic_data

    def player_season_data(self, player_name, season):
        data = DataAnalyzer().get_player_data(player_name)['standard_stats'][season]
        season_data = {}
        season_data['season'] = season
        season_data['age'] = data['age']
        season_data['squad'] = data['squad']
        season_data['leagueRank'] = data['leagueRank']
        season_data['goals'] = data['performance']['goals']
        season_data['assists'] = data['performance']['assists']
        return season_data

    def player_years(self, player_data):
        player_years = []
        player_years = player_data["standard_stats"]
        player_seasons_years = list(player_years)
        player_seasons_years.append('all')
        return player_seasons_years

    def player_graph_standard(self, player_data):
        seasons = []
        goals_scored = []
        assists_made = []
        exp_goals = []
        exp_assists = []
        seasons_with_xG = []
        index = 0
        for season, stats in player_data["standard_stats"].items():
            seasons.append(season)
            if stats['goals'] == "":
                goals_scored.append(0)
            else:
                goals_scored.append(int(stats["goals"]))

            if stats['assists'] == "":
                assists_made.append(0)
            else:
                assists_made.append(int(stats["assists"]))

            performance = stats.get("performance", {})

            # count the number of seasons with xG introduced
            if performance.get("expectedGoals") != "":
                seasons_with_xG.append(season)
            else:
                index += 1

            expected_goals_str = performance.get("expectedGoals", "0")
            expected_assists_str = performance.get("expectedAssists", "0")
            exp_goals.append(float(expected_goals_str) if expected_goals_str else 0.0)
            exp_assists.append(float(expected_assists_str) if expected_assists_str else 0.0)

        #create a graph
        plt.figure(figsize=(10, 6))
        #create plots with goals and assists
        plt.plot(seasons, goals_scored, linewidth=5, color='red', linestyle='-', label='Goals Scored')
        plt.plot(seasons, assists_made, linewidth=5, color='green', linestyle='-', label='Assists Made')

        #exclude data that doesnt suit the seasons_with_xG
        exp_goals = exp_goals[index:len(seasons)]
        exp_assists = exp_assists[index:len(seasons)]

        #Only plots for seasons with xG
        plt.plot(seasons_with_xG, exp_goals, linewidth=5, alpha=0.3,  color='red', linestyle='-', label='Expected Goals')
        plt.plot(seasons_with_xG, exp_assists, linewidth=5, alpha=0.3, color='green', linestyle='-', label='Expected Assists')

        #Add a grid
        plt.grid(linestyle='-')
        #Desc
        plt.title("Goals scored by season")
        plt.xlabel("Season")
        plt.ylabel("Stats")
        #rotate desc
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.legend()
        #save the graph to the player dir
        path = DataAnalyzer().player_path(unidecode(player_data["name"])) + '-graph.png'
        plt.savefig(path)
        plt.show()

#options = Options()
#user_agent_string = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
#options.add_argument(f"user-agent={user_agent_string}")
#options.add_argument("window-size=1920,1080")
#driver = webdriver.Chrome(options=options)
#scraper = Scraper(repository, webdriver.Chrome())
##scraper.prepare_dataset()
#analyzer = DataAnalyzer()
#results = analyzer.search_players('Zinch')
#scraper.generate_player_data('https://fbref.com/en/players/' + results[0][1])

#data = analyzer.get_player_data(results[0][0])

#print(analyzer.player_season_data(results[0][0], '2021-2022'))
#DataAnalyzer().player_graph_attack(data)
#print(analyzer.player_years())
#driver.quit()