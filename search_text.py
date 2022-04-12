import logging
import re


def wrapper(parser_response, etalon, set_price: int = 0):
    document = parser_response[0]
    etalon_document = etalon[0]
    # etalon_document = clean_text(etalon_document)

    document = check_points(document, etalon_document)

    document = clean_text(document)
    document = subparagraph_format(document)
    document, price = define_attributes(document, set_price if set_price > 0 else -1)
    document = check_warranty_periods(document)
    document, info = check_fines(document, price if set_price <= 0 else set_price)
    document, info = fine_for_each_fact(document, price if set_price <= 0 else set_price, info)

    return document, info


def check_points(document, etalon):
    exclude = ['1.1.', '1.3.', '1.5.', '3.1.', '7.1.1.', '3.5.1.', '15.2.1.', '15.5.1.']
    list_of_bad_points = []
    for index, paragraph in enumerate(document['paragraphs'][:26]):
        paragraph_text_from_etalon = etalon['paragraphs'][index]['paragraphBody']['text']

        # regex: str = r'(\s+(?<!\.)\d+\.\d+\.(\d+\.|)\s+(.{10}))'
        # regex: str = r'((?<!\.)\d+\.\d+\.(\d+\.|)\s+)'
        # regex: str = r'((?<!п.)\s+(?<!\.)\d+\.\d+\.(\d+\.|)\s+)'

        regex_global: str = r'((?<!п\.)(\s+|^)(\d+\.\d+\.(\d+\.|))\s+(.{10}))'  # Эволюция выражения =D

        # regex: str = r'((?<!п.)\s+(?<!\.)(\d+\.\d+\.(\d+\.|))\s+(.*)(?<!п.)\s+(?<!\.)(\d+\.\d+\.(\d+\.|)))'
        # r'(?=((?<!п.)(\s+|)(?<!\.)(\d+\.\d+\.(\d+\.|))\s+(.*?)(?<!п.)\s+(?<!\.)(\d+\.\d+\.(\d+\.|))\s+))'
        # r'(?=((?<!п.)(\s+|\S|^)(?<!\.)(\d+\.\d+\.(\d+\.|))\s+(.*?)(?<!п.)(\S+|\s+)(?<!\.)(\d+\.\d+\.(\d+\.|))\s+))',
        # r'(?=((?<!п.)(\s+|^)(?<!\.)(\d+\.\d+\.(\d+\.|))\s+(.*?)(?<!п.)(\S+|\s+)(?<!\.)(\d+\.\d+\.(\d+\.|))\s+))',
        # r'(?=((?<!п.)(\s+|^)(?<!\.)(\d+\.\d+\.(\d+\.|))\s+(.*?)(?<!п.)(|\s+)(?<!\.)(\d+\.\d+\.(\d+\.|)|\.)\s+))',

        all_points_form_etalon = re.findall(regex_global, paragraph_text_from_etalon, re.S)
        for index1, etalon_text in enumerate(all_points_form_etalon):
            paragraph_text = document['paragraphs'][index]['paragraphBody']['text']
            all_points = re.findall(regex_global, paragraph_text, re.S)

            if etalon_text[0].strip() not in [x[0].strip() for x in all_points] and etalon_text[2] not in exclude:
                if index1 == 0:
                    print('first')
                    regex = fr'([\S\s]*)({all_points[index1][0]})'
                    good_paragraph = re.search(fr'(({etalon_text[0]})([\S\s]*))({all_points[index1][0]})',
                                               paragraph_text_from_etalon)
                    if etalon_text[2] == all_points[index1][2]:
                        regex = fr'([\S\s]*)({all_points[index1 + 1][0]})'
                        good_paragraph = re.search(fr'(({etalon_text[0]})([\S\s]*))({all_points[index1 + 1][0]})',
                                                   paragraph_text_from_etalon)
                        print(147)

                    bad_paragraph = re.search(regex, paragraph_text)
                    list_of_bad_points.append({
                        'good': good_paragraph.group(1),
                        'bad': highlight_text(good_paragraph.group(1)) + '<br>' + '<br>' + highlight_text(
                            bad_paragraph.group(1),
                            False)
                    })

                    document['paragraphs'][index]['paragraphBody']['text'] = \
                        str(document['paragraphs'][index]['paragraphBody']['text']) \
                            .replace(bad_paragraph.group(0), good_paragraph.group(1) + bad_paragraph.group(0))
                if 0 < index1 < len(all_points_form_etalon) - 1:
                    print('all')
                    regex2 = fr'(({all_points[index1 - 1][0]})([\S\s]*)){all_points[index1][0]}'

                    good_paragraph = re.search(fr'(({etalon_text[0]})([\S\s]*))({all_points[index1][0]})',
                                               paragraph_text_from_etalon)
                    if etalon_text[2] == all_points[index1][2]:
                        regex2 = fr'(({all_points[index1][0]})([\S\s]*))({all_points[index1 + 1][0]})'
                        good_paragraph = re.search(fr'(({etalon_text[0]})([\S\s]*))({all_points[index1 + 1][0]})',
                                                   paragraph_text_from_etalon)
                    bad_paragraph = re.search(regex2, paragraph_text)
                    if etalon_text[2] == all_points[index1][2]:
                        list_of_bad_points.append({
                            'good': bad_paragraph.group(1) + good_paragraph.group(1),
                            'bad': highlight_text(good_paragraph.group(1)) +
                                   highlight_text(bad_paragraph.group(1), False)
                        })
                        document['paragraphs'][index]['paragraphBody']['text'] = \
                            str(document['paragraphs'][index]['paragraphBody']['text']) \
                                .replace(bad_paragraph.group(1), bad_paragraph.group(1) + good_paragraph.group(1))
                    else:
                        list_of_bad_points.append({
                            'good': bad_paragraph.group(1) + good_paragraph.group(1),
                            'bad': bad_paragraph.group(1) + highlight_text(good_paragraph.group(1))
                        })

                        document['paragraphs'][index]['paragraphBody']['text'] = \
                            str(document['paragraphs'][index]['paragraphBody']['text']) \
                                .replace(bad_paragraph.group(1), bad_paragraph.group(1) + good_paragraph.group(1))

                if index1 == len(all_points_form_etalon) - 1:
                    print('Last')
                    good_paragraph = re.search(fr'(({etalon_text[0]})([\S\s]*))$', paragraph_text_from_etalon)
                    regex3 = fr'({all_points[index1 - 1][0]})([\S\s]*)$'

                    if index1 < len(all_points) and etalon_text[2] == all_points[index1][2]:
                        regex3 = fr'({all_points[index1][0]})([\S\s]*)$'
                        bad_paragraph = re.search(regex3, paragraph_text)

                        list_of_bad_points.append({
                            'good': good_paragraph.group(),
                            'bad': highlight_text(good_paragraph.group()) + highlight_text(bad_paragraph.group(), False)
                        })

                        document['paragraphs'][index]['paragraphBody']['text'] = \
                            str(document['paragraphs'][index]['paragraphBody']['text']) \
                                .replace(bad_paragraph.group(), good_paragraph.group())
                    else:
                        bad_paragraph = re.search(regex3, paragraph_text)
                        list_of_bad_points.append({
                            'good': bad_paragraph.group() + good_paragraph.group(),
                            'bad': bad_paragraph.group() + highlight_text(good_paragraph.group())
                        })

                        document['paragraphs'][index]['paragraphBody']['text'] = \
                            str(document['paragraphs'][index]['paragraphBody']['text']) \
                                .replace(bad_paragraph.group(), bad_paragraph.group() + good_paragraph.group())

        for bad_point in list_of_bad_points:
            document['paragraphs'][index]['paragraphBody']['text'] = \
                str(document['paragraphs'][index]['paragraphBody']['text']).replace(bad_point['good'], bad_point['bad'])

    return document


