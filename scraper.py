from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timedelta

import time
import random
from typing import List, Dict
import logging
from concurrent.futures import ThreadPoolExecutor
from queue import Queue


class WebScraper:
    def __init__(self):
        self.driver
        self.sources = {
            "digi24": {
                "url": "https://www.digi24.ro",
                "search_url": "https://www.digi24.ro/search?q={query}",
                "article_pattern": "//article[contains(@class, 'article')]",
                "title_pattern": ".//h2[@class='h4 article-title']/a",
                "date_pattern": ".//span[@class='article-date']",
                "link_pattern": ".//h2[@class='h4 article-title']/a/@href",
            },
            #     "antena3": {
            #         "url": "https://www.antena3.ro",
            #         "search_url": "https://www.antena3.ro/cautare/{query}",
            #         "article_pattern": "//div[contains(@class, 'article-item')]",
            #         "title_pattern": ".//h3",
            #         "date_pattern": ".//time",
            #         "link_pattern": ".//a/@href",
            #     },
            #     "adevarul": {
            #         "url": "https://adevarul.ro",
            #         "search_url": "https://adevarul.ro/cauta?q={query}",
            #         "article_pattern": "//div[contains(@class, 'article-box')]",
            #         "title_pattern": ".//h3",
            #         "date_pattern": ".//span[contains(@class, 'date')]",
            #         "link_pattern": ".//a/@href",
            #     },
            #     "pro_tv": {
            #         "url": "https://stirileprotv.ro",
            #         "search_url": "https://adevarul.ro/cautare/{query}",
            #         "article_pattern": "//div[contains(@class, 'search-box')]",
            #         "title_pattern": ".//h2",
            #         "date_pattern": ".//div[contains(@class, 'article-date')]",
            #         "link_pattern": ".//a/@href",
            #     },
            #     "realitatea": {
            #         "url": "https://www.realitatea.net",
            #         "search_url": "https://www.realitatea.net/{query}?page={page_nr}&search-input={query}",
            #         "article_pattern": "//div[contains(@class, 'search-box')]",
            #         "title_pattern": ".//h2",
            #         "date_pattern": ".//div[contains(@class, 'article-date')]",
            #         "link_pattern": ".//a/@href",
            #     },
        }

        self.companies = {
            "AXPO": ["AXPO", "AXPO Energy Romania"],
            "CEZ": ["CEZ", "CEZ Vanzare"],
            "TERMOENERGETICA": ["TERMOENERGETICA", "Termoenergetica Bucuresti"],
            "TRANSELECTRICA": [
                "TRANSELECTRICA",
                "Compania Nationala de Transport al Energiei Electrice",
            ],
            # Add other companies...
        }

    def set_options(self):
        options = webdriver.FirefoxOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--lang=ro-RO")

        self.driver = webdriver.Firefox(options)
        self.driver.set_page_load_timeout(30)

    def random_delay(self, min_seconds=2, max_seconds=5):
        """Add random delay between actions"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def safe_get(self, url):
        try:
            self.driver.get(url)
            self.random_delay(1, 3)
            return True
        except Exception as e:
            print("error at safe_get")
            return False

    def run(self):
        for company in self.companies:
            for query in self.companies[company]:
                for source_name, config in self.sources.items():
                    self.scrape_page(config, query, source_name)

    def run_test(self, config, query: str = "", source_name: str = ""):
        return self.scrape_page(config, query, source_name)

    def extract_element_text(self, element, xpath: str) -> str:
        """Safely extract text from element using xpath"""
        try:
            result = element.find_element(By.XPATH, xpath)
            return result.text.strip()
        except NoSuchElementException:
            return ""

    def scrape_page(
        self, config: Dict[str, str], query: str, source_name: str
    ) -> List[Dict]:
        articles = []
        try:
            search_url = config["search_url"].format(query=query)
            if not self.safe_get(search_url):
                return articles

            # Wait for articles to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, config["article_pattern"])
                    )
                )
            except TimeoutException:
                print(f"Timeout waiting for articles on {source_name}")
                return articles

            self.scroll_page(self.driver)

            article_elements = self.driver.find_elements(
                By.XPATH, config["article_pattern"]
            )
            for element in article_elements:
                try:
                    title = self.extract_element_text(element, config["title_pattern"])
                    # date = self.extract_element_text(element, config["date_pattern"])
                    link = element.find_element(
                        By.XPATH, config["link_pattern"]
                    ).get_attribute("href")

                    if title and link:
                        articles.append(
                            {
                                "title": title,
                                "url": link,
                                "date": "",
                                "source": source_name,
                            }
                        )
                except Exception as e:
                    print(f"Error extracting article from {source_name}: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error scraping {source_name}: {str(e)}")

        finally:
            return articles

            # Scroll to load more articles if available


if __name__ == "__main__":
    my_driver = WebScraper()
    my_driver.set_options()
    my_driver.driver.get("https://www.google.com")
