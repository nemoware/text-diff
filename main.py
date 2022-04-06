import re
import time
from json import JSONDecodeError

import base64
import json
import requests
import streamlit as st
from search_text import clean_text, wrapper

parser_url = 'http://127.0.0.1:8889'
etalon_file_name = 'etalon.docx'

doc_type_translation = {
    'UNKNOWN': 'Входящий документ',
    'CONTRACT': 'Договор',
    'CHARTER': 'Устав',
    'PROTOCOL': 'Протокол',
    'REGULATION': 'Положение',
    'CHARITY_POLICY': 'Политика благотворительности',
    'ORDER': 'Приказ',
    'WORK_PLAN': 'План работ',
    'SUPPLEMENTARY_AGREEMENT': 'Дополнительное соглашение',
    'ANNEX': 'Приложение',
    'AGREEMENT': 'Соглашение',
    'POWER_OF_ATTORNEY': 'Доверенность',
}


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


for key in ['result_btn', 'start_btn', 'uploader']:
    if key not in st.session_state:
        st.session_state[key] = False

for key in ['document_type', 'info', 'document', 'number_input']:
    if key not in st.session_state:
        st.session_state[key] = ""

st.set_page_config(layout="wide")

col1, col2 = st.columns([1, 3])

uploader = col1.file_uploader("Выберите файл", ["doc", "docx"])

container_btn = col1.container()
container = col1.container()
container_text = col2.container()

if not server_activity_check():
    container_btn.error("Сервер выключен")

if uploader:
    with st.spinner(text="Обработка документа"):
        from_parser = get_json_from_parser(uploader.getvalue(), uploader.name)
        st.session_state.document, st.session_state.info = wrapper(from_parser)
        # container_text.write(from_parser)
        container_text.header("Текст Документа")
        for paragraph in st.session_state.document['paragraphs']:
            container_text.markdown('#### ' + paragraph['paragraphHeader']['text'], unsafe_allow_html=True)
            container_text.markdown(paragraph['paragraphBody']['text'], unsafe_allow_html=True)

if st.session_state.info:
    container.subheader('Дополнительная информация')
    if st.session_state.info['price'] == 0:
        container.write('Сумма договора не указана, ПЖ! Укажи!11!!1')

    st.session_state.number_input = container.number_input(
        value=st.session_state.info['price'] if st.session_state.info else 0,
        label='Сумма договора, руб', step=1000
    )

    if st.session_state.info['fine'] != -1:
        container.write('Штраф = ' + str(st.session_state.info['fine']) + 'руб')
    container.write(int(st.session_state.number_input))

    if len(st.session_state.info['errors']) > 0:
        container.subheader('Найденные ошибки')
        for error in st.session_state.info['errors']:
            container.error(error['error'])
