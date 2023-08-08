import importlib
import json
import urllib3
import pandas as pd

urllib3.disable_warnings()


def get_crawling_strategy(website_name: str):
    with open("map.json", "r") as file:
        mapping = json.load(file)
        file_name = mapping[website_name]

    module = importlib.import_module(f'crawler.{file_name}')
    class_name = f"{''.join([element.capitalize() for element in file_name.split('_')])}CrawlingStrategy"
    crawling_strategy = getattr(module, class_name)

    return crawling_strategy


def get_parsing_strategy(website_name: str):
    with open("map.json", "r") as file:
        mapping = json.load(file)
        file_name = mapping[website_name]

    module = importlib.import_module(f'parser.{file_name}')
    class_name = f"{''.join([element.capitalize() for element in file_name.split('_')])}ParsingStrategy"
    parsing_strategy = getattr(module, class_name)

    return parsing_strategy


if __name__ == '__main__':
    country = 'uk'
    website = 'planning.wandsworth.gov.uk'

    crawler = get_crawling_strategy(website)()
    parser = get_parsing_strategy(website)()

    raw_data_list = crawler.crawl()
    data_list = parser.parse(raw_data_list)

    df = pd.DataFrame(data_list)
    csv_file = 'output/output.csv'

    df.to_csv(csv_file, index=False)

    print(data_list)
