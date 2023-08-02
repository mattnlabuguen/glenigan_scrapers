from PyPDF2 import PdfReader

from base.parser import ParsingStrategy
from base.logging import Logging

class WandsworthGovUkParsingStrategy(ParsingStrategy):
    def __init__(self):
        self.logger = Logging(self.__class__.__name__).logger


    def parse(self):
        pass