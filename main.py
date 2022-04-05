import difflib
import re
import string
from json import JSONDecodeError

import base64
import json
import requests
import streamlit as st
from nltk.tokenize import WhitespaceTokenizer
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


def get_tokens(text: str) -> []:
    span_generator = WhitespaceTokenizer().span_tokenize(text)
    spans = [text[span[0]:span[1]] for span in span_generator]
    # print(spans)
    return spans


def convert_to_text(json_from_parser):
    result = ""
    for doc in json_from_parser:
        for paragraph in doc.get('paragraphs', []):
            result += paragraph['paragraphHeader']['text'] + ' '
            result += paragraph['paragraphBody']['text'] + ' '
    return get_tokens(result)


def compare(parser_result, etalon):
    result = []
    st.session_state.debug = etalon
    if len(parser_result) > 0:
        st.session_state.document_type = parser_result[0]['documentType']
        text = convert_to_text(parser_result)
        etalon_text = convert_to_text(etalon)
        diffs = difflib.unified_diff(etalon_text, text)
        new_diff = None
        for diff in diffs:
            m = re.search(r'@@.*\+(\d+),(\d+).*@@', diff)
            if m:
                new_diff = {'start': int(m.group(1)) - 1, 'length': 0, 'text': []}
                result.append(new_diff)
                start_diff = False
            elif (diff.startswith('-') or diff.startswith('+')) and new_diff:
                new_diff['text'].append(diff)
                start_diff = True
                new_diff['length'] += 1
            elif diff.startswith(' ') and not start_diff:
                new_diff['start'] += 1
    # print(result)
    return result


def escape_markdown(text: str) -> str:
    parse = re.sub(r"([_*\[\]()~`>\#\+\-=|\.!])", r"\\\1", text)
    reparse = re.sub(r"\\\\([_*\[\]()~`>\#\+\-=|\.!])", r"\1", parse)
    return reparse


def highlight_result(tokens: [str], token_count: int, diff, tokens_to_remove: int, escape=True):
    result = ''
    for idx, word in enumerate(tokens):
        if len(diff) > 0:
            div_closed = True
            if diff[0]['start'] <= token_count + idx <= diff[0]['start'] + diff[0]['length']:
                diff_part = 0
                sign = ''
                for diff_idx, diff_token in enumerate(diff[0]['text']):
                    if sign == '+' and len(tokens) == idx + diff_idx:
                        diff_part = diff_idx
                        break
                    if diff_token.startswith('-'):
                        if sign != '-':
                            if not div_closed:
                                result += '</div>'
                            result += '<div style="background-color:red;display: inline;">'
                            sign = '-'
                            div_closed = False
                        if escape:
                            result += escape_markdown(diff_token[1:] + ' ')
                        else:
                            result += diff_token[1:] + ' '
                    if diff_token.startswith('+'):
                        if sign != '+':
                            if not div_closed:
                                result += '</div>'
                            result += '<div style="background-color:green;display: inline;">'
                            sign = '+'
                            div_closed = False
                        if escape:
                            result += escape_markdown(diff_token[1:] + ' ')
                        else:
                            result += diff_token[1:] + ' '
                        tokens_to_remove += 1
                if not div_closed:
                    result += '</div>'
                if diff_part == 0:
                    diff.pop(0)
                else:
                    diff[0]['text'] = diff[0]['text'][diff_part:]
                    if sign == '+':
                        return result, tokens_to_remove
        if tokens_to_remove > 0:
            tokens_to_remove -= 1
            continue
        result += escape_markdown(word + ' ')
    return result, tokens_to_remove


def highlight_removed(token_count, diff) -> str:
    result = ''
    if len(diff) > 0:
        div_closed = True
        if diff[0]['start'] <= token_count <= diff[0]['start'] + diff[0]['length']:
            diff_part = 0
            sign = ''
            for diff_idx, diff_token in enumerate(diff[0]['text']):
                # if len(tokens) == diff_idx:
                #     diff_part = diff_idx
                #     break
                if diff_token.startswith('-'):
                    if sign != '-':
                        if not div_closed:
                            result += '</div>'
                        result += '<div style="background-color:red;display: inline;">'
                        sign = '-'
                        div_closed = False
                    result += diff_token[1:] + ' '
                if diff_token.startswith('+'):
                    break
                #     if sign != '+':
                #         if not div_closed:
                #             result += '</div>'
                #         result += '<div style="background-color:green;display: inline;">'
                #         sign = '+'
                #         div_closed = False
                #     result += diff_token[1:] + ' '
            if not div_closed:
                result += '</div>'
            if diff_part == 0:
                diff.pop(0)
            else:
                diff[0]['text'] = diff[0]['text'][diff_part:]
    return result


for key in ['result_btn', 'start_btn', 'uploader']:
    if key not in st.session_state:
        st.session_state[key] = False

for key in ['main_text', 'response', 'document_type', 'diff', 'document']:
    if key not in st.session_state:
        st.session_state[key] = ""

st.set_page_config(layout="wide")

col1, col2 = st.columns([1, 3])

uploader = col1.file_uploader("Выберите файл", ["doc", "docx"])

container_btn = col1.container()
container = col2.container()
container_text = col2.container()
container_debug = col2.container()

if not server_activity_check():
    container_btn.error("Сервер выключен")

if uploader:
    with st.spinner(text="Обработка документа"), open(etalon_file_name, "rb") as etalon_file:
        from_parser_etalon = get_json_from_parser(etalon_file.read(), etalon_file_name)

        from_parser = get_json_from_parser(uploader.getvalue(), uploader.name)
        # container_text.write(from_parser)
        st.session_state.document = wrapper(from_parser)
        if from_parser != "" and from_parser is not None:
            st.session_state.diff = compare(from_parser, from_parser_etalon)
        else:
            col1.error("Ошибка при парсинге документа")

if st.session_state.document:
    col1.subheader("Тип документа")
    col1.markdown('##### ' + doc_type_translation[st.session_state.document_type])

    col1.subheader('Оглавление')
    for paragraph in st.session_state.document['paragraphs']:
        col1.write(escape_markdown(paragraph['paragraphHeader']['text']))

    container_text.header("Текст Документа")
    for paragraph in st.session_state.document['paragraphs']:
        container_text.markdown('#### ' + paragraph['paragraphHeader']['text'], unsafe_allow_html=True)
        container_text.markdown(paragraph['paragraphBody']['text'], unsafe_allow_html=True)

    # token_count = 0
    # tokens_to_remove = 0
    # for paragraph in st.session_state.document.get('paragraphs', []):
    #     if len(st.session_state.diff) > 0:
    #         diff = st.session_state.diff[0]
    #         if diff['start'] <= token_count <= diff['start'] + diff['length'] and diff['text'][0].startswith('-'):
    #             container_text.markdown(highlight_removed(token_count, st.session_state.diff), unsafe_allow_html=True)
    #
    #     paragraphHeader = paragraph['paragraphHeader']
    #     tokens = get_tokens(paragraphHeader['text'])
    #     highlighted_text, tokens_to_remove = highlight_result(tokens, token_count, st.session_state.diff,
    #                                                           tokens_to_remove)
    #     container_text.markdown('#### ' + highlighted_text, unsafe_allow_html=True)
    #     token_count += len(tokens)
    #     paragraphBody = paragraph['paragraphBody']
    #     tokens = get_tokens(paragraphBody['text'])
    #     highlighted_text, tokens_to_remove = highlight_result(tokens, token_count, st.session_state.diff,
    #                                                           tokens_to_remove, False)
    #     container_text.markdown(highlighted_text, unsafe_allow_html=True)
    #     token_count += len(tokens)
