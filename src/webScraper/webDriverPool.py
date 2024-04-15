from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from threading import Condition, Thread
import queue
import time
from contextlib import contextmanager

options = Options()
user_agent_string = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
options.add_argument(f"user-agent={user_agent_string}")
options.add_argument("window-size=1920,1080")

class WebDriverPool:
    def __init__(self, size, browser_timeout, driver_pool_monitor_frequency, max_wait_time, headless):
        self.size = int(size)
        self.browser_timeout = int(browser_timeout)
        self.driver_pool_monitor_frequency = int(driver_pool_monitor_frequency)
        self.max_wait_time = int(max_wait_time)

        if headless == 'True':
            options.add_argument("--headless")

        self.pool = queue.Queue(maxsize=self.size)
        self.condition = Condition()

        self.idle_times = dict()
        self.driver_map = dict()
        self.monitor_thread = Thread(target=self._monitor_driver_pool, daemon=True)
        self.monitor_thread.start()

    def acquire(self, client_id=None):
        with self.condition:
            end_time = time.time() + self.max_wait_time

            while True:
                if client_id is not None and client_id in self.driver_map:
                    return self.driver_map[client_id]

                if self.pool.empty():
                    if len(self.idle_times) < self.size:
                        driver = webdriver.Chrome(options=options)
                        driver.set_page_load_timeout(360)
                        self.idle_times[id(driver)] = time.time()
                        if client_id:
                            self.driver_map[client_id] = driver
                        return driver
                else:
                    driver = self.pool.get()
                    if client_id:
                        self.driver_map[client_id] = driver
                    return driver

                remaining_time = end_time - time.time()
                if not self.condition.wait(timeout=remaining_time):
                    print('Timed out')
                    raise TimeoutError('Timed out waiting for a browser')

    def release(self, driver, client_id):
        with self.condition:
            if client_id and client_id in self.driver_map:
                del self.driver_map[client_id]

            if self.pool.qsize() < self.size:
                self.pool.put(driver)
                self.idle_times[id(driver)] = time.time()
            else:
                driver.quit()
            self.condition.notify()

    def _monitor_driver_pool(self):
        while True:
            with self.condition:
                current_time = time.time()
                to_close = [driver_id for driver_id, release_time in self.idle_times.items()
                            if current_time - release_time > self.browser_timeout]
                for driver_id in to_close:
                    for driver in list(self.pool.queue):
                        if id(driver) == driver_id:
                            self.pool.queue.remove(driver)
                            driver.quit()
                            self.idle_times.pop(driver_id, None)
                            client_ids_to_remove = [k for k, v in self.driver_map.items() if v == driver]
                            for cid in client_ids_to_remove:
                                del self.driver_map[cid]
                self.condition.notify_all()
            time.sleep(self.driver_pool_monitor_frequency)

    def __del__(self):
        while not self.pool.empty():
            driver = self.pool.get()
            driver.quit()

    @contextmanager
    def get_driver(self, client_id=None):
        driver = self.acquire(client_id)
        try:
            yield driver
        finally:
            self.release(driver, client_id)
