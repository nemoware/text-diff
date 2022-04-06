import difflib
import logging
import re
from nltk.tokenize import WhitespaceTokenizer


def wrapper(parser_response):
    document = parser_response[0]
    document = clean_text(document)
    document = subparagraph_format(document)
    document, price = define_attributes(document)
    document = check_warranty_periods(document)
    document, obj = check_fines(document, price)
    return document


def clean_text(document):
    for paragraph in document.get('paragraphs', []):
        paragraph['paragraphHeader']['text'] = paragraph['paragraphHeader']['text'].strip()
        paragraph['paragraphBody']['text'] = paragraph['paragraphBody']['text'].strip()
    return document


def subparagraph_format(document):
    regex = re.compile(r'(\d+\.\d+\.(\d+\.|)\s)', re.S)
    for index, paragraph in enumerate(document.get('paragraphs', [])):
        document['paragraphs'][index]['paragraphBody']['text'] = regex.sub(
            lambda m: "\n" + m.group() + "\n",
            paragraph['paragraphBody']['text']
        )

    return document


def define_attributes(document):
    keys: [[str]] = [
        ['казенное учреждение комбинат', 'Управления Федерального агентства'],
        ['государственным резервам по', 'федеральному округу, именуем'],
        [', с одной стороны, и', ', именуем'],
        [r'полный комплекс работ по строительству объекта \(далее – «работы»\):',
         r'\(далее – «Объект»\) в соответствии с проектной документацией,'],
        ['Место выполнения работ:', '.'],
        ['Цена Государственного контракта составляет', ', включая НДС по ставке']
    ]
    price: int = 0
    for index, paragraph in enumerate([0, 0, 0, 1, 1, 3]):
        phrase = re.search(
            f'{keys[index][0]}(.*){keys[index][1]}',
            document['paragraphs'][paragraph]['paragraphBody']['text']
        )

        if phrase is None:
            print('doesn`t find')
            return
        change_phrase = phrase.group(0).replace(
            phrase.group(1),
            ' <div style="background-color:lightgreen;display: inline;">' +
            phrase.group(1).strip() +
            '</div> '
        )
        if paragraph == 3:
            price_in_str = re.search(r'(\d+)', ''.join(phrase.group(1).strip().split()))
            if price_in_str:
                price = int(price_in_str.group(0))

        document['paragraphs'][paragraph]['paragraphBody']['text'] = document['paragraphs'][paragraph]['paragraphBody'][
            'text'].replace(phrase.group(0), change_phrase)

    return document, price


def check_warranty_periods(document):
    start: str = 'срок исполнения таких обязательств не менее чем на'
    end: str = ', в том числе в случае его'

    phrase = re.search(
        f'{start}(.*){end}',
        document['paragraphs'][13]['paragraphBody']['text']
    )
    if phrase is None:
        logging.error("Not find date")
        return document
    date: str = phrase.group(1)

    bad: [str] = ['недел', 'дня', 'день']
    good: [str] = ['месяц', 'год', 'лет']
    flag: bool = False

    if any(word in date for word in bad):
        flag = False
    if any(word in date for word in good):
        flag = True

    color: str = 'lightgreen;' if flag else 'pink;'

    change_phrase = phrase.group(0).replace(
        phrase.group(1),
        f' <div style="background-color:{color};display: inline;">' +
        phrase.group(1).strip() +
        '</div> '
    )

    document['paragraphs'][13]['paragraphBody']['text'] = document['paragraphs'][13]['paragraphBody'][
        'text'].replace(phrase.group(0), change_phrase)

    return document


