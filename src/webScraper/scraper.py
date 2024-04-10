from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
        self.__prepare_dataset()

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

        player["name"] = driver.find_element(By.XPATH, '//*[@id="meta"]/div[2]/h1/span').text

        player_characteristics = driver.find_element(By.XPATH, '//*[@id="meta"]/div[2]/p[2]').text.split(' ▪  ')
        player["position"] = player_characteristics[0].split(': ')[1].strip()
        player["footed"] = player_characteristics[1].split(': ')[1].strip()

        full_name = driver.find_element(By.XPATH, '//*[@id="meta"]/div[2]/p[1]/strong').text

        player_img_base64 = driver.find_element(By.XPATH, '//*[@id="meta"]/div[1]/img').screenshot_as_base64

        if len(full_name.split(' ')) > 1:
            player["fullName"] = full_name

        id_to_parse = [
            "all_stats_standard",
            "all_stats_shooting",
            "all_stats_passing"
        ]

        for played_id in id_to_parse:
            current_table = driver.find_element(By.XPATH, f'.//*[@id="{played_id}"]')

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
                season["goals"] = entry.find_element(By.XPATH, './/td[10]').text
                season["assists"] = entry.find_element(By.XPATH, './/td[11]').text

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

            player[played_id] = seasons

        # Go to wiki for short bio
        driver.get("https://www.wikipedia.org/")

        m = driver.find_element(By.XPATH, '//*[@id="searchInput"]')
        m.click()
        m.send_keys(player.get("fullName", player["name"]) + ' footballer')
        time.sleep(0.2)
        m.send_keys(Keys.ENTER)
        time.sleep(0.2)

        results = driver.find_element(By.XPATH, '//*[@id="mw-content-text"]/div[2]/div[*]/ul/li[1]/table/tbody/tr/td['
                                                '2]/div[1]/a')
        results.click()
        time.sleep(0.2)

        # Get description as well as remove [1] etc
        player["shortDescription"] = re.sub(r'\[\d+]', '', driver.find_element(By.XPATH, '//*[@id="mw-content-text'
                                                                                         '"]/div[1]/p[2]').text)
        self.player_repository.write_data(player_url, player, player_img_base64)
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
