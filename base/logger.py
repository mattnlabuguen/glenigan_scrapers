from datetime import datetime

import logging


class Logger:
    def __init__(self, class_name):
        self.logger = logging.getLogger(class_name)
        self.logger.setLevel(logging.DEBUG)

        # File handler to log messages to a file
        log_file = f"logs/{datetime.today().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Console handler to log messages to the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # Formatter for the handlers
        formatter = logging.Formatter('[%(asctime)s] - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add the handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
