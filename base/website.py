from abc import ABC, abstractmethod

class WebsiteStrategy(ABC):
    @abstractmethod
    def extract(self, raw_data):
        pass