import os
import time
from csv import DictWriter
from random import randint

from selenium.common.exceptions import (NoSuchElementException, ElementClickInterceptedException,
                                        ElementNotInteractableException)
from selenium.webdriver import Chrome  # for annotation
from selenium.webdriver.common.by import By


from constants import *
from exceptions import *
from utils import get_driver, get_data, calculate_vol, calculate_dif


def auth(driver: Chrome, login: str, password: str):
    login_url = os.getenv('login_url')
    if not login_url:
        raise MissingDotenvData('В переменных среды отсутствует login_url')
    driver.get(login_url)
    for input_name, verbose_name, value in [('email', 'логина', login), ('password', 'пароля', password)]:
        try:
            field = driver.find_element(By.XPATH, f'//input[@name="{input_name}"]')
        except NoSuchElementException:
            raise AuthorizationFailedException(f'Не удалось найти поле для ввода {verbose_name}')
        for s in value:
            field.send_keys(s)
            time.sleep(float(f'0.1{randint(0, 9)}'))
    try:
        driver.find_element(By.XPATH, '//button[@type="submit"]').click()
    except (NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException) as e:
        raise AuthorizationFailedException(f'Не удалось нажать на кнопку авторизации [{e.__class__.__name__}]')


def parse(countries: list, row_limit: int, temp_folder: str = 'temp',
          phrases_text_filename: str = 'phrases.txt'):
    third_party_source = False
    driver = get_driver(os.path.abspath(temp_folder))
    with open(os.getenv('credentials_filename'), encoding='utf-8') as f:
        lines = [x.strip() for x in f.readlines()]
        if len(lines) > 1:
            third_party_source = True
            login_url, base_url = lines
        else:
            base_url = os.getenv('base_url')
        try:
            login, password = lines[0].split(':')
        except ValueError:
            raise InvalidFileData(f'Неверный формат данных в {os.getenv("credentials_filename")}')
    if not third_party_source:
        auth(driver, login, password)
        time.sleep(AUTH_TIMEOUT)
        if driver.current_url == os.getenv('login_url'):
            auth(driver, login, password)
    else:
        driver.get(login_url)
        print('Ожидание авторизации пользователем...')
        while driver.current_url == login_url:
            pass
    print('Авторизация прошла успешно...')
    url = f'{base_url.rstrip("/")}/keywords-explorer'
    output_filename = os.getenv('output_filename', 'output.csv')
    total_count = len(countries)
    with open(output_filename, 'w', newline='', encoding='utf-8') as f:
        writer = DictWriter(f, EXPORT_KEYS, delimiter=';')
        writer.writeheader()
    output = []
    for i, country in enumerate(countries, 1):
        raw_data = get_data(driver, url, country, row_limit, phrases_text_filename)
        data, pairs = [], []
        for row in raw_data:
            if (row['Keyword'], row['Country']) not in pairs:
                data.append(row)
                pairs.append((row['Keyword'], row['Country']))
        with open(output_filename, 'a', newline='', encoding='utf-8') as f:
            writer = DictWriter(f, EXPORT_KEYS, delimiter=';')
            writer.writerows(data)
        output += data
        print(f'[{i}/{total_count}] {country}: {len(data)} rows')
        time.sleep(float(f'{randint(1, 5)}.{randint(0, 9)}'))
    driver.close()
    return output, output_filename


def process_data(data: list, filename: str, countries: dict, phrases: list, vol_k: float, dif_k: float):
    processed_filename = f'{".".join(filename.split(".")[:-1])}_processed.csv'
    output = dict()
    length = len(phrases)
    for i, ph in enumerate(phrases):
        row = {'Запрос': ph['Запрос']}
        results = [d for d in data if d['Keyword'].lower() == ph['Запрос'].lower()]
        true_res = [x['Difficulty'] for x in results if x['Difficulty'] is not None]
        max_dif = max(true_res) if true_res else 0
        max_vols = dict()
        for country in countries:
            true_res = [int(x['Volume']) for x in data if x['Country'] == country
                        and x['Volume'] != '' and x['Volume'] is not None]
            if country not in max_vols:
                max_vols[country] = max(true_res) if true_res else 0
            for d in results:
                if d['Country'] == country and d['Volume'] is not None:
                    row[f'Volume_{country}'] = 1 if 1 <= d['Volume'] <= 10 else d['Volume']
                    break
            else:
                row[f'Volume_{country}'] = 0
        for country in countries:
            for d in results:
                if d['Country'] == country and d['Difficulty'] is not None:
                    row[f'Difficulty_{country}'] = d['Difficulty']
                    break
            else:
                row[f'Difficulty_{country}'] = max_dif
        row = {**row, **{f'Score_{country}': (vol_k * calculate_vol(row[f'Volume_{country}'], max_vols[country]) *
                                              dif_k * calculate_dif(row[f'Difficulty_{country}']))
                         for country in countries}}
        row['Total_Score'] = sum(val * row[f'Score_{key}'] for key, val in countries.items())
        if i == 0:
            with open(processed_filename, 'w', newline='', encoding='utf-8') as f:
                writer = DictWriter(f, list(row.keys()), delimiter=';')
                writer.writeheader()
        with open(processed_filename, 'a', newline='', encoding='utf-8') as f:
            writer = DictWriter(f, list(row.keys()), delimiter=';')
            cur_row = row.copy()
            for key in 'Volume', 'Difficulty', 'Score':
                for country in countries:
                    cur_row[f'{key}_{country}'] = str(row[f'{key}_{country}']).replace('.', ',')
            cur_row['Total_Score'] = str(row['Total_Score']).replace('.', ',')
            writer.writerow(cur_row)
        output[ph['Название']] = output.get(ph['Название'], []) + [row]
        if (i + 1) % 100 == 0:
            print(f'{i + 1}/{length}')
    pivot_filename = f'{".".join(filename.split(".")[:-1])}_pivot.csv'
    for i, items in enumerate(output.items()):
        key, queries = items
        fieldnames = ['Название'] + list(queries[0].keys())[1:]
        if i == 0:
            with open(pivot_filename, 'w', newline='', encoding='utf-8') as f:
                writer = DictWriter(f, fieldnames, delimiter=';')
                writer.writeheader()
        row = {'Название': key, **{field: (max if 'Difficulty' in field else sum)(q[field] for q in queries)
                                   for field in fieldnames[1:]}}
        with open(pivot_filename, 'a', newline='', encoding='utf-8') as f:
            cur_row = row.copy()
            for key in 'Volume', 'Difficulty', 'Score':
                for country in countries:
                    cur_row[f'{key}_{country}'] = str(row[f'{key}_{country}']).replace('.', ',')
            cur_row['Total_Score'] = str(row['Total_Score']).replace('.', ',')
            writer = DictWriter(f, fieldnames, delimiter=';')
            writer.writerow(cur_row)
    print('\nOK')