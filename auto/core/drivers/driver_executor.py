"""Commands for browsing a website"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path
from sys import platform
from typing import Type

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeDriverService
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.options import ArgOptions as BrowserOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeDriverService
from selenium.webdriver.edge.webdriver import WebDriver as EdgeDriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as GeckoDriverService
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxDriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.safari.webdriver import WebDriver as SafariDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager as EdgeDriverManager
from dotenv import load_dotenv

load_dotenv()

class DriverMetaData:
    selenium_web_browser: str = "chrome"
    selenium_headless: bool = False
    session_id: str = None


class DriverWatch:
    log_thread = None

    def listen(self, driver):
        # 日志打印
        self.log_thread = threading.Thread(target=self.listen_console_logs, args=(driver,))
        self.log_thread.start()

    def destory(self):
        pass

    def listen_console_logs(self, driver):
        while True:
            logs = driver.get_log('browser')
            for log_entry in logs:
                print("控制台输出:", log_entry['level'], "-", log_entry['message'])
            time.sleep(1)


class DriverExecutor:
    driver: WebDriver = None
    meta_data: DriverMetaData = None
    driver_watch: DriverWatch = None

    def start(self, meta_data: DriverMetaData = DriverMetaData()) -> DriverExecutor:
        """Browse a website and return the answer and links to the user

        Args:
            url (str): The url of the website to browse
            question (str): The question to answer using the content of the webpage

        Returns:
            str: The answer and links to the user and the webdriver
        """
        self.driver = None
        try:

            if meta_data is None:
                self.meta_data = DriverMetaData()
            else:
                self.meta_data = meta_data

            self.driver = self.init_browser(self.meta_data)
            # 填写sessionId
            self.meta_data.session_id = self.driver.session_id

            # 初始化监听
            self.driver_watch = DriverWatch()
            self.driver_watch.listen(self.driver)
            return self

        except WebDriverException as e:
            # These errors are often quite long and include lots of context.
            # Just grab the first line.
            msg = e.msg.split("\n")[0]
            if "net::" in msg:
                raise Exception(
                    f"A networking error occurred while trying to load the page: "
                    + re.sub(r"^unknown error: ", "", msg)
                )
            raise Exception(msg)

    def init_browser(self, config: DriverMetaData) -> WebDriver:
        """Open a browser window and load a web page using Selenium

          Params:
              url (str): The URL of the page to load
              config (Config): The applicable application configuration

          Returns:
              driver (WebDriver): A driver object representing the browser window to scrape
          """
        logging.getLogger("selenium").setLevel(logging.CRITICAL)

        options_available: dict[str, Type[BrowserOptions]] = {
            "chrome": ChromeOptions,
            "edge": EdgeOptions,
            "firefox": FirefoxOptions,
            "safari": SafariOptions,
        }

        options: BrowserOptions = options_available[config.selenium_web_browser]()
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.49 Safari/537.36"
        )

        if config.selenium_web_browser == "firefox":
            if config.selenium_headless:
                options.headless = True
                options.add_argument("--disable-gpu")
            self.driver = FirefoxDriver(
                service=GeckoDriverService(GeckoDriverManager().install()), options=options
            )
        elif config.selenium_web_browser == "edge":
            self.driver = EdgeDriver(
                service=EdgeDriverService(EdgeDriverManager().install()), options=options
            )
        elif config.selenium_web_browser == "safari":
            # Requires a bit more setup on the users end
            # See https://developer.apple.com/documentation/webkit/testing_with_webdriver_in_safari
            self.driver = SafariDriver(options=options)
        else:
            if platform == "linux" or platform == "linux2":
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--remote-debugging-port=9222")

            options.add_argument("--no-sandbox")
            if config.selenium_headless:
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")

            # >>>>>>>>>>>>>>>>>>>>>>>>> DEBUG >>>>>>>>>>>>>>>>>>>>
            # chromium_driver_path = Path("/usr/bin/chromedriver")
            chromium_driver_path = Path(os.getenv("LOCAL_DRIVER_PATH"))

            self.driver = ChromeDriver(
                service=ChromeDriverService(str(chromium_driver_path))
                if chromium_driver_path.exists()
                else ChromeDriverService(ChromeDriverManager().install()),
                options=options,
            )
        return self.driver

    def open_page_in_browser(self, url: str) -> WebDriver:
        self.driver.get(url)

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        return self.driver

    def close_browser(self) -> None:
        """Close the browser

        Args:
            driver (WebDriver): The webdriver to close

        Returns:
            None
        """
        self.driver_watch.destory()
        self.driver.quit()
