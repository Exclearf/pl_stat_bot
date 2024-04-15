from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from unidecode import unidecode
import time
import re
from datetime import datetime


class Scraper:
    def __init__(self, repo, driver):
        self.driver = None
        self.player_repository = repo
        self.driver = driver

    def generate_player_data(self, player_url):
        player = dict()

        player['creationDate'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Go to player page
        self.driver.get(player_url)

        if player_url not in self.driver.current_url:
            raise RuntimeError('Player has no page')

        try:
            btn = self.driver.find_element(By.XPATH, '//*[@id="modal-close"]')
            btn.click()
        except:
            pass

        try:
            cookies_button = self.driver.find_element(By.XPATH, '//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]')
            cookies_button.click()
        except:
            print("No cookie button found")

        player["name"] = unidecode(self.driver.find_element(By.XPATH, '//*[@id="meta"]/div[2]/h1/span').text)
        player["asciiName"] = unidecode(player["name"])

        full_name = self.driver.find_element(By.XPATH, '//*[@id="meta"]/div[2]/p[1]').text

        try:
            player_img_base64 = self.driver.find_element(By.XPATH, '//*[@id="meta"]/div[1]/img').screenshot_as_base64
        except:
            print(f'Reference image not found for {player["name"]}')

        if full_name.find(player["name"].split(' ')[0]) != -1:
            player["fullName"] = full_name

        rows = self.driver.find_elements(By.XPATH, f'//*[@id="meta"]/div[2]/p')
        for row in rows:
            if 'Club: ' in row.text:
                player['club'] = row.text.split(': ')[-1]
            player['club'] = ''
            if 'Position: ' in row.text:
                row_text_parts = row.text.split(' ▪  ')
                if len(row_text_parts) > 0:
                    player["position"] = row_text_parts[0].split(': ')[1].strip()
                if len(row_text_parts) > 1:
                    player["footed"] = row_text_parts[1].split(': ')[1].strip()
            if 'Born: ' in row.text:
                player['nationality'] = " ".join(row.text.split(', ')[-1].strip().split(' ')[:-1])

        player["standard_stats"] = self.parse_standard_stats()
        player["shooting_stats"] = self.parse_shooting_stats()
        player["passing_stats"] = self.parse_passing_stats()
        if player["position"] == 'GK':
            player["standard_goalkeeping"] = self.parse_standard_goalkeeping()
            player['advanced_goalkeeping'] = self.parse_advanced_goalkeeping()

        # Go to wiki for short bio
        self.driver.get("https://wikipedia.org/")
        try:
            select = Select(self.driver.find_element_by_xpath('//*[@id="searchLanguage"]'))
            select.select_by_value('English')
        except:
            pass

        m = self.driver.find_element(By.XPATH, '//*[@id="searchInput"]')
        m.click()
        m.send_keys(player.get("fullName", player["name"]) + ' footballer ' + player['standard_stats']['2023-2024'].get('squad', ''))
        time.sleep(0.2)
        m.send_keys(Keys.ENTER)
        time.sleep(0.2)

        results = self.driver.find_element(By.XPATH, '//*[@id="mw-content-text"]/div[*]/div[*]/ul/li[1]/table/tbody/tr/td['
                                                '2]/div[1]/a')
        results.click()
        time.sleep(0.2)

        # Get description as well as remove [1] etc
        player["shortDescription"] = re.sub(r'\[\d+]', '', self.driver.find_element(By.XPATH, '//*[@id="mw-content-text'
                                                                                    '"]/div[1]/p[*]').text)
        wiki_img_base64 = None
        try:
            wiki_img_base64 = self.driver.find_element(By.XPATH, '//*[@id="mw-content-text"]/div[1]/table[1]/tbody/tr[1]/td/span/a/img').screenshot_as_base64
        except:
            pass
        self.player_repository.write_data(player_url, player, player_img_base64, wiki_img_base64)
        return player

    def prepare_dataset(self):
        """The method which parses data relative to the reference URL

        Args:

        Returns:
            array: Data extracted by parsing
        """
        header = ['name', 'url']
        data = []

        self.driver.get('https://fbref.com/en/comps/9/stats/Premier-League-Stats')

        try:
            cookies_button = self.driver.find_element(By.XPATH, '//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]')
            cookies_button.click()
        except:
            print("No cookie button found")

        # Parse the document into result[]
        links = self.driver.find_elements(By.XPATH, '//*[@id="stats_standard"]/tbody/tr[*]/td[1]/a')
        for link in links:
            data.append([link.text, link.get_attribute("href").replace('https://fbref.com/en/players/', '')])

        self.player_repository.write_dataset(header, data)
        print('Preparation ended')
        return


    # Different kinds of tables and respective parsing methods
    def parse_standard_stats(self):
        current_table = self.driver.find_element(By.XPATH, f'.//*[@id="all_stats_standard"]')

        entries = current_table.find_elements(By.XPATH, './/*[@id= "stats"]')

        seasons = dict()
        for entry in entries:
            current_season = entry.find_element(By.XPATH, './/th').text

            season = dict()
            season["age"] = entry.find_element(By.XPATH, './/td[1]').text
            season["squad"] = entry.find_element(By.XPATH, './/td[2]/a').text
            season["country"] = entry.find_element(By.XPATH, './/td[3]/a[2]').text
            season["competition"] = entry.find_element(By.XPATH, './/td[4]/a').text
            season["leagueRank"] = entry.find_element(By.XPATH, './/td[5]').text
            season["matchesPlayed"] = entry.find_element(By.XPATH, './/td[6]').text

            performance = dict()
            performance["goals"] = entry.find_element(By.XPATH, './/td[10]').text
            performance["expectedGoals"] = entry.find_element(By.XPATH, './/td[18]').text
            performance["assists"] = entry.find_element(By.XPATH, './/td[11]').text
            performance["expectedAssists"] = entry.find_element(By.XPATH, './/td[20]').text
            season["performance"] = performance

            cards = dict()
            cards["yellow"] = entry.find_element(By.XPATH, './/td[16]').text
            cards["red"] = entry.find_element(By.XPATH, './/td[17]').text
            season["cards"] = cards

            seasons[current_season] = season

        return seasons

    def parse_shooting_stats(self):
        current_table = self.driver.find_element(By.XPATH, f'.//*[@id="all_stats_shooting"]')

        entries = current_table.find_elements(By.XPATH, './/*[@id= "stats"]')

        seasons = dict()
        for entry in entries:
            current_season = entry.find_element(By.XPATH, './/th').text

            season = dict()

            performance = dict()
            performance["shots"] = entry.find_element(By.XPATH, './/td[8]').text
            performance["shotsOnTarget"] = entry.find_element(By.XPATH, './/td[9]').text
            performance['averageShotDistance'] = entry.find_element(By.XPATH, './/td[15]').text
            performance['shotsFromFreeKicks'] = entry.find_element(By.XPATH, './/td[16]').text
            season["performance"] = performance

            seasons[current_season] = season

        return seasons

    def parse_passing_stats(self):
        current_table = self.driver.find_element(By.XPATH, f'.//*[@id="all_stats_passing"]')

        entries = current_table.find_elements(By.XPATH, './/*[@id= "stats"]')
        seasons = dict()
        for entry in entries:
            current_season = entry.find_element(By.XPATH, './/th').text

            season = dict()

            performance = dict()

            performance["passesCompleted"] = entry.find_element(By.XPATH, './/td[7]').text
            performance["passesAttempted"] = entry.find_element(By.XPATH, './/td[8]').text

            passes = dict()

            l_passes = dict()
            l_passes["completed"] = entry.find_element(By.XPATH, './/td[18]').text
            l_passes["attempted"] = entry.find_element(By.XPATH, './/td[19]').text
            passes["longPasses"] = l_passes

            m_passes = dict()
            m_passes["completed"] = entry.find_element(By.XPATH, './/td[15]').text
            m_passes["attempted"] = entry.find_element(By.XPATH, './/td[16]').text
            passes["mediumPasses"] = m_passes

            s_passes = dict()
            s_passes["completed"] = entry.find_element(By.XPATH, './/td[12]').text
            s_passes["attempted"] = entry.find_element(By.XPATH, './/td[13]').text
            passes["shortPasses"] = s_passes

            performance['passes'] = passes

            season["performance"] = performance

            seasons[current_season] = season

        return seasons

    def parse_standard_goalkeeping(self):
        current_table = self.driver.find_element(By.XPATH, f'.//*[@id="all_stats_keeper"]')

        entries = current_table.find_elements(By.XPATH, './/*[@id= "stats"]')

        seasons = dict()
        for entry in entries:
            current_season = entry.find_element(By.XPATH, './/th').text

            season = dict()
            season["age"] = entry.find_element(By.XPATH, './/td[1]').text
            season["squad"] = entry.find_element(By.XPATH, './/td[2]/a').text
            season["country"] = entry.find_element(By.XPATH, './/td[3]/a[2]').text
            season["competition"] = entry.find_element(By.XPATH, './/td[4]/a').text
            season["leagueRank"] = entry.find_element(By.XPATH, './/td[5]').text
            season["matchesPlayed"] = entry.find_element(By.XPATH, './/td[6]').text
            season["matchesPlayed"] = entry.find_element(By.XPATH, './/td[7]').text
            season["gamesStarted"] = entry.find_element(By.XPATH, './/td[8]').text

            performance = dict()
            performance["goalsAgainst"] = entry.find_element(By.XPATH, './/td[10]').text
            performance["shotsOnTargetAgainst"] = entry.find_element(By.XPATH, './/td[12]').text
            performance["saves"] = entry.find_element(By.XPATH, './/td[13]').text
            performance["cleanSheets"] = entry.find_element(By.XPATH, './/td[18]').text
            season["performance"] = performance

            penalty = dict()
            penalty["attempted"] = entry.find_element(By.XPATH, './/td[20]').text
            penalty["saved"] = entry.find_element(By.XPATH, './/td[22]').text
            season["penalty"] = penalty

            seasons[current_season] = season

        return seasons

    def parse_advanced_goalkeeping(self):
        current_table = self.driver.find_element(By.XPATH, f'.//*[@id="all_stats_keeper_adv"]')

        entries = current_table.find_elements(By.XPATH, './/*[@id= "stats"]')

        seasons = dict()
        for entry in entries:
            current_season = entry.find_element(By.XPATH, './/th').text

            season = dict()
            season["postShotExpected"] = entry.find_element(By.XPATH, './/td[12]').text
            season["passesCompletedLaunched"] = entry.find_element(By.XPATH, './/td[16]').text
            season["passesAttempted"] = entry.find_element(By.XPATH, './/td[19]').text
            season["defActionOutsidePenArea"] = entry.find_element(By.XPATH, './/td[29]').text
            season["avgDistOfDefActions"] = entry.find_element(By.XPATH, './/td[31]').text

            seasons[current_season] = season

        return seasons
