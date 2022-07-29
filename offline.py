import os
from csv import DictWriter, DictReader

from dotenv import load_dotenv

from utils import retrieve_countries, retrieve_phrases
from general import process_data
from constants import EXPORT_KEYS, COUNTRIES_CODES


def main():
    countries = {c['Страна']: float(c['Коэффициент']) for c in retrieve_countries(os.getenv('countries_filename'))}
    phrases = retrieve_phrases(os.getenv('phrases_filename'))
    phrases_text_filename = '.'.join(os.getenv('phrases_filename').split('.')[:-1]) + '.txt'
    with open(phrases_text_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join([ph['Запрос'] for ph in phrases]))
    output_filename = os.getenv('output_filename', 'output.csv')
    temp_folder = os.getenv('temp_folder', 'temp')
    files = os.listdir(temp_folder)
    if not files:
        return print(f'Папка {temp_folder} пуста')
    total_count = len(files)
    vol_k, dif_k = map(float, input('Введите коэффициенты Volume и Difficulty через пробел '
                                    '(если число вещественное, то дробную часть записывать через "."):\n').split())
    with open(output_filename, 'w', newline='', encoding='utf-8') as f:
        writer = DictWriter(f, EXPORT_KEYS, delimiter=';')
        writer.writeheader()
    data = []
    for i, filename in enumerate(files, 1):
        cur_data, pairs = [], []
        with open(os.path.join(temp_folder, filename), encoding='utf-8') as f:
            for d in DictReader(f, f.readline().strip().split(','), delimiter=','):
                if (d['Keyword'], d['Country']) not in pairs:
                    row = {'Keyword': d['Keyword'], 'Country': COUNTRIES_CODES.get(d['Country'], d['Country']),
                           'Difficulty': int(d['Difficulty']) if d['Difficulty'] else None,
                           'Volume': int(d['Volume']) if d['Volume'] else None}
                    cur_data.append(row)
                    pairs.append((row['Keyword'], row['Country']))
        with open(output_filename, 'a', newline='', encoding='utf-8') as f:
            writer = DictWriter(f, EXPORT_KEYS, delimiter=';')
            writer.writerows(cur_data)
        data += cur_data
        print(f'[{i}/{total_count}] {filename}: {len(data)} rows')
    process_data(data, output_filename, countries, phrases, vol_k, dif_k)


if __name__ == '__main__':
    load_dotenv()
    main()