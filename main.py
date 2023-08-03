import importlib
import json
import urllib3

urllib3.disable_warnings()


def get_download_strategy(website: str):
    file_name = None
    with open("map.json", "r") as file:
        mapping = json.load(file)
        file_name = mapping[website]

    module = importlib.import_module(f'download.{file_name}')
    class_name = f"{''.join([element.capitalize() for element in file_name.split('_')])}DownloadStrategy"
    download_strategy = getattr(module, class_name)

    return download_strategy


if __name__ == '__main__':
    country = 'uk'
    website = 'planning.wandsworth.gov.uk'

    downloader = get_download_strategy(website)()
    downloader.crawl()
