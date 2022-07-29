import os
import time
from csv import DictReader
from selenium.webdriver import Chrome, ChromeOptions, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as exp_cond
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

from exceptions import FileIsEmptyException
from constants import PHRASES_FIELDNAMES, LOAD_TIMEOUT, ERROR_FILENAME, EXPORT_KEYS, COUNTRIES_FIELDNAMES, \
    ROWS_LOAD_TIMEOUT


def get_driver(download_folder: str = '/temp/'):
    options = ChromeOptions()
    options.add_argument('--log-level=3')
    options.add_experimental_option('prefs', {'download.default_directory': download_folder})
    # options.add_argument('--headless')
    return Chrome(options=options)


def assert_file_data(filename: str, data):
    if not data:
        raise FileIsEmptyException(f'Файл {filename} пуст')
    return data


def assert_count_rows(filename, count):
    with open(filename, encoding='utf-8') as f:
        length = len(f.readlines()) - 1
        scale = int(count) * 0.99 if int(count) * 0.99 >= 1 else count - 1
        return True if scale <= length <= count else False


def retrieve_phrases(filename: str, delimiter: str = ';'):
    with open(filename, encoding='utf-8') as f:
        return assert_file_data(filename, list(DictReader(f, PHRASES_FIELDNAMES, delimiter=delimiter))[1:])


def retrieve_countries(filename: str, delimiter: str = ';'):
    with open(filename, encoding='utf-8') as f:
        return assert_file_data(filename, list(DictReader(f, COUNTRIES_FIELDNAMES, delimiter=delimiter))[1:])


def handle_exception(driver: Chrome, exception_cls, text: str, error_pic_filename: str):
    driver.save_screenshot(error_pic_filename)
    return exception_cls(f'{text} (см. {error_pic_filename})')


def get_export_rows_count(driver: Chrome):
    try:
        rows_count_block = WebDriverWait(driver, ROWS_LOAD_TIMEOUT).until(
            exp_cond.presence_of_element_located((
                By.XPATH, '//span[@class="css-a5m6co-text css-p8ym46-fontFamily '
                          'css-1wmho6b-fontWeight css-18j1nfb-display"]')))
    except TimeoutException:
        raise handle_exception(driver, TimeoutException, 'Не удалось получить количество строчек', ERROR_FILENAME)
    return int(''.join(rows_count_block.text.strip().split()[0].split(',')))


def export(driver: Chrome, row_limit: int):
    rows_count = get_export_rows_count(driver)
    try:
        export_btn = WebDriverWait(driver, LOAD_TIMEOUT).until(
            exp_cond.presence_of_element_located((
                By.XPATH, '//button[@class="css-15qe8gh-button css-ykx4dy-buttonFocus '
                          'css-1emi1z8-buttonWidth css-15kjecu-buttonHeight css-q66qvq-buttonCursor"]')))
    except TimeoutException:
        raise handle_exception(driver, TimeoutException,
                               'Не удалось найти кнопку экспорта', ERROR_FILENAME)
    ActionChains(driver).move_by_offset(10, 20).perform()
    start_time = time.time()
    while time.time() - start_time <= LOAD_TIMEOUT:
        try:
            export_btn.click()
            break
        except ElementClickInterceptedException:
            pass
    else:
        raise handle_exception(driver, TimeoutException, 'Не удалось нажать на кнопку экспорта', ERROR_FILENAME)
    try:
        input_fields = WebDriverWait(driver, LOAD_TIMEOUT).until(
            exp_cond.presence_of_all_elements_located((By.XPATH, '//input[@name="export-encoding-options"]/..')))
    except TimeoutException:
        raise handle_exception(driver, TimeoutException,
                               'Не удалось установить кодировку при экспорте', ERROR_FILENAME)
    input_fields[-1].click()
    try:
        row_fields = WebDriverWait(driver, LOAD_TIMEOUT).until(
            exp_cond.presence_of_all_elements_located((By.XPATH, '//input[@name="export-number-of-rows"]/..')))
    except TimeoutException:
        raise handle_exception(driver, TimeoutException,
                               'Не удалось установить количество строчек при экспорте', ERROR_FILENAME)
    more_iterations = False
    if len(row_fields) == 3:
        conflict_field = row_fields[1]
        if '(' in conflict_field.text and ')' in conflict_field.text:
            more_iterations = True
            rows_count = row_limit
        conflict_field.click()
    try:
        download_btn = WebDriverWait(driver, LOAD_TIMEOUT).until(
            exp_cond.presence_of_element_located(
                (By.XPATH, '//button[@class="css-15qe8gh-button css-1i73y9f-buttonFocus '
                           'css-1emi1z8-buttonWidth css-15kjecu-buttonHeight css-q66qvq-buttonCursor"]')))
    except TimeoutException:
        raise handle_exception(driver, TimeoutException,
                               'Не удалось произвести экспорт', ERROR_FILENAME)
    download_btn.click()
    old_temp_files = set(os.listdir(os.path.join('temp')))
    while True:
        try:
            new_temp_files = set(os.listdir(os.path.join('temp')))
            if len(new_temp_files) != len(old_temp_files):
                difference = new_temp_files.difference(old_temp_files).pop()
                if (not difference.endswith('.tmp') and not difference.endswith('.crdownload')
                    and os.path.getsize(os.path.join('temp', difference))) \
                        and (assert_count_rows(os.path.join('temp', difference), rows_count)):
                    return os.path.join('temp', difference), more_iterations
        except PermissionError:
            continue


