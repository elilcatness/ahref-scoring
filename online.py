import os
from dotenv import load_dotenv
from shutil import rmtree

from general import parse, process_data
from utils import retrieve_countries, retrieve_phrases


def main(row_limit: int = 5000):
    temp_folder = os.getenv('temp_folder', 'temp')
    if os.path.exists(temp_folder):
        if input(f'Папка {temp_folder} будет перезаписана. Продолжить? (y\\n) ').lower() != 'y':
            return
        rmtree(temp_folder)
    os.mkdir(temp_folder)
    vol_k, dif_k = map(float, input('Введите коэффициенты Volume и Difficulty через пробел '
                                    '(если число вещественное, то дробную часть записывать через "."):\n').split())
    row_answer = input(f'Введите лимит строк (по умолчанию - {row_limit}, для сего значения нажмите Enter): ')
    if row_answer:
        try:
            row_limit = int(row_answer)
        except ValueError:
            raise ValueError('Неверный формат числа строк')
    countries = {c['Страна']: float(c['Коэффициент']) for c in retrieve_countries(os.getenv('countries_filename'))}
    phrases = retrieve_phrases(os.getenv('phrases_filename'))
    phrases_text_filename = '.'.join(os.getenv('phrases_filename').split('.')[:-1]) + '.txt'
    with open(phrases_text_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join([ph['Запрос'] for ph in phrases]))
    data, filename = parse(list(countries.keys()), row_limit, temp_folder, phrases_text_filename)
    process_data(data, filename, countries, phrases, vol_k, dif_k)


if __name__ == '__main__':
    load_dotenv()
    main()