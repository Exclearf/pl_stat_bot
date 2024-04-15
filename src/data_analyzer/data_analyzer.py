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
from PIL import Image

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from src.webScraper.scraper import *
from src.repository.players_repository import *
repository = PlayerRepository()
plt.style.use('dark_background')


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
    def graph_path(self, player_name, graph_type, graph_name):
        changed_player_name = player_name.replace(' ', '-')
        dir_graph = f'../resources/data/parsed_players/{changed_player_name}/graph'
        os.makedirs(dir_graph, exist_ok=True)
        dir_graph_type = f'{dir_graph}/{graph_type}'
        os.makedirs(dir_graph_type, exist_ok=True)
        path = dir_graph_type + '/' + graph_name
        return path

    def path_for_btn(self, primary_path):
        optimized_path = primary_path[3:]
        return optimized_path


    #Get data from json created by scraper
    def get_player_data(self, player_name):
        path = DataAnalyzer().player_path(player_name) + '.json'
        with open(path, 'r', encoding='UTF8') as file:
            data = json.load(file)
            return data

    def player_basic_data(self, player_name):
        player_data = self.get_player_data(player_name)

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
        player_basic_data["competition"] = season_2023_2024["competition"]
        player_basic_data["age"] = season_2023_2024["age"]
        if self.isGK(player_data["name"]):
            season_2023_2024_gk = player_data["standard_goalkeeping"]["2023-2024"]
            player_basic_data['cleanSheets'] = season_2023_2024_gk['performance']['cleanSheets']
            player_basic_data['goalsAgainst'] = season_2023_2024_gk['performance']['goalsAgainst']
        else:
            player_basic_data['goals'] = season_2023_2024['performance']['goals']
            player_basic_data['assists'] = season_2023_2024['performance']['assists']

        return player_basic_data

    def player_season_data(self, player_name, season):
        data = self.get_player_data(player_name)['standard_stats'][season]

        season_data = {}
        season_data['season'] = season
        season_data['age'] = data['age']
        season_data['squad'] = data['squad']
        season_data["competition"] = data["competition"]
        season_data['leagueRank'] = data['leagueRank']
        if self.isGK(player_name):
            gk_data = self.get_player_data(player_name)['standard_goalkeeping'][season]
            season_data['cleanSheets'] = gk_data['performance']['cleanSheets']
            season_data['goalsAgainst'] = gk_data['performance']['goalsAgainst']
        else:
            season_data['goals'] = data['performance']['goals']
            season_data['assists'] = data['performance']['assists']
        return season_data

    def player_years(self, player_data):
        player_years = []
        player_years = player_data["standard_stats"]
        player_seasons_years = list(player_years)
        player_seasons_years.append('all')
        return player_seasons_years

    # if CreationDate(graph) > creationDate(json) -> new graph
    def check_graphs_age(self, player_name, graph_type, graph_name):
        player_data_filepath = '../resources/data/parsed_players/' + player_name + '/'
        if os.path.exists(f'../resources/data/parsed_players/{player_name}/graph/{graph_type}/{graph_name}-graph.png'):
                ti_c = os.path.getmtime(f'../resources/data/parsed_players/{player_name}/graph/{graph_type}/{graph_name}-graph.png')
                c_ti = datetime.fromtimestamp(ti_c)

                with open(player_data_filepath + player_name + '.json', 'rb') as file:
                    if c_ti > datetime.fromisoformat(json.load(file)['creationDate']):
                        return True
                    else:
                        return False
        else:
            return False

    def isGK(self, player_name):
        data = self.get_player_data(player_name)
        if data['position'] == "GK":
            return True
        else:
            return False