def clean_text(document):
    for paragraph in document.get('paragraphs', []):
        paragraph['paragraphHeader']['text'] = paragraph['paragraphHeader']['text'].strip()
        paragraph['paragraphBody']['text'] = paragraph['paragraphBody']['text'].strip()
    return document


def subparagraph_format(document):
    regex = re.compile(r'(?<!п.)(\s+|^)(\d+\.\d+\.(\d+\.|)\s)', re.S)
    for index, paragraph in enumerate(document.get('paragraphs', [])):
        document['paragraphs'][index]['paragraphBody']['text'] = regex.sub(
            lambda m: "<br>" + "<br>" + m.group(),
            paragraph['paragraphBody']['text']
        )

    return document


def define_attributes(document, set_price: int = -1):
    keys: [[str]] = [
        ['казенное учреждение комбинат', 'Управления Федерального агентства'],
        ['государственным резервам по', 'федеральному округу, именуем'],
        [', с одной стороны, и', ', именуем'],
        [r'полный комплекс работ по строительству объекта \(далее – «работы»\):',
         r'\(далее – «Объект»\) в соответствии с проектной документацией,'],
        ['Место выполнения работ:', '.'],
        ['Цена Государственного контракта составляет', ', в том числе по']
    ]
    price: int = 0
    for index, paragraph in enumerate([0, 0, 0, 1, 1, 3]):
        phrase = re.search(
            f'{keys[index][0]}(.*){keys[index][1]}',
            document['paragraphs'][paragraph]['paragraphBody']['text']
        )

        if phrase is None:
            logging.error('doesn`t find phrase')
            logging.error(f'{keys[index][0]}(.*){keys[index][1]}')
            continue

        change_phrase = phrase.group(0).replace(
            phrase.group(1),
            ' <span style="background-color:moccasin;display: inline;">' +
            phrase.group(1).strip() +
            '</span> '
        )

        if paragraph == 3:
            price_in_str = re.search(r'(\d+)', ''.join(phrase.group(1).strip().split()))
            if price_in_str:
                price = int(price_in_str.group(0))
            if set_price != -1:
                key = f'{keys[index][0]} <span style="background-color:moccasin;display: inline;">' \
                      f'{str(set_price).strip()} руб.' \
                      f'</span> ' \
                      f'{keys[index][1]}'
                change_phrase = re.sub(f'{keys[index][0]}(.*){keys[index][1]}', key, phrase.group(0))
                price = set_price

        document['paragraphs'][paragraph]['paragraphBody']['text'] = document['paragraphs'][paragraph]['paragraphBody'][
            'text'].replace(phrase.group(0), change_phrase)

    return document, price


