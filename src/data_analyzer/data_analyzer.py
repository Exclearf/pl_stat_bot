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
        name_pattern = re.compile(re.escape(partial_name), re.IGNORECASE)
        # open in read 'r' mode, using utf8
        with open(self.csv_file_path, 'r', encoding='UTF8') as csvfile:
            # CSV reader obj, column headers for iteration
            csv_reader = csv.DictReader(csvfile)
            # array of arrays, smaller array - [name, url] of every matched player
            for row in csv_reader:
                normalized_name = unidecode(row['name'])
                if name_pattern.search(normalized_name):
                    found_players.append([normalized_name, row['url']])
        return found_players

    # name -> path for easier movements
    def player_path(self, player_name):
        changed_player_name = player_name.replace(' ', '-')
        path = os.path.join( '..', 'resources', 'data', 'parsed_players', changed_player_name, changed_player_name)
        return path

    def graph_path(self, player_name, graph_type, graph_name):
        changed_player_name = player_name.replace(' ', '-')
        dir_graph_type = os.path.join( '..', 'resources', 'data', 'parsed_players', changed_player_name, 'graph', graph_type)
        os.makedirs(dir_graph_type, exist_ok=True)
        full_path = os.path.join(dir_graph_type, graph_name)
        return full_path

    def path_for_btn(self, primary_path):
        optimized_path = primary_path[3:]
        return optimized_path

    #G et data from json created by scraper
    def get_player_data(self, player_name):
        path = DataAnalyzer().player_path(player_name) + '.json'
        with open(path, 'r', encoding='UTF8') as file:
            data = json.load(file)
            return data

    def player_basic_data(self, player_name):
        player_data = self.get_player_data(player_name)

        # Setup player basic data dictionary with default values
        player_basic_data = {
            "fullName": player_data.get("fullName", player_data.get("name", "")),
            "nationality": player_data.get("nationality", ""),
            "position": player_data.get("position", ""),
            "footed": player_data.get("footed", ""),
            "shortDescription": player_data.get("shortDescription", ""),
        }

        # Extract season-specific data
        season_data = player_data.get("standard_stats", {}).get("2023-2024", {})
        player_basic_data.update({
            "squad": season_data.get("squad", ""),
            "leagueRank": season_data.get("leagueRank", ""),
            "matchesPlayed": season_data.get("matchesPlayed", 0),
            "competition": season_data.get("competition", ""),
            "age": season_data.get("age", 0),
        })

        # Handling goalkeeper specific data
        if self.isGK(player_name):
            gk_data = player_data.get("standard_goalkeeping", {}).get("2023-2024", {}).get("performance", {})
            player_basic_data.update({
                'cleanSheets': gk_data.get('cleanSheets', 0),
                'goalsAgainst': gk_data.get('goalsAgainst', 0)
            })
        else:
            perf_data = season_data.get("performance", {})
            player_basic_data.update({
                'goals': perf_data.get('goals', 0),
                'assists': perf_data.get('assists', 0)
            })

        return player_basic_data

    def player_season_data(self, player_name, season):
        player_data = self.get_player_data(player_name)

        season_stats = player_data.get('standard_stats', {}).get(season, {})
        season_data = {
            'season': season,
            'age': season_stats.get('age', 0),
            'squad': season_stats.get('squad', ''),
            'competition': season_stats.get('competition', ''),
            'leagueRank': season_stats.get('leagueRank', ''),
            'matchesPlayed': season_stats.get('matchesPlayed', 0),
        }

        if self.isGK(player_name):
            gk_stats = player_data.get('standard_goalkeeping', {}).get(season, {}).get('performance', {})
            season_data.update({
                'cleanSheets': gk_stats.get('cleanSheets', 0),
                'goalsAgainst': gk_stats.get('goalsAgainst', 0)
            })
        else:
            perf_data = season_stats.get('performance', {})
            season_data.update({
                'goals': perf_data.get('goals', 0),
                'assists': perf_data.get('assists', 0)
            })

        return season_data

    def player_years(self, player_data):
        player_seasons_years = list(player_data["standard_stats"].keys())
        player_seasons_years.append('all')
        return player_seasons_years

    # if CreationDate(graph) > creationDate(json) -> new graph
    def check_graphs_age(self, player_name, graph_type, graph_name):
        base_path = os.path.join('../resources/data/parsed_players', player_name)
        graph_path = os.path.join(base_path, 'graph', graph_type, f'{graph_name}-graph.png')
        json_path = os.path.join(base_path, f'{player_name}.json')

        if os.path.exists(graph_path):
            graph_mod_time = datetime.fromtimestamp(os.path.getmtime(graph_path))
            try:
                with open(json_path, 'r', encoding='UTF-8') as file:
                    creation_date = datetime.fromisoformat(json.load(file)['creationDate'])
            except (IOError, KeyError, json.JSONDecodeError) as e:
                print(f"Error reading from JSON file: {e}")
                return False

            return graph_mod_time > creation_date
        else:
            return False

    def isGK(self, player_name):
        data = self.get_player_data(player_name)
        if data['position'] == "GK":
            return True
        else:
            return False

    def get_int_performance_stats(self, stats, stats_type, stats_data):
        performance = stats.get(stats_type, {})
        result = performance.get(stats_data, {})
        # Convert empty strings to 0
        result = int(result) if result else 0
        return result

    def get_float_performance_stats(self, stats, stats_type, stats_data):
        performance = stats.get(stats_type, {})
        result = performance.get(stats_data, {})
        # Convert empty strings to 0
        result = float(result) if result else 0.0
        return result

    def get_int_stats(self, stats, stats_data):
        result = stats.get(stats_data, {})
        # Convert empty strings to 0
        result = int(result) if result else 0
        return result

    def get_float_stats(self, stats, stats_data):
        result = stats.get(stats_data, {})
        # Convert empty strings to 0
        result = float(result) if result else 0.0
        return result

    def remove_yyyy(self, seasons):
        full_seasons = [element for element in seasons if "-" in element]
        skipped_count = len(seasons) - len(full_seasons)
        return full_seasons, skipped_count

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
        for season, stats in player_data["standard_stats"].items():
            seasons.append(season)
            goals_scored.append(self.get_int_performance_stats(stats, "performance", 'goals'))
            assists_made.append(self.get_int_performance_stats(stats, "performance", 'assists'))
            exp_goals.append(self.get_float_performance_stats(stats, "performance", 'expectedGoals'))
            exp_assists.append(self.get_float_performance_stats(stats, "performance", 'expectedAssists'))

        # exclude data that didnt exist back then
        zero_count = exp_goals.count(0.0)
        seasons_with_xG = seasons[zero_count:]
        exp_goals = exp_goals[zero_count:]
        exp_assists = exp_assists[zero_count:]

        print(exp_goals)
        print(exp_assists)
        print(goals_scored)
        print(assists_made)
        print(seasons_with_xG)
        #create a g/a graph
        plt.figure(figsize=(10, 6))
        #create plots with goals and assists
        plt.plot(seasons, goals_scored, linewidth=5, color='red', linestyle='-', label='Goals Scored')
        plt.plot(seasons, assists_made, linewidth=5, color='green', linestyle='-', label='Assists Made')

        #Only plots for seasons with xG
        plt.plot(seasons_with_xG, exp_goals, linewidth=5, alpha=0.3, color='red', linestyle='-', label='Expected Goals')
        plt.plot(seasons_with_xG, exp_assists, linewidth=5, alpha=0.3, color='green', linestyle='-',
                 label='Expected Assists')

        #Add a grid
        plt.grid(linestyle='-')
        #Desc
        plt.title("Goals/Assists Made/Expected by season")
        plt.xlabel("Season")
        plt.ylabel("Goals/Assists")
        #rotate desc
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.legend()
        #save the graph to the player dir
        path = self.graph_path(unidecode(player_data["name"]), 'standard', 'Goals_Assists.png')
        plt.savefig(path)
        plt.show()
        return self.path_for_btn(path)

    def player_graph_standard_cards(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='standard', graph_name='cards'):
            return
        player_data = DataAnalyzer().get_player_data(player_name)
        red_cards = []
        yellow_cards = []
        seasons = []

        for season, stats in player_data["standard_stats"].items():
            seasons.append(season)
            red_cards.append(self.get_int_performance_stats(stats, "cards", 'red'))
            yellow_cards.append(self.get_int_performance_stats(stats, "cards", 'yellow'))

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

    def player_graph_shooting(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='shots', graph_name='shots'):
            return

        #shotsOnTarget/shots,  xG/matches,  goals/matches
        seasons = []
        shots_on_target = []
        shots = []
        goals = []
        matches = []
        exp_goals = []
        real_match_eff = []
        exp_match_eff = []
        shot_precision = []
        seasons_with_exp = []

        player_data = self.get_player_data(player_name)

        for season, stats in player_data["shooting_stats"].items():
            seasons.append(season)
            shots_on_target.append(self.get_int_performance_stats(stats, 'performance', 'shotsOnTarget'))
            shots.append(self.get_int_performance_stats(stats, 'performance', 'shots'))

            if shots[-1] != 0:
                shot_precision.append(round((shots_on_target[-1] / shots[-1]), 2) * 100)
            else:
                shot_precision.append(0.0)

        for season, stats in player_data["standard_stats"].items():
            exp_goals.append(self.get_float_performance_stats(stats, 'performance', 'expectedGoals'))
            goals.append(self.get_int_performance_stats(stats, 'performance', 'goals'))
            matches.append(self.get_int_stats(stats, 'matchesPlayed'))

            if matches[-1] != 0:
                real_match_eff.append(round((goals[-1] / matches[-1]), 2) * 100)
            else:
                real_match_eff.append(0.0)

            if matches[-1] != 0:
                exp_match_eff.append(round((exp_goals[-1] / matches[-1]), 2) * 100)
            else:
                exp_match_eff.append(0.0)

        zero_count = exp_match_eff.count(0.0)
        seasons_with_exp = seasons[zero_count:]
        exp_match_eff = exp_match_eff[zero_count:]

        plt.figure(figsize=(10, 6))
        plt.plot(seasons, real_match_eff, linewidth=5, color='yellow', linestyle='-', label='Real Match Effectiveness')
        plt.plot(seasons_with_exp, exp_match_eff, linewidth=5, alpha=0.5, color='yellow', linestyle='-',
                 label='Expected Match Effectiveness')
        plt.plot(seasons, shot_precision, linewidth=5, color='blue', linestyle='-', label='Shot Precision')

        # Add a grid
        plt.grid(linestyle='-')
        # Desc
        plt.title("Shooting Effectiveness by Season")
        plt.xlabel("Season")
        plt.ylabel("Effectiveness, %")
        # rotate desc
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.legend()
        # save the graph to the player dir
        path = DataAnalyzer().graph_path(unidecode(player_data["name"]), 'shots', 'Shots_Goals.png')
        plt.savefig(path)
        plt.show()
        return self.path_for_btn(path)

    def player_graph_shooting_distance(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='shots', graph_name='shots'):
            return
        # distance target/shots
        seasons = []
        shots_on_target = []
        shots = []
        goals = []
        average_shot_distance = []
        shots_precision = []

        player_data = self.get_player_data(player_name)

        for season, stats in player_data["shooting_stats"].items():
            seasons.append(season)
            shots_on_target.append(self.get_int_performance_stats(stats, 'performance', 'shotsOnTarget'))
            shots.append(self.get_int_performance_stats(stats, 'performance', 'shots'))
            average_shot_distance.append(self.get_float_performance_stats(stats, 'performance', 'averageShotDistance'))

            if shots[-1] != 0:

                shots_precision.append((round((shots_on_target[-1] / shots[-1]), 2)) * 100)
            else:
                shots_precision.append(0.0)

        zero_count_distance = average_shot_distance.count(0.0)
        seasons_with_shot_distance = seasons[zero_count_distance:]
        average_shot_distance = average_shot_distance[zero_count_distance:]

        zero_count_precision = shots_precision.count(0.0)
        seasons_with_shot_precision = seasons[zero_count_precision:]
        shots_precision = shots_precision[zero_count_precision:]

        for season, stats in player_data["standard_stats"].items():
            goals.append(self.get_int_performance_stats(stats, 'performance', 'goals'))

        plt.figure(figsize=(10, 6))
        plt.plot(seasons, goals, linewidth=5, color='blue', linestyle='-', label='Goals')
        plt.plot(seasons_with_shot_distance, average_shot_distance, linewidth=5, color='yellow', linestyle='-',
                 label='Average Shot Distance')
        plt.plot(seasons_with_shot_precision, shots_precision, linewidth=5, color='green', linestyle='-',
                 label='Shots Effectiveness')

        # Add a grid
        plt.grid(linestyle='-')
        # Desc
        plt.title("Shot stats with distance by season")
        plt.xlabel("Season")
        plt.ylabel("Stats")
        # rotate desc
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.legend()
        # save the graph to the player dir
        path = self.graph_path(unidecode(player_data["name"]), 'shots', 'Shots_Distance.png')
        plt.savefig(path)
        plt.show()
        return self.path_for_btn(path)

    def player_graph_passing_assists(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='passing', graph_name='assists'):
            return
        player_data = self.get_player_data(player_name)

        seasons = []
        passes_att = []
        passes_com = []
        matches = []
        assists_made = []
        exp_assists = []
        real_match_eff = []
        exp_match_eff = []
        pass_precision = []
        seasons_with_exp = []
        index = 0

        for season, stats in player_data["passing_stats"].items():
            seasons.append(season)
            passes_att.append(self.get_int_performance_stats(stats, 'performance', 'passesAttempted'))
            passes_com.append(self.get_int_performance_stats(stats, 'performance', 'passesCompleted'))

            if passes_att[-1] != 0:
                pass_precision.append(round((passes_com[-1] / passes_att[-1]), 2) * 100)
            else:
                pass_precision.append(0.0)

        #get the xA and Assists
        for season, stats in player_data["standard_stats"].items():
            assists_made.append(self.get_int_performance_stats(stats, "performance", 'assists'))
            exp_assists.append(self.get_float_performance_stats(stats, "performance", 'expectedAssists'))
            matches.append(self.get_int_stats(stats, 'matchesPlayed'))

            if matches[-1] != 0:
                real_match_eff.append(round((assists_made[-1] / matches[-1]), 2) * 100)
            else:
                real_match_eff.append(0.0)

            if matches[-1] != 0:
                exp_match_eff.append(round((exp_assists[-1] / matches[-1]), 2) * 100)
            else:
                exp_match_eff.append(0.0)

        zero_count = exp_assists.count(0.0)
        seasons_with_exp = seasons[zero_count:]
        exp_match_eff = exp_match_eff[zero_count:]
        pass_precision = pass_precision[zero_count:]

        plt.figure(figsize=(10, 6))
        plt.plot(seasons, real_match_eff, linewidth=5, color='yellow', linestyle='-',
                 label='Real Match Effectiveness')
        plt.plot(seasons_with_exp, pass_precision, linewidth=5, color='blue', linestyle='-', label='Pass Precision')
        plt.plot(seasons_with_exp, exp_match_eff, linewidth=5, alpha=0.5, color='yellow', linestyle='-',
                 label='Expected Match Effectiveness')
        
        # Add a grid
        plt.grid(linestyle='-')
        # Desc
        plt.title("Assists Effectiveness by season")
        plt.xlabel("Season")
        plt.ylabel("Effectiveness, %")
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
        plt.plot(seasons_with_distance, short_eff, linewidth=5, color='green', label='Short Passes')
        plt.plot(seasons_with_distance, mid_eff, linewidth=5, color='yellow', label='Medium Passes')
        plt.plot(seasons_with_distance, long_eff, linewidth=5, color='blue', label='Long Passes')

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

        for season, stats in player_data["standard_goalkeeping"].items():
            seasons.append(season)
            pen_att.append(self.get_int_performance_stats(stats, 'penalty', 'attempted'))
            pen_sav.append(self.get_int_performance_stats(stats, 'penalty', 'saved'))

            sh_att.append(self.get_int_performance_stats(stats, 'performance', 'shotsOnTargetAgainst'))
            sh_sav.append(self.get_int_performance_stats(stats, 'performance', 'saves'))

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
        pen_eff = pen_eff[zero_count:]
        sh_eff = sh_eff[zero_count:]
        seasons_with_data = seasons[zero_count:]

        plt.figure(figsize=(10, 6))
        plt.plot(seasons_with_data, sh_eff, linewidth=5, color='green', label='Shots Saving Efficiency')
        plt.plot(seasons_with_data, pen_eff, linewidth=5, color='blue', label='Penalties Saving Efficiency')
        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Penalties/Shots Saving Efficiency")
        plt.xlabel("Season")
        plt.ylabel("Efficiency, %")
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
        cleanSheets = []
        matches = []
        sh_eff = []
        seasons = []
        great_matches = []

        for season, stats in player_data["standard_goalkeeping"].items():
            seasons.append(season)
            sh_att.append(self.get_int_performance_stats(stats, 'performance', 'shotsOnTargetAgainst'))
            sh_sav.append(self.get_int_performance_stats(stats, 'performance', 'saves'))
            cleanSheets.append(self.get_int_performance_stats(stats, 'performance', 'cleanSheets'))
            matches.append(int(self.get_float_stats(stats, 'matchesPlayed')))

            # saves / shots on target
            if sh_att[-1] != 0:
                sh_eff.append(round((sh_sav[-1] / sh_att[-1]), 2) * 100)
            else:
                sh_eff.append(0.0)

            if matches[-1] != 0:
                great_matches.append(round((cleanSheets[-1] / matches[-1]), 2) * 100)
            else:
                great_matches.append(0.0)

        plt.figure(figsize=(10, 6))
        plt.plot(seasons, great_matches, linewidth=5, color='yellow', label='Clean Sheet Matches %')
        plt.plot(seasons, sh_eff, linewidth=5, color='green', label='Shots Saved %')
        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Saves/Clean Sheets")
        plt.xlabel("Season")
        plt.ylabel("Efficiency, %")
        plt.ylim(0, 100)
        plt.xticks(rotation=45)
        plt.tight_layout()
        path = self.graph_path(unidecode(player_data["name"]), 'bgk', 'Saves.png')
        plt.savefig(path)
        plt.show()

    def player_graph_agk(self, player_name):
        if self.check_graphs_age(player_name.replace(' ', '-'), graph_type='agk', graph_name='main'):
            return
        player_data = self.get_player_data(player_name)

        seasons = []
        g_exp = []
        sh_att = []
        sh_ag = []
        expected_eff = []
        true_eff = []
        seasons_with_sh_ag = []

        for season, stats in player_data["advanced_goalkeeping"].items():
            seasons.append(season)
            g_exp.append(self.get_float_stats(stats, 'postShotExpected'))

        for season, stats in player_data["standard_goalkeeping"].items():
            sh_att.append(self.get_int_performance_stats(stats, 'performance', 'shotsOnTargetAgainst'))
            sh_ag.append(self.get_int_performance_stats(stats, 'performance', 'goalsAgainst'))

            if sh_att[-1] != 0:
                true_eff.append(round((sh_ag[-1] / sh_att[-1]), 2) * 100)
            else:
                true_eff.append(0.0)

            if sh_att[-1] != 0:
                expected_eff.append(round((g_exp[-1] / sh_att[-1]), 2) * 100)
            else:
                expected_eff.append(0.0)

        zero_count = g_exp.count(0.0)
        g_exp = g_exp[zero_count:]
        seasons_with_sh_ag = seasons[zero_count:]

        plt.figure(figsize=(10, 6))
        plt.plot(seasons, true_eff, linewidth=5, color='yellow', label='Goals/Shots')
        plt.plot(seasons, expected_eff, linewidth=5, alpha=0.7, color='green', label='Expected Goals/Shots')
        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Goals Expectation")
        plt.xlabel("Season")
        plt.ylabel("Goals")
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
        seasons = []
        seasons_with_data = []
        avgDistOfDefActions = []
        defActionOutsidePenArea = []
        passesAttempted = []
        outside_freq = []
        distance_part = []
        # 115 yards
        field_length = 115

        for season, stats in player_data["advanced_goalkeeping"].items():
            seasons.append(season)
            avgDistOfDefActions.append(self.get_float_stats(stats, 'avgDistOfDefActions'))
            defActionOutsidePenArea.append(self.get_float_stats(stats, 'defActionOutsidePenArea'))
            passesAttempted.append(self.get_float_stats(stats, 'passesAttempted'))

            if passesAttempted[-1] != 0:
                #actions outside of pen area / all passes
                outside_freq.append(round((defActionOutsidePenArea[-1] / passesAttempted[-1]), 2) * 100)
            else:
                outside_freq.append(0.0)

            #% of the length
            distance_part.append(round((avgDistOfDefActions[-1] / field_length), 2) * 100)

        zero_count = distance_part.count(0.0)
        distance_part = distance_part[zero_count:]
        outside_freq = outside_freq[zero_count:]
        seasons_with_data = seasons[zero_count:]

        plt.figure(figsize=(10, 6))
        plt.plot(seasons_with_data, distance_part, linewidth=5, color='yellow', label=' avg % of field distance')
        plt.plot(seasons_with_data, outside_freq, linewidth=5, color='green',
                 label='% of actions outside of penalty area')
        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Sweeper")
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

        seasons = []
        seasons_with_data = []
        passes_attempted = []
        launches_attempted = []
        matches = []
        launches_att_by_match = []
        passes_att_by_match = []
        i = 0

        player_data = self.get_player_data(player_name)

        for season, stats in player_data["standard_stats"].items():
            matches.append(self.get_int_stats(stats, 'matchesPlayed'))

        for season, stats in player_data["advanced_goalkeeping"].items():
            seasons.append(season)
            passes_attempted.append(self.get_int_stats(stats, 'passesAttempted'))
            launches_attempted.append(self.get_int_stats(stats, 'passesAttemptedLaunched'))

            if matches[i] != 0:
                launches_att_by_match.append(round((launches_attempted[-1] / matches[i]), 2))
                passes_att_by_match.append(round((passes_attempted[-1] / matches[i]), 2))
            else:
                launches_att_by_match.append(0.0)
                passes_att_by_match.append(0.0)

            i = i + 1

        zero_count = launches_att_by_match.count(0.0)
        launches_att_by_match = launches_att_by_match[zero_count:]
        passes_att_by_match = passes_att_by_match[zero_count:]
        seasons_with_data = seasons[zero_count:]

        plt.figure(figsize=(10, 6))
        plt.plot(seasons_with_data, launches_att_by_match, linewidth=5, color='yellow', label='Launch Attempts by Match')
        plt.plot(seasons_with_data, passes_att_by_match, linewidth=5, color='green', label='Pass Attempts by Match')
        plt.legend()
        plt.grid(linestyle='-')
        plt.title("Pass/Launch Attempts")
        plt.xlabel("Season")
        plt.ylabel("Number by match")
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
results = analyzer.search_players('Jordan Pickford')
#
print(results[0][1])
scraper.generate_player_data('https://fbref.com/en/players/' + results[0][1] )