########################################################################################################################
#                                                        GRAPHS                                                        #
########################################################################################################################

    def player_graph_standard_ga(self, player_name):

        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='standard', graph_name='ga'):
            return
        player_data = DataAnalyzer().get_player_data(player_name)
        seasons = []
        goals_scored = []
        assists_made = []
        exp_goals = []
        exp_assists = []
        seasons_with_xG = []
        index = 0
        for season, stats in player_data["standard_stats"].items():
            seasons.append(season)

            if stats['performance']['goals'] == "":
                goals_scored.append(0)
            else:
                goals_scored.append(int(stats['performance']["goals"]))

            if stats['performance']['assists'] == "":
                assists_made.append(0)
            else:
                assists_made.append(int(stats['performance']["assists"]))

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

        #create a g/a graph
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
        path = DataAnalyzer().graph_path(unidecode(player_data["name"]), 'standard', 'Goals_Assists.png')
        plt.savefig(path)
        plt.show()
        return DataAnalyzer().path_for_btn(path)

    def player_graph_standard_cards(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='standard', graph_name='cards'):
            return
        player_data = DataAnalyzer().get_player_data(player_name)
        red_cards = []
        yellow_cards = []
        seasons = []

        for season, stats in player_data["standard_stats"].items():
            seasons.append(season)

            if stats['cards']['red'] == "":
                red_cards.append(0)
            else:
                red_cards.append(int(stats['cards']["red"]))

            if stats['cards']['yellow'] == "":
                yellow_cards.append(0)
            else:
                yellow_cards.append(int(stats['cards']["yellow"]))

        # create cards graph
        plt.figure(figsize=(10, 6))
        # create plots with red and yellow cards
        plt.plot(seasons, yellow_cards, linewidth=5, color='yellow', linestyle='-', label='Yellow Cards')
        plt.plot(seasons, red_cards, linewidth=5, color='red', linestyle='-', label='Red Cards')

        # Add a grid
        plt.grid(linestyle='-')
        # Desc
        plt.title("Cards received by season")
        plt.xlabel("Season")
        plt.ylabel("Cards")
        # rotate desc
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.legend()
        # save the graph to the player dir
        path = DataAnalyzer().graph_path(unidecode(player_data["name"]), 'standard', 'Cards.png')
        plt.savefig(path)
        plt.show()
        return DataAnalyzer().path_for_btn(path)

    #goals-expected goals
    def player_graph_shooting(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='shots', graph_name='shots'):
            return
        player_data = DataAnalyzer().get_player_data(player_name)
        shots = []
        goals_scored = []
        shotsOnTarget = []
        exp_goals = []
        seasons_with_xG = []
        seasons = []
        index = 0

        for season, stats in player_data["standard_stats"].items():
            seasons.append(season)

            if stats['performance']['goals'] == "":
                goals_scored.append(0)
            else:
                goals_scored.append(int(stats['performance']["goals"]))

            performance = stats.get("performance", {})

            # count the number of seasons with xG introduced
            if performance.get("expectedGoals") != "":
                seasons_with_xG.append(season)
            else:
                index += 1

            expected_goals_str = performance.get("expectedGoals", "0")
            exp_goals.append(float(expected_goals_str) if expected_goals_str else 0.0)

        for season, stats in player_data["shooting_stats"].items():

            if stats['performance']['shots'] == "":
                shots.append(0)
            else:
                shots.append(int(stats['performance']['shots']))

            if stats['performance']['shotsOnTarget'] == "":
                shotsOnTarget.append(0)
            else:
                shotsOnTarget.append(int(stats['performance']['shotsOnTarget']))

        plt.figure(figsize=(10, 6))
        plt.plot(seasons, goals_scored, linewidth=5, color='green', linestyle='-', label='Goals Scored')
        plt.plot(seasons, shots, linewidth=5, color='yellow', linestyle='-', label='Shots')
        plt.plot(seasons, shotsOnTarget, linewidth=5, color='purple', linestyle='-', label='On Target')


        exp_goals = exp_goals[index:len(seasons)]
        plt.plot(seasons_with_xG, exp_goals, linewidth=5, alpha=0.3, color='green', linestyle='-', label='Expected Goals')

        # Add a grid
        plt.grid(linestyle='-')
        # Desc
        plt.title("Shot stats by season")
        plt.xlabel("Season")
        plt.ylabel("Stats")
        # rotate desc
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.legend()
        # save the graph to the player dir
        path = DataAnalyzer().graph_path(unidecode(player_data["name"]), 'shots', 'Shots_Goals.png')
        plt.savefig(path)
        plt.show()
        return DataAnalyzer().path_for_btn(path)

    def player_graph_passing_assists(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='passing', graph_name='assists'):
            return
        player_data = DataAnalyzer().get_player_data(player_name)

        assists_made = []
        exp_assists = []
        seasons_with_xG = []
        seasons = []
        index = 0

        #get the xA and Assists
        for season, stats in player_data["standard_stats"].items():
            seasons.append(season)
            if stats['performance']['assists'] == "":
                assists_made.append(0)
            else:
                assists_made.append(int(stats['performance']["assists"]))

            performance = stats.get("performance", {})

            # count the number of seasons with xG introduced
            if performance.get("expectedGoals") != "":
                seasons_with_xG.append(season)
            else:
                index += 1

            expected_assists_str = performance.get("expectedAssists", "0")
            exp_assists.append(float(expected_assists_str) if expected_assists_str else 0.0)

        plt.figure(figsize=(10, 6))

        plt.plot(seasons, assists_made, linewidth=5, color='green', linestyle='-', label='Assists Made')

        # exclude data that doesnt suit the seasons_with_xG
        exp_assists = exp_assists[index:len(seasons)]

        # Only plots for seasons with xG
        plt.plot(seasons_with_xG, exp_assists, linewidth=5, alpha=0.3, color='green', linestyle='-', label='Expected Assists')

        # Add a grid
        plt.grid(linestyle='-')
        # Desc
        plt.title("Assists and passes by season")
        plt.xlabel("Season")
        plt.ylabel("Stats")
        # rotate desc
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.legend()
        # save the graph to the player dir
        path = DataAnalyzer().graph_path(unidecode(player_data["name"]), 'passing', 'Assists.png')
        plt.savefig(path)
        plt.show()
        return DataAnalyzer().path_for_btn(path)

    def player_graph_passing_distance(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='passing', graph_name='passes'):
            return
        player_data = DataAnalyzer().get_player_data(player_name)
        short_att = []
        short_com = []
        short_eff = []

        mid_att = []
        mid_com = []
        mid_eff = []

        long_att = []
        long_com = []
        long_eff = []

        seasons_with_distance = []
        seasons = []

        def get_passes_stats(stats, pass_type):
            passes = stats.get("passes", {}).get(pass_type, {})
            attempted = passes.get("attempted", "0")
            completed = passes.get("completed", "0")
            # Convert empty strings to 0
            attempted = int(attempted) if attempted else 1
            completed = int(completed) if completed else 0
            return attempted, completed

        for season, stats in player_data["passing_stats"].items():
            seasons.append(season)
            performance = stats.get("performance", {})
            short_att.append(get_passes_stats(performance, "shortPasses")[0])
            short_com.append(get_passes_stats(performance, "shortPasses")[1])
            mid_att.append(get_passes_stats(performance, "mediumPasses")[0])
            mid_com.append(get_passes_stats(performance, "mediumPasses")[1])
            long_att.append(get_passes_stats(performance, "longPasses")[0])
            long_com.append(get_passes_stats(performance, "longPasses")[1])

            short_eff.append(round(short_com[-1] / short_att[-1], 2) * 100)
            mid_eff.append(round(mid_com[-1] / mid_att[-1], 2) * 100)
            long_eff.append(round(long_com[-1] / long_att[-1], 2) * 100)

        zero_count = short_eff.count(0.0)
        short_eff = short_eff[zero_count:]
        mid_eff = mid_eff[zero_count:]
        long_eff = long_eff[zero_count:]
        seasons_with_distance = seasons[zero_count:]

        plt.figure(figsize=(10, 6))
        plt.plot(seasons_with_distance, short_eff, linewidth=5, color='green',  label='Short')
        plt.plot(seasons_with_distance, mid_eff, linewidth=5, color='red', label='Medium')
        plt.plot(seasons_with_distance, long_eff, linewidth=5, color='blue', label='Long')

        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Passes Efficiency by Season")
        plt.xlabel("Season")
        plt.ylabel("Passes Efficiency, %")
        plt.ylim(0, 100)
        plt.xticks(rotation=45)
        plt.tight_layout()
        path = DataAnalyzer().graph_path(unidecode(player_data["name"]), 'passing', 'Passes.png')
        plt.savefig(path)
        plt.show()
        return self.path_for_btn(path)

    def player_graph_bgk_penalties(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='bgk', graph_name='penalties'):
            return
        player_data = self.get_player_data(player_name)

        seasons = []
        pen_att = []
        pen_sav = []
        pen_eff = []

        sh_att = []
        sh_sav = []
        sh_eff = []
        seasons_with_data = []

        def get_gk_stats(stats, stats_type, stats_data):
            performance = stats.get(stats_type, {})
            result = performance.get(stats_data, {})
            # Convert empty strings to 0
            result = int(result) if result else 0
            return result

        for season, stats in player_data["standard_goalkeeping"].items():
            seasons.append(season)
            pen_att.append(get_gk_stats(stats, 'penalty', 'attempted'))
            pen_sav.append(get_gk_stats(stats, 'penalty', 'saved'))

            sh_att.append(get_gk_stats(stats, 'performance', 'shotsOnTargetAgainst'))
            sh_sav.append(get_gk_stats(stats, 'performance', 'saves'))

            if pen_att[-1] == 0:
                eff_pen_att = pen_att[-1] + 1
                pen_eff.append(round(pen_sav[-1] / eff_pen_att, 2) * 100)
            else:
                pen_eff.append(round(pen_sav[-1] / pen_att[-1], 2) * 100)

            if sh_att[-1] == 0:
                eff_sh_att = sh_att[-1] + 1
                sh_eff.append(round(sh_sav[-1] / eff_sh_att, 2) * 100)
            else:
                sh_eff.append(round(sh_sav[-1] / sh_att[-1], 2) * 100)

        zero_count = pen_att.count(0)
        pen_att = pen_att[zero_count:]
        pen_sav = pen_sav[zero_count:]
        pen_eff = pen_eff[zero_count:]

        sh_att = sh_att[zero_count:]
        sh_sav = sh_sav[zero_count:]
        sh_eff = sh_eff[zero_count:]
        seasons_with_data = seasons[zero_count:]

        print(sh_eff)
        print(sh_att)
        print(sh_sav)
        print(seasons_with_data)

        plt.figure(figsize=(10, 6))
        plt.plot(seasons_with_data, sh_eff, linewidth=5, color='red', label='Shots Saving')
        plt.plot(seasons_with_data, pen_eff, linewidth=5, color='blue', label='Penalties Saving')
        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Penalties/Shots Saving Efficiency")
        plt.xlabel("Season")
        plt.ylabel("Penalties/Shots Saving Efficiency, %")
        plt.ylim(0, 100)
        plt.xticks(rotation=45)
        plt.tight_layout()
        path = self.graph_path(unidecode(player_data["name"]), 'bgk', 'Penalties_Shots.png')
        plt.savefig(path)
        plt.show()

    def player_graph_bgk_saves(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='bgk', graph_name='saves'):
            return
        player_data = self.get_player_data(player_name)

        sh_att = []
        sh_sav = []
        sh_ag = []
        seasons = []
        def get_gk_stats(stats, stats_type, stats_data):
            performance = stats.get(stats_type, {})
            result = performance.get(stats_data, {})
            # Convert empty strings to 0
            result = int(result) if result else 0
            return result

        for season, stats in player_data["standard_goalkeeping"].items():
            seasons.append(season)
            sh_att.append(get_gk_stats(stats, 'performance', 'shotsOnTargetAgainst'))
            sh_sav.append(get_gk_stats(stats, 'performance', 'saves'))
            sh_ag.append(get_gk_stats(stats, 'performance', 'goalsAgainst'))

        plt.figure(figsize=(10, 6))
        plt.plot(seasons, sh_att, linewidth=5, color='yellow', label='Shots On Target')
        plt.plot(seasons, sh_sav, linewidth=5, color='green', label='Shots Saved')
        plt.plot(seasons, sh_ag, linewidth=5, color='red', label='Goals')
        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Shots On Target Efficiency")
        plt.xlabel("Season")
        plt.ylabel("Shots/Goals/Saves")
        plt.ylim()
        plt.xticks(rotation=45)
        plt.tight_layout()
        path = self.graph_path(unidecode(player_data["name"]), 'bgk', 'Saves.png')
        plt.savefig(path)
        plt.show()

    def player_graph_agk(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='agk', graph_name='main'):
            return
        player_data = self.get_player_data(player_name)

        plt.figure(figsize=(10, 6))
        plt.plot([1, 2, 3], [3, 2, 1], linewidth=5, color='blue', label='Long')
        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Stats")
        plt.xlabel("Season")
        plt.ylabel("Efficiency, %")
        plt.ylim()
        plt.xticks(rotation=45)
        plt.tight_layout()
        path = self.graph_path(unidecode(player_data["name"]), 'agk', 'Advanced-Data.png')
        plt.savefig(path)
        plt.show()

    def player_graph_agk_sweeper(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='agk', graph_name='sweeper'):
            return
        player_data = self.get_player_data(player_name)

        plt.figure(figsize=(10, 6))
        plt.plot([1, 2, 3], [3, 2, 1], linewidth=5, color='blue', label='Long')
        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Stats")
        plt.xlabel("Season")
        plt.ylabel("Efficiency, %")
        plt.ylim()
        plt.xticks(rotation=45)
        plt.tight_layout()
        path = self.graph_path(unidecode(player_data["name"]), 'agk', 'Sweeper-Activities.png')
        plt.savefig(path)
        plt.show()

    def player_graph_agk_passes(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='agk', graph_name='passes'):
            return
        player_data = self.get_player_data(player_name)

        plt.figure(figsize=(10, 6))
        plt.plot([1, 2, 3], [3, 2, 1], linewidth=5, color='blue', label='Long')
        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Stats")
        plt.xlabel("Season")
        plt.ylabel("Efficiency, %")
        plt.ylim()
        plt.xticks(rotation=45)
        plt.tight_layout()
        path = self.graph_path(unidecode(player_data["name"]), 'agk', 'Passes.png')
        plt.savefig(path)
        plt.show()