def check_fines(document, price: int = -1):
    if price == -1:
        return document, {'error': 'Не найдена сумма договора'}

    array_of_interval = [
        {
            'start': 0,
            'end': 3000000,
            'percent': 10
        },
        {
            'start': 3000000,
            'end': 50000000,
            'percent': 5
        },
        {
            'start': 50000000,
            'end': 100000000,
            'percent': 1
        },
        {
            'start': 100000000,
            'end': 500000000,
            'percent': 0.5
        },
        {
            'start': 500000000,
            'end': 1000000000,
            'percent': 0.4
        },
        {
            'start': 1000000000,
            'end': 2000000000,
            'percent': 0.3
        },
        {
            'start': 2000000000,
            'end': 5000000000,
            'percent': 0.25
        },
        {
            'start': 5000000000,
            'end': 10000000000,
            'percent': 0.2
        },
        {
            'start': 10000000000,
            'end': float('inf'),
            'percent': 0.1
        },
    ]
    percent = 0
    templates = {
        10: '\n <div style="background-color:lightgreen;display: inline;">10</div> процентов цены Государственного контракта (здесь и далее при необходимости: этапа), что составляет <div style="background-color:lightgreen;display: inline;">___ руб.</div> (в случае, если цена Контракта (здесь и далее при необходимости: этапа) не превышает 3 млн. рублей).\n',
        5: '\n <div style="background-color:lightgreen;display: inline;">5</div> процентов цены Государственного контракта, что составляет <div style="background-color:lightgreen;display: inline;">___ руб.</div> (в случае, если цена Контракта составляет от 3 млн. рублей до 50 млн. рублей (включительно).\n',
        1: '123 <div style="background-color:lightgreen;display: inline;">1</div> процент цены Государственного контракта, что составляет <div style="background-color:lightgreen;display: inline;">___ руб.</div> (в случае, если цена Контракта составляет от 50 млн. рублей до 100 млн. рублей (включительно).\n',
        0.5: '\n <div style="background-color:lightgreen;display: inline;">0,5</div> процента цены Государственного контракта, что составляет <div style="background-color:lightgreen;display: inline;">___ руб.</div> (в случае, если цена Контракта составляет от 100 млн. рублей до 500 млн. руб.(включительно).\n',
        0.4: '\n <div style="background-color:lightgreen;display: inline;">0,4</div> процента цены Государственного контракта, что составляет <div style="background-color:lightgreen;display: inline;">___ руб.</div> (в случае, если цена Контракта составляет от 500 млн. рублей до 1 млрд. руб. (включительно).\n',
        0.3: '\n <div style="background-color:lightgreen;display: inline;">0,3</div> процента цены Государственного контракта, что составляет <div style="background-color:lightgreen;display: inline;">___ руб.</div> (в случае, если цена Контракта составляет от 1 млрд. рублей до 2 млрд. руб.(включительно).\n',
        0.25: '\n<div style="background-color:lightgreen;display: inline;">0,25</div> процента цены Государственного контракта, что составляет <div style="background-color:lightgreen;display: inline;">__ руб.</div> (в случае, если цена Контракта составляет от 2 млрд. рублей до 5 млрд. руб.(включительно).\n',
        0.2: '\n <div style="background-color:lightgreen;display: inline;">0,2</div> процента цены Государственного контракта, что составляет <div style="background-color:lightgreen;display: inline;">___ руб.</div> (в случае, если цена Контракта составляет от 5 млрд. рублей до 10 млрд. руб.(включительно).\n',
        0.1: '\n <div style="background-color:lightgreen;display: inline;">0,1</div> процента цены Государственного контракта, что составляет <div style="background-color:lightgreen;display: inline;">___ руб.</div> (в случае, если цена Контракта превышает 10 млрд. рублей.\n'
    }
    fine = 0
    fine_from_doc = 0
    array_of_errors = []

    for interval in array_of_interval:
        if interval['start'] <= price < interval['end']:
            percent = interval['percent']
            fine = int((price * percent) / 100)
            break

    start: str = r'Государственного контракта, что составляет'
    end: str = r'руб. \(в случае, если цена Контракта составляет от'

    phrase = re.search(f'{start}(.*){end}', document['paragraphs'][21]['paragraphBody']['text'])

    if phrase is None:
        logging.error('Не найдена налог')
        array_of_errors.append({'error': 'Не найдена налог'})
    else:
        fine_from_doc = int(phrase.group(1).replace(' ', ''))

    if fine != fine_from_doc:
        logging.error('Налог не совпадает с суммой договора')
        array_of_errors.append({
            'error': 'Налог не совпадает с суммой договора',
            'fine': fine,
            'fine_from_doc': fine_from_doc
        })

    percent_from_doc = re.search(r'(\d+(,\d+|)) процент', document['paragraphs'][21]['paragraphBody']['text'])

    if percent_from_doc is None:
        logging.error('Не найдена процент')
        array_of_errors.append({'error': 'Не найдена процент'})
    else:
        percent_from_doc_int = int(percent_from_doc.group(1).strip())
        if percent == percent_from_doc_int:
            change_phrase = highlight(phrase, fine == fine_from_doc)
            change_percent = highlight(percent_from_doc)

            document['paragraphs'][21]['paragraphBody']['text'] = document['paragraphs'][21]['paragraphBody']['text'] \
                .replace(phrase.group(0), change_phrase).replace(percent_from_doc.group(0), change_percent)
        else:
            change_phrase = highlight(phrase, fine == fine_from_doc)
            change_percent = highlight(percent_from_doc, False)

            template = templates[percent].replace('___', str(fine))
            template = '\n'+template + "<br>" + change_percent

            document['paragraphs'][21]['paragraphBody']['text'] = document['paragraphs'][21]['paragraphBody']['text'] \
                .replace(phrase.group(0), change_phrase) \
                .replace(percent_from_doc.group(0), template) \
                .replace('15.2.2.', '\n15.2.2.')

    return document, {
        'price': price,
        'fine': fine_from_doc,
        'errors': array_of_errors
    }


def highlight(phrase, good: bool = True):
    return phrase.group(0).replace(
        phrase.group(1),
        f' <div style="background-color:{"lightgreen" if good else "pink"};display: inline;">' +
        phrase.group(1).strip() +
        '</div> '
    )