data = analyzer.get_player_data(results[0][0])

print(analyzer.player_graph_shooting("Erling-Haaland"))

print(analyzer.player_graph_standard_ga("Erling-Haaland"))
print(analyzer.player_graph_standard_cards("Erling-Haaland"))
print(analyzer.player_graph_passing_distance("Erling-Haaland"))
print(analyzer.player_graph_passing_assists("Erling-Haaland"))

print(DataAnalyzer().player_graph_shooting("Jordan Pickford"))

DataAnalyzer().player_graph_bgk_penalties("Jordan Pickford")
DataAnalyzer().player_graph_bgk_saves("Jordan Pickford")
DataAnalyzer().player_graph_agk("Jordan Pickford")

DataAnalyzer().player_graph_agk_passes("Jordan Pickford")

driver.quit()
print(DataAnalyzer().player_season_data("Jordan Pickford", "2022-2023"))
print(DataAnalyzer().player_basic_data("Jordan Pickford"))
DataAnalyzer().player_graph_bgk_saves("Jordan Pickford")
DataAnalyzer().player_graph_agk_passes("Jordan Pickford")
analyzer = DataAnalyzer()
analyzer = DataAnalyzer()
analyzer.player_graph_bgk_saves("Jordan Pickford")
#DataAnalyzer().player_graph_shooting_distance("Kevin-De-Bruyne")
#print(DataAnalyzer().player_season_data("Jordan Pickford", '2021-2022'))
'''