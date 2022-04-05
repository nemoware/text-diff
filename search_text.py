import difflib
import re
import string
from json import JSONDecodeError

import base64
import json
import requests
import streamlit as st
from nltk.tokenize import WhitespaceTokenizer


def wrapper(parser_response):
    document = parser_response[0]
    document = clean_text(document)
    document = subparagraph_format(document)
    document = define_attributes(document)
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


def define_attributes2(document):
    template_text = 'Федеральное государственное казенное учреждение комбинат «_________________» Управления ' \
                    'Федерального ' \
                    'агентства по государственным резервам по ___________________ федеральному округу, именуемое в ' \
                    'дальнейшем ' \
                    '«Заказчик», в лице директора, действующего на основании _______________, с одной стороны, ' \
                    'и ____________________________________________, именуем__'
    key = 'в дальнейшем «Генеральный подрядчик»'

    span_generator = WhitespaceTokenizer().span_tokenize(template_text)
    spans_template_document = [template_text[span[0]:span[1]] for span in span_generator]

    first_paragraph: str = document['paragraphs'][0]['paragraphBody']['text']
    # split_first_paragraph: str = ''.join(first_paragraph.split(key)[0].split('Федеральное', 1))
    split_first_paragraph: str = first_paragraph.split(key)[0]

    span_generator = WhitespaceTokenizer().span_tokenize(split_first_paragraph)
    spans_document = [first_paragraph[span[0]:span[1]] for span in span_generator]

    # print(split_first_paragraph)
    # print(spans_template_document)
    # print(spans_document)
    diffs = difflib.unified_diff(spans_template_document, spans_document)

    pass


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
            price = int(price_in_str.group(0))
            print(price)

        document['paragraphs'][paragraph]['paragraphBody']['text'] = document['paragraphs'][paragraph]['paragraphBody'][
            'text'].replace(phrase.group(0), change_phrase)

    return document
