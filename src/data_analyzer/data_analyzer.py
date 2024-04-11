import csv
import re
from unidecode import unidecode


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
            for row in csv_reader:
                row['name'] = unidecode(row['name'])
                if name_pattern.search(row['name']):
                    found_players.append({'name': row['name'], 'url': row['url']})

        if not found_players:
            return({'name': 'No players found matching the provided partial name.', 'url': ''})

        return found_players


analyzer = DataAnalyzer()
results = analyzer.search_players('Odegaard')
print(results)