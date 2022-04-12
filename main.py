import logging
import re
import time
from json import JSONDecodeError
import copy
import base64
import json
import requests
import streamlit as st
from search_text import check_fines, wrapper, clean_text, subparagraph_format

# parser_url = 'http://127.0.0.1:8889'
parser_url = 'http://192.168.10.36:8889'
etalon_file_name = 'etalon.docx'


def get_json_from_parser(doc, filename):
    result = ""
    headers = {
        'Content-type': 'application/json',
        'Accept': 'application/json; text/plain'
    }
    try:
        # file = open(doc, 'rb')
        encoded_string = base64.b64encode(doc)
        encoded_string = str(encoded_string)[2:-1]
    except Exception as e:
        print(f"\nОшибка в файле {doc}")
        print(f"при конвертации в base64, исключение = {e}")
        print("=" * 200)
        return

    response = requests.post(
        parser_url + "/document-parser",
        data=json.dumps({
            "base64Content": encoded_string,
            "documentFileType": filename.split(".")[-1].upper()
        }),
        headers=headers
    )

    try:
        result = response.json()['documents']
    except Exception as e:
        print(f"\nОшибка в файле {doc}")
        print(f"Ответ от парсера {response.json()}")
        print(f"Исключение = {e}")
        print("=" * 200)
        return
    return result


def server_activity_check():
    headers = {
        'Content-type': 'application/json',
        'Accept': 'application/json; text/plain'
    }
    try:
        response = requests.get(
            parser_url + "/status",
            headers=headers
        )
        response_json = response.json()
        status = response_json['status']
        if status == 'ok':
            return True
    except JSONDecodeError:
        print('Decoding JSON has failed')
        return False
    except requests.exceptions.RequestException:
        print("Ошибка при запросе на сервер")
        return False
    return False


def escape_markdown(text: str) -> str:
    parse = re.sub(r"([_*\[\]()~`>\#\+\-=|\.!])", r"\\\1", text)
    reparse = re.sub(r"\\\\([_*\[\]()~`>\#\+\-=|\.!])", r"\1", parse)
    return reparse


for key in ['start_btn']:
    if key not in st.session_state:
        st.session_state[key] = False

for key in ['document', 'reserve_document', 'etalon_file']:
    if key not in st.session_state:
        st.session_state[key] = ""

for key in ['info']:
    if key not in st.session_state:
        st.session_state[key] = {}

for key in ['price', 'number_input']:
    if key not in st.session_state:
        st.session_state[key] = 0

st.set_page_config(layout="wide")

# col1, col2 = st.columns([1, 3])

st.markdown(f'''
    <style>
        section[data-testid="stSidebar"] .css-ng1t4o {{width: 40rem;}}
        section[data-testid="stSidebar"] .css-1d391kg {{width: 40rem;}}
    </style>
''', unsafe_allow_html=True)

uploader = st.sidebar.file_uploader("Выберите файл", ["doc", "docx"])

# container_btn = st.container()
# container = col1.container()
# container = st.sidebar()

container_text = st.container()
number_input = None
button = None

# if not server_activity_check():
#     container_btn.error("Сервер выключен")

if uploader and st.sidebar.button('Получить результат'):
    # col2.empty()
    container_text.empty()
    st.session_state.document = ""
    st.session_state.info = ""

    with st.spinner(text="Обработка документа"), open(etalon_file_name, "rb") as etalon_file:
        from_parser = get_json_from_parser(uploader.getvalue(), uploader.name)
        from_parser_etalon = get_json_from_parser(etalon_file.read(), etalon_file_name)
        st.session_state.etalon_file = copy.deepcopy(from_parser_etalon)
        st.session_state.start_btn = False
        st.session_state.document, st.session_state.info = wrapper(copy.deepcopy(from_parser),
                                                                   copy.deepcopy(from_parser_etalon))
        # container_text.write(from_parser_etalon)
        st.session_state.reserve_document = copy.deepcopy(from_parser)

        if st.session_state.info != {}:
            st.session_state.price = st.session_state.info['price']
        else:
            st.session_state.price = 0

if st.session_state.document:
    number_input = st.sidebar.number_input(
        label='Сумма договора, руб', min_value=0, step=1000, key='price'
    )
    button = st.sidebar.button('Задать сумму')

if number_input:
    st.session_state.number_input = number_input

if button and number_input > 0:
    # col2.empty()
    container_text.empty()
    st.session_state.document = ""
    st.session_state.info = ""
    # col1.write(st.session_state.reserve_document[0]['paragraphs'][21]['paragraphBody']['text'])
    st.session_state.document, st.session_state.info = wrapper(copy.deepcopy(st.session_state.reserve_document),
                                                               copy.deepcopy(st.session_state.etalon_file),
                                                               set_price=st.session_state.number_input)
    st.session_state.start_btn = True

if st.session_state.info:
    # if st.session_state.info['fine'] > 0:
    #     st.sidebar.write('Штраф = ' + str(st.session_state.info['fine']) + 'руб')
    # if st.session_state.info['fine_from_doc'] > 0:
    #     st.sidebar.write('Штраф найденный в документе = ' + str(st.session_state.info['fine_from_doc']) + 'руб')
    if st.session_state.info['price'] == 0:
        st.sidebar.subheader('Найденные ошибки')
        st.sidebar.error('Не найдена сумма договора')

    if len(st.session_state.info['errors']) > 0 and not st.session_state.start_btn:
        st.sidebar.subheader('Исправленные ошибки')
        for error in st.session_state.info['errors']:
            st.sidebar.error(error['error'])

    if len(st.session_state.info['template']) > 0:
        st.sidebar.subheader('Дополнительная информация')
        for additional_info in st.session_state.info['template']:
            st.sidebar.markdown(additional_info, unsafe_allow_html=True)

    st.sidebar.subheader('Пункты')
    flag = True
    st.sidebar.markdown(f'[Текст Документа](#top_text)')
    for index, paragraph in enumerate(st.session_state.document['paragraphs']):
        text = paragraph['paragraphHeader']['text']
        search = re.search(r'(\d+\. )', text)
        digit = re.search(r'(^5\.)', text)
        if digit:
            if flag:
                st.sidebar.markdown(f'[5. Права и обязанности Сторон](#5)')
            flag = False
            continue
        if search:
            st.sidebar.markdown(f'[{text}](#{search.group(0).replace(".", "")})')

if st.session_state.document:
    container_text.header("Текст Документа", "top_text")
    # container_text.markdown('## ' + "Текст Документа", unsafe_allow_html=True)
    for paragraph in st.session_state.document['paragraphs']:
        container_text.markdown('#### ' + paragraph['paragraphHeader']['text'], unsafe_allow_html=True)
        container_text.markdown(paragraph['paragraphBody']['text'], unsafe_allow_html=True)
