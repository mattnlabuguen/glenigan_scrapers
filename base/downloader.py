import requests
from requests.exceptions import HTTPError, ConnectionError

from retrying import retry


class Downloader:
    max_retries = 5
    retry_delay = 5000  # In milliseconds

    def __init__(self):
        self.requester = requests.Session()
        self.requester.verify = False

    @retry(stop_max_attempt_number=max_retries, wait_fixed=retry_delay, retry_on_exception=ConnectionError)
    def get(self, url, timeout=100, headers=None, cookies=None):
        try:
            response = self.requester.get(url, timeout=timeout, headers=headers, cookies=cookies)
            response.raise_for_status()

            return response
        except ConnectionError:
            raise ConnectionError
        except HTTPError:
            raise HTTPError

    @retry(stop_max_attempt_number=max_retries, wait_fixed=retry_delay, retry_on_exception=ConnectionError)
    def post(self, url, timeout=100, headers=None, cookies=None, data=None):
        try:
            response = self.requester.post(url, timeout=timeout, headers=headers, cookies=cookies, data=data)
            response.raise_for_status()

            return response
        except ConnectionError:
            raise ConnectionError()
        except HTTPError:
            raise HTTPError
