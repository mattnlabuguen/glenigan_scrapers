from PyPDF2 import PdfReader

from base.parser import ParsingStrategy
from base.logger import Logger

class WandsworthGovUkParsingStrategy(ParsingStrategy):
    def __init__(self):
        self.logger = Logger(self.__class__.__name__).logger


    def parse(self):
        pass