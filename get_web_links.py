from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timedelta

# import pandas as pd
import json
import time
import random
from typing import List, Dict
import logging
from concurrent.futures import ThreadPoolExecutor
from queue import Queue


class SeleniumNewsScraper:
    def __init__(self, headless: bool = True, num_browsers: int = 3):
        self.headless = headless
        self.num_browsers = num_browsers
        self.browser_pool = Queue()
        self.setup_logging()

        # Configure news sources with their search patterns
        self.sources = {
            "digi24": {
                "url": "https://www.digi24.ro",
                "search_url": "https://www.digi24.ro/cautare?q={query}",
                "article_pattern": "//article[contains(@class, 'article-alt')]",
                "title_pattern": ".//h2[@class='h4 article-title']/a",
                "date_pattern": ".//span[@class='article-date']",
                "link_pattern": ".//h2[@class='h4 article-title']/a",
            },
            #    "antena3": {
            #        "url": "https://www.antena3.ro",
            #        "search_url": "https://www.antena3.ro/cautare/{query}",
            #        "article_pattern": "//div[contains(@class, 'article-item')]",
            #        "title_pattern": ".//h3",
            #        "date_pattern": ".//time",
            #        "link_pattern": ".//a/@href",
            #    },
            #    "adevarul": {
            #        "url": "https://adevarul.ro",
            #        "search_url": "https://adevarul.ro/cauta?q={query}",
            #        "article_pattern": "//div[contains(@class, 'article-box')]",
            #        "title_pattern": ".//h3",
            #        "date_pattern": ".//span[contains(@class, 'date')]",
            #        "link_pattern": ".//a/@href",
            #    },
            #    "pro_tv": {
            #        "url": "https://stirileprotv.ro",
            #        "search_url": "https://adevarul.ro/cautare/{query}",
            #        "article_pattern": "//div[contains(@class, 'search-box')]",
            #        "title_pattern": ".//h2",
            #        "date_pattern": ".//div[contains(@class, 'article-date')]",
            #        "link_pattern": ".//a/@href",
            #    },
            #    "realitatea": {
            #        "url": "https://www.realitatea.net",
            #        "search_url": "https://www.realitatea.net/{query}?page={page_nr}&search-input={query}",
            #        "article_pattern": "//div[contains(@class, 'search-box')]",
            #        "title_pattern": ".//h2",
            #        "date_pattern": ".//div[contains(@class, 'article-date')]",
            #        "link_pattern": ".//a/@href",
            #    },
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

        self.initialize_browser_pool()

    def scrape_source(self, source_name: str, config: dict, query: str) -> List[Dict]:
        """Scrape a specific news source"""
        browser = self.get_browser()
        articles = []

        self.logger.info("got to scrape_source")
        try:
            search_url = config["search_url"].format(query=query)
            print(search_url)
            if not self.safe_get(browser, search_url):
                return articles

            # Wait for articles to load
            try:
                WebDriverWait(browser, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, config["article_pattern"])
                    )
                )
            except TimeoutException:
                self.logger.warning(f"Timeout waiting for articles on {source_name}")
                return articles

            # Scroll to load more articles if available
            self.scroll_page(browser)

            # Extract articles
            article_elements = browser.find_elements(
                By.XPATH, config["article_pattern"]
            )

            self.logger.info(f"got some article elements {len(article_elements)}")
            for element in article_elements:
                try:
                    title = self.extract_element_text(element, config["title_pattern"])
                    self.logger.info(f"got title")
                    date = self.extract_element_text(element, config["date_pattern"])
                    self.logger.info(f"got date")
                    link = element.find_element(
                        By.XPATH, config["link_pattern"]
                    ).get_attribute("href")
                    self.logger.info(f"got link")

                    if title and link:
                        articles.append(
                            {
                                "title": title,
                                "url": link,
                                "date": self.normalize_date(date, source_name),
                                "source": source_name,
                            }
                        )
                except Exception as e:
                    self.logger.error(
                        f"Error extracting article from {source_name}: {str(e)}"
                    )
                    continue

        except Exception as e:
            self.logger.error(f"Error scraping {source_name}: {str(e)}")

        finally:
            self.return_browser(browser)

        return articles

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="scraper.log",
        )
        self.logger = logging.getLogger(__name__)

    def initialize_browser_pool(self):
        """Initialize pool of browser instances"""
        for _ in range(self.num_browsers):
            options = webdriver.FirefoxOptions()
            if self.headless:
                options.add_argument("--headless")

            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920x1080")
            options.add_argument("--lang=ro-RO")
            options.set_preference("network.cookie.cookieBehavior", 2)

            # Use undetected-chromedriver to avoid detection
            driver = webdriver.Firefox(options)
            driver.set_page_load_timeout(30)
            self.browser_pool.put(driver)

    def get_browser(self):
        """Get a browser from the pool"""
        return self.browser_pool.get()

    def return_browser(self, browser):
        """Return a browser to the pool"""
        self.browser_pool.put(browser)

    def random_delay(self, min_seconds=2, max_seconds=5):
        """Add random delay between actions"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def safe_get(self, browser, url: str) -> bool:
        """Safely navigate to URL with error handling"""
        try:
            browser.get(url)
            self.random_delay(1, 3)
            return True
        except Exception as e:
            self.logger.error(f"Error accessing {url}: {str(e)}")
            return False

    def extract_element_text(self, element, xpath: str) -> str:
        """Safely extract text from element using xpath"""
        try:
            result = element.find_element(By.XPATH, xpath)
            return result.text.strip()
        except NoSuchElementException:
            return ""

    def scroll_page(self, browser, scroll_pause_time=2):
        """Scroll the page to load dynamic content"""
        last_height = browser.execute_script("return document.body.scrollHeight")

        while True:
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)

            new_height = browser.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def normalize_date(self, date_str: str, source: str) -> str:
        """Normalize different date formats to ISO format"""
        # Similar to previous implementation but with more robust handling
        try:
            # Remove common Romanian text
            date_str = date_str.lower()
            date_str = date_str.replace("acum", "").replace("în urmă", "")

            # Handle relative dates
            if "minut" in date_str:
                minutes = int("".join(filter(str.isdigit, date_str)))
                return (datetime.now() - timedelta(minutes=minutes)).isoformat()
            elif "ora" in date_str:
                hours = int("".join(filter(str.isdigit, date_str)))
                return (datetime.now() - timedelta(hours=hours)).isoformat()
            elif "zi" in date_str:
                days = int("".join(filter(str.isdigit, date_str)))
                return (datetime.now() - timedelta(days=days)).isoformat()

            # Handle absolute dates
            # Add more specific date format handling here

            return date_str
        except Exception as e:
            self.logger.error(f"Date parsing error for {source}: {date_str} - {str(e)}")
            return ""

    def main(self, output_file: str = "selenium_news_results.json"):
        """Main scraping process"""
        all_results = []

        #   for company in self.companies:
        #       articles = []
        #       for query in self.companies[company]:
        #           for source_name, config in self.sources.items():
        #               articles.append(self.scrape_source(source_name, config, query))
        #     all_results.extend(articles)
        with ThreadPoolExecutor(max_workers=self.num_browsers) as executor:
            futures = []

            for company in self.companies:
                for query in self.companies[company]:
                    for source_name, config in self.sources.items():
                        futures.append(
                            executor.submit(
                                self.scrape_source, source_name, config, query
                            )
                        )

            for future in futures:
                try:
                    articles = future.result()
                    all_results.extend(articles)
                except Exception as e:
                    self.logger.error(f"Error processing future: {str(e)}")

        # Deduplicate results
        unique_results = {article["url"]: article for article in all_results}.values()
        print("printing results: \n")
        # Save results
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(list(unique_results), f, ensure_ascii=False, indent=2)

        self.cleanup()

    def cleanup(self):
        """Clean up browser instances"""
        while not self.browser_pool.empty():
            browser = self.browser_pool.get()
            try:
                browser.quit()
            except:
                pass


if __name__ == "__main__":
    scraper = SeleniumNewsScraper(headless=True, num_browsers=3)
    scraper.main()