'''
options = Options()
user_agent_string = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
options.add_argument(f"user-agent={user_agent_string}")
options.add_argument("window-size=1920,1080")
#
driver = webdriver.Chrome(options=options)
scraper = Scraper(repository, webdriver.Chrome())
analyzer = DataAnalyzer()
results = analyzer.search_players('Pickford')
#
scraper.generate_player_data('https://fbref.com/en/players/' + results[0][1])

data = analyzer.get_player_data(results[0][0])
print(analyzer.player_graph_standard_ga("Jordan Pickford"))
print(analyzer.player_graph_standard_cards("Jordan Pickford"))
print(analyzer.player_graph_passing_distance("Jordan Pickford"))
print(analyzer.player_graph_passing_assists("Jordan Pickford"))
print(analyzer.player_graph_shooting("Jordan Pickford"))

DataAnalyzer().player_graph_bgk_penalties("Jordan Pickford")
DataAnalyzer().player_graph_bgk_saves("Jordan Pickford")
DataAnalyzer().player_graph_agk("Jordan Pickford")
DataAnalyzer().player_graph_agk_passes("Jordan Pickford")

driver.quit()
print(DataAnalyzer().player_season_data("Jordan Pickford", "2022-2023"))
print(DataAnalyzer().player_basic_data("Jordan Pickford"))
DataAnalyzer().player_graph_bgk_saves("Jordan Pickford")
'''