def get_data(driver: Chrome, url: str, country: str, row_limit: int, phrases_text_filename: str):
    data = []
    driver.get(url)
    try:
        btn = WebDriverWait(driver, LOAD_TIMEOUT).until(
            exp_cond.presence_of_element_located((
                By.XPATH, '//div[@class="css-1m3jbw6-dropdown css-mkifqh-dropdownMenuWidth '
                          'css-1sspey-dropdownWithControl"]'
                          '/button[@class="css-15qe8gh-button css-ykx4dy-buttonFocus '
                          'css-1g8qvce-buttonWidth css-15kjecu-buttonHeight '
                          'css-q66qvq-buttonCursor"]')))
    except TimeoutException:
        raise handle_exception(driver, TimeoutException,
                               'Не удалось нажать кнопку выпадающего меню стран', ERROR_FILENAME)
    btn.click()
    try:
        input_field = WebDriverWait(driver, LOAD_TIMEOUT).until(
            exp_cond.presence_of_element_located((
                By.XPATH, '//input[@class="css-19vgjhp-input css-ke2x6i-inputNoBorder css-ocd83c-inputNoPadding '
                          'css-1e2o21f-inputColor css-lvmapq-inputBorderRadius '
                          'css-oamlhg-sm css-1o5fyf7-mainFontSize"]'
            )))
        input_field.send_keys(country.lower())
    except TimeoutException:
        raise handle_exception(driver, TimeoutException,
                               'Не удалось произвести действия над полем для ввода страны', ERROR_FILENAME)
    try:
        country_block = WebDriverWait(driver, LOAD_TIMEOUT).until(
            exp_cond.presence_of_element_located((
                By.XPATH, '//div[@class="css-kt22mo-dropdownBaseMenu css-6vm5e4-countrySelectInnerMenu"]'
                          '/div[@class="css-yufi00-dropdownItem"]'
            )))
    except TimeoutException:
        try:
            country_block = WebDriverWait(driver, LOAD_TIMEOUT).until(
                exp_cond.presence_of_element_located((
                    By.XPATH, '//div[@class="css-kt22mo-dropdownBaseMenu css-6vm5e4-countrySelectInnerMenu"]'
                              '//div[@class="css-yufi00-dropdownItem css-15h7oaf-dropdownItemSelected"]'
                )))
        except TimeoutException:
            raise handle_exception(driver, TimeoutException,
                                   f'Не удалось найти в выпадающем меню страну {country}', ERROR_FILENAME)
    if country_block.text.strip().lower() != country.lower():
        raise handle_exception(driver, TimeoutException,
                               f'Не удалось выбрать из выпадающего меню страну {country}', ERROR_FILENAME)
    country_block.click()
    # Sending file to the text area
    try:
        file_input = WebDriverWait(driver, LOAD_TIMEOUT).until(
            exp_cond.presence_of_element_located((By.XPATH, '//input[@class="css-1ew8z33-input"]')))
    except TimeoutException:
        raise handle_exception(driver, TimeoutException,
                               'Не удалось записать запросы в поле для ввода', ERROR_FILENAME)
    file_input.send_keys(os.path.abspath(phrases_text_filename))
    # Search button clicking
    try:
        search_btn = WebDriverWait(driver, LOAD_TIMEOUT).until(
            exp_cond.presence_of_element_located((
                By.XPATH, '//button[@class="css-15qe8gh-button css-1i73y9f-buttonFocus '
                          'css-1tdldg1-buttonWidth css-15kjecu-buttonHeight css-q66qvq-buttonCursor"]')))
    except TimeoutException:
        raise handle_exception(driver, TimeoutException,
                               'Не удалось найти кнопку поиска', ERROR_FILENAME)
    search_btn.click()
    export_filename, more_iterations = export(driver, row_limit)
    if more_iterations:
        with open(phrases_text_filename, encoding='utf-8') as f:
            phrases = [x.strip() for x in f.readlines()[row_limit:]]
        cropped_filename = ('.'.join(phrases_text_filename.split('.')[:-1]) + (
            '_cropped.txt' if not phrases_text_filename.endswith('_cropped.txt') else ''))
        with open(cropped_filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(phrases))
        data += get_data(driver, url, country, row_limit, cropped_filename)
    with open(export_filename, encoding='utf-8') as f:
        fieldnames = [x.strip() for x in f.readline().strip().split(',')]
        reader = DictReader(f, fieldnames, delimiter=',')
        data += [{'Keyword': d['Keyword'], 'Country': country,
                  'Difficulty': int(d['Difficulty']) if d['Difficulty'] else None,
                  'Volume': int(d['Volume']) if d['Volume'] else None} for d in reader]
    return data


def calculate_vol(vol, max_vol):
    return vol / max_vol * 100 if max_vol != 0 else 0


def calculate_dif(dif):
    return 100 - dif