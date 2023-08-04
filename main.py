import importlib
import json
import urllib3

urllib3.disable_warnings()


def get_crawling_strategy(website_name: str):
    file_name = None
    with open("map.json", "r") as file:
        mapping = json.load(file)
        file_name = mapping[website_name]

    module = importlib.import_module(f'crawler.{file_name}')
    class_name = f"{''.join([element.capitalize() for element in file_name.split('_')])}CrawlingStrategy"
    crawling_strategy = getattr(module, class_name)

    return crawling_strategy


if __name__ == '__main__':
    country = 'uk'
    website = 'planning.wandsworth.gov.uk'

    crawler = get_crawling_strategy(website)()
    crawler.crawl()
