import io
import json
import re

from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

from base.parser import ParsingStrategy
from base.logger import Logger
from .defaults import Defaults


class WandsworthGovUkParsingStrategy(ParsingStrategy):
    def __init__(self):
        self.logger = Logger(self.__class__.__name__).logger
        self.data_template = {
            'council_decision': None, 'application_number': None, 'application_type': None,
            'site_address': None, 'proposal': None, 'appeal_submitted': None,
            'appeal_decision': None, 'appeal_date_lodged': None, 'appeal_decision_date': None,
            'received': None, 'registered': None, 'decision_expiry': None,
            'easting': None, 'northing': None, 'planning_portal_reference': None
        }

    def parse(self, raw_data_list: list):
        data_list = []
        for raw_data in raw_data_list:
            data = self.data_template

            main_details_soup = None
            dates_soup = None
            document = None

            if 'main_details_data' in raw_data and raw_data['main_details_data']:
                main_details_soup = BeautifulSoup(raw_data['main_details_data'], 'lxml')

            if 'dates_data' in raw_data and raw_data['dates_data']:
                dates_soup = BeautifulSoup(raw_data['dates_data'], 'lxml')

            if 'document_data' in raw_data and raw_data['document_data']:
                document_byte_stream = io.BytesIO(raw_data['document_data'])
                document = PdfReader(document_byte_stream)

            if main_details_soup:
                data['council_decision'] = self.get_table_value(main_details_soup, 'Decision')
                data['application_number'] = self.get_table_value(main_details_soup, 'Application Number')
                data['application_type'] = self.get_table_value(main_details_soup, 'Application Type')
                data['site_address'] = self.get_table_value(main_details_soup, 'Site Address')
                data['proposal'] = self.get_table_value(main_details_soup, 'Proposal')
                data['appeal_submitted'] = self.get_table_value(main_details_soup, 'Appeal Submitted?')
                data['appeal_decision'], data['appeal_decision_date'] = self.get_decision_values(main_details_soup)
                data['appeal_date_lodged'] = self.get_table_value(main_details_soup, 'Appeal Lodged')

            if dates_soup:
                data['received'] = self.get_table_value(dates_soup, 'Received?')
                data['registered'] = self.get_table_value(dates_soup, 'Registered')
                data['decision_expiry'] = self.get_table_value(dates_soup, 'Decision Expiry')

            if document:
                data['easting'] = self.get_pdf_values(document, r'Easting \(x\) (\d+)Northing')
                data['northing'] = self.get_pdf_values(document, r"\(y\) (\d+)")
                data['planning_portal_reference'] = self.get_pdf_values(document, r"(PP-\d{7})")

            data_list.append(data)

        return data_list

    def get_pdf_values(self, document, pattern: str) -> str:
        page_text = ' '.join([page.extract_text() for page in document.pages]).strip()  # Join all pages and their text.
        page_text = re.sub(r'\s+', ' ', page_text)
        matches = list(re.finditer(pattern, page_text))
        if matches:
            return ' '.join(set([match.group(1) for match in matches]))

    def get_table_value(self, soup, column_name: str) -> str:
        value = Defaults.NOT_FOUND.value
        try:
            pattern = re.compile(f'^' + re.escape(column_name) + '$')
            child_tag = soup.find('span', text=pattern)
            if child_tag:
                parent_tag = child_tag.parent
                child_tag.decompose()

                tag_text = parent_tag.get_text().strip()

                if tag_text:
                    value = tag_text

        except Exception as e:
            self.logger.error(str(e))
            value = Defaults.EXTRACTION_ERROR.value

        return value

    def get_decision_values(self, soup) -> tuple:
        decision_values = (None, None)
        try:
            extracted_value = self.get_table_value(soup, 'Decision')
            if extracted_value not in [Defaults.NOT_FOUND.value, Defaults.EXTRACTION_ERROR.value]:
                decision_values = extracted_value.split('&nbsp;')

        except Exception as e:
            self.logger.error(str(e))

        return decision_values