def check_warranty_periods(document):
    start: str = 'срок исполнения таких обязательств '
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

    number = re.search(r'\d+', date)
    if number is not None:
        number = int(number.group(0))
        if number > 29:
            flag = True

    if any(word in date for word in good):
        flag = True

    if not ('не менее' in date or ('более' in date and 'не' not in date)):
        flag = False

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


def check_fines(document, price: int = 0):
    if price == 0:
        return document, {
            'price': 0,
            'fine': 0,
            'fine_from_doc': 0,
            'template': [],
            'errors': []
        }

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
        10: '\n <span style="background-color:lightgreen;display: inline;">10 процентов цены Государственного контракта (здесь и далее при необходимости: этапа), что составляет ___ руб. (в случае, если цена Контракта (здесь и далее при необходимости: этапа) не превышает 3 млн. рублей).\n</span>',
        5: '\n <span style="background-color:lightgreen;display: inline;">5 процентов цены Государственного контракта, что составляет ___ руб. (в случае, если цена Контракта составляет от 3 млн. рублей до 50 млн. рублей (включительно).\n</span>',
        1: '\n <span  style="background-color:lightgreen;display: inline;">1 процент цены Государственного контракта, что составляет ___ руб. (в случае, если цена Контракта составляет от 50 млн. рублей до 100 млн. рублей (включительно).\n</span>',
        0.5: '\n <span style="background-color:lightgreen;display: inline;">0,5 процента цены Государственного контракта, что составляет ___ руб. (в случае, если цена Контракта составляет от 100 млн. рублей до 500 млн. руб.(включительно).\n</span>',
        0.4: '\n <span style="background-color:lightgreen;display: inline;">0,4 процента цены Государственного контракта, что составляет ___ руб. (в случае, если цена Контракта составляет от 500 млн. рублей до 1 млрд. руб. (включительно).\n</span>',
        0.3: '\n <span style="background-color:lightgreen;display: inline;">0,3 процента цены Государственного контракта, что составляет ___ руб. (в случае, если цена Контракта составляет от 1 млрд. рублей до 2 млрд. руб.(включительно).\n</span>',
        0.25: '\n<span style="background-color:lightgreen;display: inline;">0,25 процента цены Государственного контракта, что составляет ___ руб. (в случае, если цена Контракта составляет от 2 млрд. рублей до 5 млрд. руб.(включительно).\n</span>',
        0.2: '\n <span style="background-color:lightgreen;display: inline;">0,2 процента цены Государственного контракта, что составляет ___ руб. (в случае, если цена Контракта составляет от 5 млрд. рублей до 10 млрд. руб.(включительно).\n</span>',
        0.1: '\n <span style="background-color:lightgreen;display: inline;">0,1 процента цены Государственного контракта, что составляет ___ руб. (в случае, если цена Контракта превышает 10 млрд. рублей.\n</span>'
    }
    fine = -5
    fine_from_doc = -10
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
        logging.error('Не найден штраф в пункте 15.2.1')
        array_of_errors.append({'error': 'Не найден штраф в пункте 15.2.1'})
    else:
        try:
            fine_from_doc = int(phrase.group(1).replace(' ', ''))
        except ValueError:
            fine_from_doc = -10
        if fine != fine_from_doc:
            logging.error('Не правильно указан штраф в пункте 15.2.1')
            array_of_errors.append({
                'error': 'Не правильно указан штраф в пункте 15.2.1',
            })

    percent_from_doc = re.search(r'(\d+(,\d+|)) процент(ов|а|) цены Государственного',
                                 document['paragraphs'][21]['paragraphBody']['text'])
    template: str = ''
    if percent_from_doc is None:
        logging.error('Не найден процент')
        array_of_errors.append({'error': 'Не найден процент в пункте 15.2.1'})

        template = templates[percent].replace('___', str(fine))
        template = '\n' + template + '\n'

        document['paragraphs'][21]['paragraphBody']['text'] = document['paragraphs'][21]['paragraphBody']['text'] \
            .replace('предусмотренных Государственным контрактом в размере:',
                     'предусмотренных Государственным контрактом в размере:' + template)
    else:
        percent_from_doc_int = float(percent_from_doc.group(1).strip().replace(',', '.'))
        if percent == percent_from_doc_int and fine == fine_from_doc:
            change_phrase = highlight(phrase)
            change_percent = highlight(percent_from_doc)

            template = templates[percent].replace('___', str(fine))

            document['paragraphs'][21]['paragraphBody']['text'] = document['paragraphs'][21]['paragraphBody']['text'] \
                .replace(phrase.group(0), change_phrase).replace(percent_from_doc.group(0), change_percent)
        else:
            if percent != percent_from_doc_int:
                array_of_errors.append({'error': 'Не правильно указан процент в пункте 15.2.1'})
            change_phrase = highlight(phrase, fine == fine_from_doc)
            change_percent = highlight(percent_from_doc, percent == percent_from_doc_int)

            template = templates[percent].replace('___', str(fine))
            template = '\n' + template + '\n'

            document['paragraphs'][21]['paragraphBody']['text'] = document['paragraphs'][21]['paragraphBody']['text'] \
                .replace(phrase.group(0), change_phrase) \
                .replace(percent_from_doc.group(0), change_percent) \
                .replace('предусмотренных Государственным контрактом в размере:',
                         'предусмотренных Государственным контрактом в размере:' + template)
    # print(price)
    return document, {
        'price': price,
        'fine': fine,
        'fine_from_doc': fine_from_doc,
        'template': ['[Пункт 15.2.1](#15)' + template],
        'errors': array_of_errors
    }


