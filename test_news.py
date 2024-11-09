import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import re
from typing import List, Dict, Tuple
import concurrent.futures
import json
from urllib.parse import urljoin

class RomanianNewsScraper:
    def __init__(self):
        # Same company definitions as before
        self.companies = {
            "AXPO": ["AXPO", "AXPO Energy Romania"],
            "CEZ": ["CEZ", "CEZ Vanzare"],
            "TERMOENERGETICA": ["TERMOENERGETICA", "Termoenergetica Bucuresti"],
            "TRANSELECTRICA": ["TRANSELECTRICA", "Compania Nationala de Transport al Energiei Electrice"],
            "DELGAZ": ["DELGAZ", "DELGAZ GRID"],
            "E.ON": ["E.ON", "E.ON Energie Romania"],
            "ELECTRICA": ["ELECTRICA", "ELECTRICA FURNIZARE"],
            "ENEL": ["ENEL", "ENEL ENERGIE", "ENEL GREEN POWER"],
            "ENGIE": ["ENGIE", "ENGIE ROMANIA", "ENGIE ENERGY MANAGEMENT"],
            "HIDROELECTRICA": ["HIDROELECTRICA", "Hidroelectrica SA"],
            "NUCLEARELECTRICA": ["NUCLEARELECTRICA", "Societatea Nationala Nuclearelectrica"]
        }

        # Updated news sources with their search endpoints and parsing rules
        self.sources = {
            "digi24": {
                "base_url": "https://www.digi24.ro",
                "search_path": "/search",
                "search_param": "q",
                "article_selector": "article.article-container",
                "title_selector": "h2.article-title",
                "date_selector": "span.article-date",
                "link_selector": "a.article-link"
            },
            "antena3": {
                "base_url": "https://www.antena3.ro",
                "search_path": "/cautare",
                "search_param": "termen",
                "article_selector": "div.article-item",
                "title_selector": "h3.title",
                "date_selector": "time.date",
                "link_selector": "a.article-link"
            },
            "protv": {
                "base_url": "https://stirileprotv.ro",
                "search_path": "/cautare",
                "search_param": "q",
                "article_selector": "div.article-box",
                "title_selector": "h3.article-title",
                "date_selector": "span.date",
                "link_selector": "a.article-link"
            },
            "mediafax": {
                "base_url": "https://www.mediafax.ro",
                "search_path": "/cautare",
                "search_param": "q",
                "article_selector": "div.article-item",
                "title_selector": "h2.title",
                "date_selector": "time",
                "link_selector": "a"
            },
            "zf": {
                "base_url": "https://www.zf.ro",
                "search_path": "/search",
                "search_param": "q",
                "article_selector": "div.article",
                "title_selector": "h2",
                "date_selector": "time",
                "link_selector": "a.article-link"
            },
            # Additional sources with their configurations...
            # (Similar structure for other sources)
        }

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def normalize_date(self, date_str: str, source: str) -> str:
        """Normalize different date formats to ISO format"""
        try:
            # Handle different Romanian date formats
            date_formats = {
                "digi24": "%d.%m.%Y %H:%M",
                "antena3": "%d %B %Y",
                "protv": "%d.%m.%Y",
                "mediafax": "%Y-%m-%d %H:%M:%S",
                "zf": "%d.%m.%Y %H:%M",
                # Add more source-specific date formats
            }

            # Remove common Romanian month names and replace with numerical values
            romanian_months = {
                'ianuarie': '01', 'februarie': '02', 'martie': '03',
                'aprilie': '04', 'mai': '05', 'iunie': '06',
                'iulie': '07', 'august': '08', 'septembrie': '09',
                'octombrie': '10', 'noiembrie': '11', 'decembrie': '12'
            }

            for rom, num in romanian_months.items():
                date_str = date_str.lower().replace(rom, num)

            # Try to parse with source-specific format
            if source in date_formats:
                return datetime.strptime(date_str, date_formats[source]).isoformat()

            # Fallback to generic parsing
            return datetime.fromisoformat(date_str).isoformat()
        except Exception as e:
            print(f"Date parsing error for {source}: {date_str} - {str(e)}")
            return None

    def scrape_source(self, source_name: str, config: dict, query: str) -> List[Dict]:
        """Scrape a specific news source"""
        articles = []

        try:
            search_url = urljoin(config['base_url'], config['search_path'])
            response = requests.get(
                search_url,
                params={config['search_param']: query},
                headers=self.headers,
                timeout=15
            )

            if response.status_code != 200:
                print(f"Failed to fetch {source_name}: Status {response.status_code}")
                return articles

            soup = BeautifulSoup(response.text, 'html.parser')

            for article in soup.select(config['article_selector']):
                try:
                    title_elem = article.select_one(config['title_selector'])
                    date_elem = article.select_one(config['date_selector'])
                    link_elem = article.select_one(config['link_selector'])

                    if not all([title_elem, date_elem, link_elem]):
                        continue

                    title = title_elem.get_text(strip=True)
                    date_str = date_elem.get_text(strip=True)
                    url = urljoin(config['base_url'], link_elem['href'])

                    normalized_date = self.normalize_date(date_str, source_name)

                    articles.append({
                        'title': title,
                        'url': url,
                        'date': normalized_date,
                        'source': source_name
                    })

                except Exception as e:
                    print(f"Error parsing article from {source_name}: {str(e)}")
                    continue

            time.sleep(2)  # Polite delay between requests

        except Exception as e:
            print(f"Error scraping {source_name}: {str(e)}")

        return articles

    def main(self, output_file: str = "romanian_energy_news.json"):
        all_results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_source = {}

            for company in self.companies.keys():
                queries = self.create_search_queries(company)
                for query in queries:
                    for source_name, config in self.sources.items():
                        future = executor.submit(self.scrape_source, source_name, config, query)
                        future_to_source[future] = (company, query, source_name)

            for future in concurrent.futures.as_completed(future_to_source):
                company, query, source = future_to_source[future]
                try:
                    articles = future.result()
                    for article in articles:
                        article['company'] = company
                        article['query'] = query
                        all_results.append(article)
                except Exception as e:
                    print(f"Error processing {company} from {source}: {str(e)}")

        # Deduplicate articles based on URL
        unique_results = {article['url']: article for article in all_results}.values()

        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(list(unique_results), f, ensure_ascii=False, indent=2)

    def create_search_queries(self, company: str) -> List[str]:
        """Create search queries combining company names with related terms"""
        queries = []
        company_terms = self.companies.get(company, [company])

        # Add basic company queries
        queries.extend(company_terms)

        return queries

if __name__ == "__main__":
    scraper = RomanianNewsScraper()
    scraper.main()