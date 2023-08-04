import re
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote_plus

import requests
from bs4 import BeautifulSoup

from base.logger import Logger
from base.crawler import CrawlingStrategy


class WandsworthGovUkCrawlingStrategy(CrawlingStrategy):
    def __init__(self):
        self.downloader = requests.Session()
        self.downloader.verify = False
        self.logger = Logger(self.__class__.__name__).logger

    def download(self, url, timeout=100, headers=None, cookies=None, data=None) -> str:
        raw_data = None

        if not isinstance(headers, dict):
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                          '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.wandsworth.gov.uk/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/115.0.0.0 Safari/537.36',
            }

        try:
            if not data:
                response = self.downloader.get(url, timeout=timeout, headers=headers, cookies=cookies)
            else:
                response = self.downloader.post(url, timeout=timeout, headers=headers, cookies=cookies, data=data)

            if response:
                response.raise_for_status()
                raw_data = response.text

        except Exception as e:
            self.logger.error(f'HTTP Error:{str(e)}')

        return raw_data

    def crawl(self):
        viewstate, viewstate_generator, event_validation = self.get_general_search_data()
        first_page_data: str = self.get_first_page_data(viewstate, viewstate_generator, event_validation)
        application_urls: list = self.get_application_urls(first_page_data)
        base_application_url = 'https://planning.wandsworth.gov.uk/Northgate/PlanningExplorer/Generic/'
        application_urls = [f'{base_application_url}{url}' for url in application_urls]

        for url in application_urls:
            application_data = self.download(url)
            if application_data:
                application_soup = BeautifulSoup(application_data, 'lxml')
                application_document_url = self.get_application_href(application_soup, 'a[title="Link to the '
                                                                                       'application Dates page."]')
                application_date_href = self.get_application_href(application_soup, 'a[title="Link to View Related '
                                                                                    'Documents"]')
                application_date_url = f'{base_application_url}{self.clean_href(application_date_href)}'

        return application_urls

    def get_general_search_data(self) -> tuple:
        wandsworth_base_url = 'https://planning.wandsworth.gov.uk/Northgate/PlanningExplorer/GeneralSearch.aspx'
        base_url_data = self.download(wandsworth_base_url)

        viewstate = None
        viewstate_generator = None
        event_validation = None

        if base_url_data:
            base_url_soup = BeautifulSoup(base_url_data, 'lxml')
            viewstate_tag = base_url_soup.select_one('input#__VIEWSTATE')
            viewstate_generator_tag = base_url_soup.select_one('input#__VIEWSTATEGENERATOR')
            event_validation_tag = base_url_soup.select_one('input#__EVENTVALIDATION')

            if viewstate_tag and viewstate_tag.has_attr('value'):
                viewstate = viewstate_tag['value']

            if viewstate_generator_tag and viewstate_generator_tag.has_attr('value'):
                viewstate_generator = viewstate_generator_tag['value']

            if event_validation_tag and event_validation_tag.has_attr('value'):
                event_validation = event_validation_tag['value']

        return viewstate, viewstate_generator, event_validation

    def get_first_page_data(self, viewstate: str, viewstate_generator: str, event_validation: str) -> str:
        general_search_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                      '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://planning.wandsworth.gov.uk',
            'Referer': 'https://planning.wandsworth.gov.uk/Northgate/PlanningExplorer/GeneralSearch.aspx',
            'Cache-Control': 'max-age=0',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        general_search_url = 'https://planning.wandsworth.gov.uk/Northgate/PlanningExplorer/GeneralSearch.aspx'
        current_date_time = datetime.now()
        six_months_ago = current_date_time - timedelta(days=6 * 30)

        default_params = f'__VIEWSTATE={quote_plus(viewstate)}&__VIEWSTATEGENERATOR={quote_plus(viewstate_generator)}' \
                         f'&__EVENTVALIDATION={quote_plus(event_validation)}' \
                         f'&txtApplicationNumber=&txtApplicantName=&txtAgentName=&cboStreetReferenceNumber=' \
                         f'&txtProposal=&edrDateSelection=&cboWardCode=&cboParishCode=&cboApplicationTypeCode=' \
                         f'&cboDevelopmentTypeCode=&cboStatusCode=&'
        params = {
            'cboSelectDateValue': 'DATE_RECEIVED',
            'cboMonths': '1',
            'cboDays': '1',
            'rbGroup': 'rbRange',
            'dateStart': six_months_ago.strftime('%d/%m/%Y'),
            'dateEnd': current_date_time.strftime('%d/%m/%Y'),
            'csbtnSearch': 'Search',
        }
        complete_params = f'{default_params}&{urlencode(params)}'
        first_page_data = self.download(general_search_url, headers=general_search_headers, data=complete_params)

        return first_page_data

    def get_application_urls(self, first_page_data: str, max_pages: int = 5) -> list:
        first_page_soup = BeautifulSoup(first_page_data, 'lxml')
        application_urls = self.get_search_result_data(first_page_soup)
        next_url = self.get_next_url(first_page_soup)
        current_page = 1

        while current_page < max_pages:
            page_data = self.download(next_url)
            if page_data:
                page_soup = BeautifulSoup(page_data, 'lxml')
                application_urls.extend(self.get_search_result_data(page_soup))

                next_url = self.get_next_url(page_soup)
                if not next_url:
                    break
                else:
                    current_page += 1

        return application_urls

    def get_search_result_data(self, soup) -> list:
        search_results = []
        page_links = soup.select('td.TableData a.data_text')

        for link in page_links:
            search_results.append(self.clean_href(link["href"]))

        return search_results

    def get_next_url(self, soup) -> str:
        base_document_url = 'https://planning.wandsworth.gov.uk/Northgate/PlanningExplorer/Generic/'
        next_url = None
        next_url_tag = soup.select_one('a.noborder img[title="Go to next page "]').parent

        if next_url_tag and next_url_tag.has_attr('href'):
            next_url = f'{base_document_url}{self.clean_href(next_url_tag["href"])}'

        return next_url

    @staticmethod
    def get_application_href(self, soup, bs_selector: str) -> str:
        application_href = None
        application_tag = soup.select_one(bs_selector)

        if application_tag and application_tag.has_attr('href'):
            application_href = application_tag['href']

        return application_href

    @staticmethod
    def clean_href(href: str) -> str:
        return re.sub(r'\s', '', href.replace(" ", "%20"))