def fine_for_each_fact(document, price: int, info):
    if price <= 0:
        logging.error(f'Сумма меньше или равна нулю: {price}')
        return document, info
    templates = [
        r'1( | |)000 руб\. \(в случае, если цена Государственного контракта не превышает 3 млн\. рублей\)\.',
        r'5( | |)000 руб\. \(в случае, если цена Государственного контракта составляет от 3 млн\. рублей до 50 млн\. рублей\)\.',
        r'10( | |)000 руб\. \(в случае, если цена Государственного контракта составляет от 50 млн\. рублей до 100 млн\. рублей\)\.',
        r'100( | |)000 руб\. \(в случае, если цена Государственного контракта превышает 100 млн\. рублей\)\.'
    ]
    template: str = ''
    array_of_interval = [
        {
            'start': 0,
            'end': 3000000
        },
        {
            'start': 3000000,
            'end': 50000000
        },
        {
            'start': 50000000,
            'end': 100000000
        },
        {
            'start': 100000000,
            'end': float('inf')
        },
    ]

    for index, interval in enumerate(array_of_interval):
        if interval['start'] <= price < interval['end']:
            template = templates[index]
            break

    if template == '':
        logging.error('Не удалось найти штраф в пункте 15.5.1')
        return document, info

    phrase = re.search(template, document['paragraphs'][21]['paragraphBody']['text'])
    template = template.replace('( | |)', ' ').replace(r'\.', '.').replace(r'\(', '(').replace(r'\)', ')')

    if phrase is not None:
        logging.info('Фраза найдена')
        highlight_phrase = highlight_text(phrase.group(0)) + '\n'
        document['paragraphs'][21]['paragraphBody']['text'] = document['paragraphs'][21]['paragraphBody'][
            'text'].replace(phrase.group(0), highlight_phrase)
        info['template'].append('[Пункт 15.5.1](#15) <br>' + highlight_phrase)
        return document, info
    else:
        phrase = re.search(r'превышающих начальную \(максимальную\) цену контракта\):',
                           document['paragraphs'][21]['paragraphBody']['text'])
        bad_phrase = re.search(r'превышающих начальную \(максимальную\) цену контракта\):([\s\S]*)15\.5\.2\.',
                               document['paragraphs'][21]['paragraphBody']['text'])

        if bad_phrase is None:
            logging.error('Плохая фраза не найдена')
            return document, info
        if phrase is None:
            logging.error('Хорошая фраза не найдена')
            return document, info

        info['errors'].append({'error': 'Не правильно указан штраф в пункте 15.5.1'})

        highlight_bad_phrase = highlight(bad_phrase, False)
        highlight_bad_phrase = highlight_bad_phrase.replace('<span', '<br><span').replace('</span>', '</span><br>')
        document['paragraphs'][21]['paragraphBody']['text'] = document['paragraphs'][21]['paragraphBody'][
            'text'].replace(bad_phrase.group(0), highlight_bad_phrase)

        current_phrase = phrase.group(0) + '<br>' + highlight_text(template)
        document['paragraphs'][21]['paragraphBody']['text'] = document['paragraphs'][21]['paragraphBody'][
            'text'].replace(phrase.group(0), current_phrase)

        info['template'].append('[Пункт 15.5.1](#15) <br>' + highlight_text(template))
        # info['template'].append(highlight_text(bad_phrase.group(1), False))
        return document, info


def highlight(phrase, good: bool = True):
    return phrase.group(0).replace(
        phrase.group(1),
        f' <span style="background-color:{"lightgreen" if good else "pink"};display: inline;">' +
        phrase.group(1).strip() +
        '</span> '
    )


def highlight_text(text: str, good: bool = True):
    return f'<span style="background-color:{"lightgreen" if good else "pink"};display: inline;"> ' + text + ' </span>'
