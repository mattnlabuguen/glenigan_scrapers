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
        self.base_application_url = 'https://planning.wandsworth.gov.uk/Northgate/PlanningExplorer/Generic/'
        self.post_request_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                      '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://planning.wandsworth.gov.uk',
            'Referer': 'https://planning.wandsworth.gov.uk/Northgate/PlanningExplorer/GeneralSearch.aspx',
            'Cache-Control': 'max-age=0',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

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
        application_urls = [f'{self.base_application_url}{url}' for url in application_urls]
        application_data_list = self.get_page_data(application_urls)

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
        general_search_url = 'https://planning.wandsworth.gov.uk/Northgate/PlanningExplorer/GeneralSearch.aspx'
        current_date_time = datetime.now()
        six_months_ago = current_date_time - timedelta(days=6 * 30)

        default_form_data = f'__VIEWSTATE={quote_plus(viewstate)}&__VIEWSTATEGENERATOR={quote_plus(viewstate_generator)}' \
                         f'&__EVENTVALIDATION={quote_plus(event_validation)}' \
                         f'&txtApplicationNumber=&txtApplicantName=&txtAgentName=&cboStreetReferenceNumber=' \
                         f'&txtProposal=&edrDateSelection=&cboWardCode=&cboParishCode=&cboApplicationTypeCode=' \
                         f'&cboDevelopmentTypeCode=&cboStatusCode=&'
        form_data = {
            'cboSelectDateValue': 'DATE_RECEIVED',
            'cboMonths': '1',
            'cboDays': '1',
            'rbGroup': 'rbRange',
            'dateStart': six_months_ago.strftime('%d/%m/%Y'),
            'dateEnd': current_date_time.strftime('%d/%m/%Y'),
            'csbtnSearch': 'Search',
        }
        complete_form_data = f'{default_form_data}&{urlencode(form_data)}'
        first_page_data = self.download(general_search_url, headers=self.post_request_headers, data=complete_form_data)

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
        next_url = None
        next_url_tag = None

        child_tag = soup.select_one('a.noborder img[title="Go to next page "]')
        if child_tag:
            next_url_tag = child_tag.parent

        if next_url_tag and next_url_tag.has_attr('href'):
            next_url = f'{self.base_application_url}{self.clean_href(next_url_tag["href"])}'

        return next_url

    def get_pdf_url(self, page_data: str):
        soup = BeautifulSoup(page_data, 'lxml')

        pdf_url = None
        viewstate = None
        viewstate_generator = None
        event_validation = None
        event_target = None
        case_no = None

        viewstate_tag = soup.select_one('input#__VIEWSTATE')
        viewstate_generator_tag = soup.select_one('input#__VIEWSTATEGENERATOR')
        event_validation_tag = soup.select_one('input#__EVENTVALIDATION')
        application_form_tag = soup.select_one('span:contains("Application Form")')
        case_no_tag = soup.select_one('span#lblCaseNo')

        if not application_form_tag:
            return pdf_url
        else:
            event_target_pattern = r'gvDocs\$ctl\d+\$lnkDShow'
            event_target_tag = application_form_tag.find_parent('tr').select_one('a')
            if event_target_tag and event_target_tag.has_attr('href'):
                event_target_match = re.search(event_target_pattern, event_target_tag['href'])
                if event_target_match:
                    event_target = event_target_match.group(0)

        if viewstate_tag and viewstate_tag.has_attr('value'):
            viewstate = viewstate_tag['value']

        if viewstate_generator_tag and viewstate_generator_tag.has_attr('value'):
            viewstate_generator = viewstate_generator_tag['value']

        if event_validation_tag and event_validation_tag.has_attr('value'):
            event_validation = event_validation_tag['value']

        if case_no_tag:
            case_no = case_no_tag.get_text()

        if event_target:
            form_data = f'__EVENTTARGET={quote_plus(event_target)}' \
                        f'&__EVENTARGUMENT=' \
                        f'&__VIEWSTATE={quote_plus(viewstate)}' \
                        f'&__VIEWSTATEGENERATOR={quote_plus(viewstate_generator)}' \
                        f'&__SCROLLPOSITIONX=0&__SCROLLPOSITIONY=0' \
                        f'&__EVENTVALIDATION={event_validation}'

            page_url = f'https://planning2.wandsworth.gov.uk/planningcase/comments.aspx?case={quote_plus(case_no)}'
            post_page_data = self.download(page_url, headers=self.post_request_headers, data=form_data)
            if post_page_data:
                post_page_soup = BeautifulSoup(post_page_data, 'lxml')
                pdf_tag = post_page_soup.select_one('a[target="_blank"]')

                if pdf_tag and pdf_tag.has_attr('href'):
                    pdf_url = pdf_tag['href']

        return pdf_url

    def get_page_data(self, application_urls: list):
        for url in application_urls:
            application_main_data = self.download(url)
            if application_main_data:
                application_soup = BeautifulSoup(application_main_data, 'lxml')
                application_documents_url = self.get_application_href(application_soup, 'a[title="Link to View Related '
                                                                                        'Documents"]')
                application_date_href = self.get_application_href(application_soup, 'a[title="Link to the '
                                                                                    'application Dates page."]')
                application_dates_url = f'{self.base_application_url}{self.clean_href(application_date_href)}'

                if application_documents_url:
                    application_documents_page_data = self.download(application_documents_url)
                    if application_documents_page_data:
                        pdf_url = self.get_pdf_url(application_documents_page_data)

                if application_dates_url:
                    application_dates_data = self.download(application_dates_url)

        return application_urls

    @staticmethod
    def get_application_href(soup, bs_selector: str) -> str:
        application_href = None
        application_tag = soup.select_one(bs_selector)

        if application_tag and application_tag.has_attr('href'):
            application_href = application_tag['href']

        return application_href

    @staticmethod
    def clean_href(href: str) -> str:
        return re.sub(r'\s', '', href.replace(" ", "%20"))
