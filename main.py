import importlib
import json
import os
import pickle

import pandas as pd
import urllib3

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
    raw_data_file = 'output/raw_data.pkl'
    use_local_file = True
    # For testing specific URLs.
    urls = []

    crawler = get_crawling_strategy(website)()
    parser = get_parsing_strategy(website)()

    if os.path.exists(raw_data_file) and use_local_file:
        with open(raw_data_file, "rb") as pickle_file:
            raw_data_list = pickle.load(pickle_file)

    else:
        raw_data_list = crawler.crawl(urls)
        if not urls:
            with open(raw_data_file, "wb") as pickle_file:
                pickle.dump(raw_data_list, pickle_file)

    data_list = parser.parse(raw_data_list)
    df = pd.DataFrame(data_list)
    csv_file = 'output/output.csv'

    df.to_csv(csv_file, index=False)

    print(data_list)
