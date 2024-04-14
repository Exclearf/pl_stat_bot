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
# options.add_argument("--headless")

pool = queue.Queue(maxsize=1)
idle_times = dict()
driver_map = dict()
class WebDriverPool:
    def __init__(self, size=10, timeout=60):
        self.size = size
        self.timeout = timeout
        self.condition = Condition()
        self.acquire_timeout = 3

        self.monitor_thread = Thread(target=self._monitor_driver_pool, daemon=True)
        self.monitor_thread.start()

    def acquire(self, client_id=None):
        with self.condition:
            end_time = time.time() + self.acquire_timeout

            while True:
                if client_id is not None and client_id in driver_map:
                    return driver_map[client_id]

                if pool.empty():
                    if len(idle_times) < self.size:
                        driver = webdriver.Chrome(options=options)
                        idle_times[id(driver)] = time.time()
                        if client_id:
                            driver_map[client_id] = driver
                        return driver
                else:
                    driver = pool.get()
                    if client_id:
                        driver_map[client_id] = driver
                    return driver

                remaining_time = end_time - time.time()
                if not self.condition.wait(timeout=remaining_time):
                    print('Timed out')
                    raise TimeoutError('Timed out waiting for a browser')

    def release(self, driver, client_id):
        with self.condition:
            if client_id and client_id in driver_map:
                del driver_map[client_id]

            if pool.qsize() < self.size:
                pool.put(driver)
                idle_times[id(driver)] = time.time()
            else:
                driver.quit()
            self.condition.notify()

    def _monitor_driver_pool(self):
        while True:
            with self.condition:
                current_time = time.time()
                to_close = [driver_id for driver_id, release_time in idle_times.items()
                            if current_time - release_time > self.timeout]
                for driver_id in to_close:
                    for driver in list(pool.queue):
                        if id(driver) == driver_id:
                            pool.queue.remove(driver)
                            driver.quit()
                            idle_times.pop(driver_id, None)
                            client_ids_to_remove = [k for k, v in driver_map.items() if v == driver]
                            for cid in client_ids_to_remove:
                                del driver_map[cid]
                self.condition.notify_all()
            time.sleep(10)  # Check every 10 seconds

    def __del__(self):
        while not pool.empty():
            driver = pool.get()
            driver.quit()

    @contextmanager
    def get_driver(self, client_id=None):
        driver = self.acquire(client_id)
        try:
            yield driver
        finally:
            self.release(driver, client_id)
