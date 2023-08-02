from abc import abstractmethod, ABC

class DownloadStrategy(ABC):
    @abstractmethod
    def download(self, url, timeout=10, headers=None, cookies=None, data=None) -> str:
        pass

    @abstractmethod
    def crawl(self):
        pass