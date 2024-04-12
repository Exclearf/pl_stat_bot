from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from unidecode import unidecode
import time
import re

options = Options()
user_agent_string = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 ' \
                    'Safari/537.36'
options.add_argument("--headless")
options.add_argument(f"user-agent={user_agent_string}")
options.add_argument("window-size=1920,1080")
driver = webdriver.Chrome(options=options)


class Scraper:

    def __init__(self, reference_site_url, player_repository):
        self.referenceUrl = reference_site_url
        self.player_repository = player_repository
        # self.__prepare_dataset()

    def generate_player_data(self, player_url):
        if self.player_repository.exists(player_url) and False:
            # File exists, read it and return its content as a dictionary
            return self.player_repository.get_player_data(player_url)

        player = dict()

        # Go to player page
        driver.get(player_url)

        cookies_button = driver.find_element(By.XPATH, '//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]')
        if cookies_button:
            cookies_button.click()

        player["name"] = unidecode(driver.find_element(By.XPATH, '//*[@id="meta"]/div[2]/h1/span').text)
        player["asciiName"] = unidecode(player["name"])

        full_name = driver.find_element(By.XPATH, '//*[@id="meta"]/div[2]/p[1]').text

        player['nationality'] = driver.find_element(By.XPATH, '//*[@id="meta"]/div[2]/p[4]/span[3]').text.split(', ')[-1].strip()

        player_img_base64 = driver.find_element(By.XPATH, '//*[@id="meta"]/div[1]/img').screenshot_as_base64

        if len(full_name.split(' ')) > 1:
            player_characteristics = driver.find_element(By.XPATH, '//*[@id="meta"]/div[2]/p[2]').text.split(' ▪  ')
            player["position"] = player_characteristics[0].split(': ')[1].strip()
            player["footed"] = player_characteristics[1].split(': ')[1].strip()
            player["fullName"] = full_name
        else:
            try:
                player_characteristics = driver.find_element(By.XPATH, '//*[@id="meta"]/div[2]/p[1]').text.split(' ▪  ')
                if len(player_characteristics)  > 0:
                    player["position"] = player_characteristics[0].split(': ')[1].strip()
                if len(player_characteristics) > 1:
                    player["footed"] = player_characteristics[1].split(': ')[1].strip()
            except:
                player["position"] = ''
                player["footed"] = ''
        if player["position"] != 'GK':
            player["standard_stats"] = self.parse_standard_stats()
            player["shooting_stats"] = self.parse_shooting_stats()
            player["passing_stats"] = self.parse_passing_stats()
        else:
            player["all_stats_goals"] = self.all_stats_goals()
            player['all_stats_goals1'] = self.all_stats_goals1()

        # Go to wiki for short bio
        driver.get("https://www.wikipedia.org/")

        m = driver.find_element(By.XPATH, '//*[@id="searchInput"]')
        m.click()
        m.send_keys(player.get("fullName", player["name"]) + ' footballer')
        time.sleep(0.2)
        m.send_keys(Keys.ENTER)
        time.sleep(0.2)

        results = driver.find_element(By.XPATH, '//*[@id="mw-content-text"]/div[*]/div[*]/ul/li[1]/table/tbody/tr/td['
                                                '2]/div[1]/a')
        results.click()
        time.sleep(0.2)

        # Get description as well as remove [1] etc
        player["shortDescription"] = re.sub(r'\[\d+]', '', driver.find_element(By.XPATH, '//*[@id="mw-content-text'
                                                                                         '"]/div[1]/p[2]').text)
        elem = None
        try:
            elem = driver.find_element(By.XPATH, '//*[@id="mw-content-text"]/div[1]/table[1]/tbody/tr[1]/td/span/a/img').screenshot_as_base64;
        except:
            elem = None
        self.player_repository.write_data(player_url, player, player_img_base64, elem)
        return player

    def __prepare_dataset(self):
        """The method which parses data relative to the reference URL

        Args:

        Returns:
            array: Data extracted by parsing
        """
        header = ['name', 'url']
        data = []

        driver.get(self.referenceUrl)

        # Parse the document into result[]
        links = driver.find_elements(By.XPATH, '//*[@id="stats_standard"]/tbody/tr[*]/td[1]/a')
        for link in links:
            data.append([link.text, link.get_attribute("href")])

        self.player_repository.write_dataset(header, data)


    # Different kinds of tables and respective parsing methods
    def parse_standard_stats(self):
        current_table = driver.find_element(By.XPATH, f'.//*[@id="all_stats_standard"]')

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
        current_table = driver.find_element(By.XPATH, f'.//*[@id="all_stats_shooting"]')

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
        current_table = driver.find_element(By.XPATH, f'.//*[@id="all_stats_passing"]')

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