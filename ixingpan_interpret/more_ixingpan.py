# -*- coding: utf-8 -*-
import configparser
import json
import pickle, os
import random
import time
from dateutil.relativedelta import relativedelta


import requests
from bs4 import BeautifulSoup

# 太阳1宫、太阳双子、2宫射手、太阳刑冥王、1宫宫主飞1宫
# relation2：火星正相天王（拱）

res_dict = {}
load_size = 0
more_dict = {}


def get_url(sdate, nday):
    def generate_random_string():
        import random, string
        length = random.randint(3, 9)  # 随机生成长度在4到8之间的整数
        characters = string.ascii_lowercase + string.digits  # 包含小写字母和数字的字符集
        return ''.join(random.choice(characters) for _ in range(length))

    new_name = generate_random_string()

    from datetime import datetime, timedelta

    def traverse_hours(sdate, ndays):
        start_date = datetime.strptime(sdate, "%Y-%m-%d")
        end_date = start_date + timedelta(days=nday)
        current_date = start_date
        result = []

        while current_date < end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            time_str = current_date.strftime("%H:%M")
            result.append((date_str, time_str))
            current_date += timedelta(hours=12)

        return result


    def traverse_years(sdate, nyears):
        start_date = datetime.strptime(sdate, "%Y-%m-%d")
        end_date = start_date + relativedelta(years=nyears)
        current_date = start_date
        result = []

        while current_date < end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            time_str = current_date.strftime("%H:%M")
            result.append((date_str, time_str))
            current_date += relativedelta(years=1)
        
        return result


    param_vec = traverse_hours(sdate, nday)

    base_url = "https://xp.ixingpan.com/xp.php?type=natal&name={}&sex=1&dist=759&date={}&time={}&dst=0&hsys=P"

    res = []
    for t in param_vec:
        # https://xp.ixingpan.com/xp.php?type=natal&name=jackietan&sex=0&dist=1550&date=1989-08-05&time=12:30&dst=1&hsys=P&auto=1
        date_str = t[0]
        time_str = t[1]
        res.append(base_url.format(new_name, date_str, time_str))

    return res


def get_interpret_soup(url):
    response = requests.get(url, cookies={'chart_mode': 'classic-chart',
                                          'xp_planets_natal': '0,1,2,3,4,5,6,7,8,9,25,26,27,28,15,19,10,29',
                                          'xp_aspects_natal': '0:8,180:8,120:8,90:8,60:8'})

    # 获取返回的HTML源码
    html_str = response.text
    soup = BeautifulSoup(html_str, 'html.parser')

    def _parse_web_interpret(soup):
        div_tags = soup.find_all('div', class_='interpretation-section')
        for div_tag in div_tags:
            # 找:太阳双子这样的标题
            span_tag = div_tag.find_all('span', class_='interpretation-header')
            title = span_tag[0].text

            # 找解析
            p_tags = div_tag.find_all('p')
            filtered_p_tags = [p_tag for p_tag in p_tags if not p_tag.find_parent(class_='interpretation-section-header')]
            interpret = filtered_p_tags[0].text.strip().replace('来源：点击查看', '')
            interpret = interpret.strip()
            # print('-->', interpret)

            if title not in res_dict:
                res_dict[title] = []

            if interpret not in res_dict[title]:
                res_dict[title].append(interpret)

    _parse_web_interpret(soup)


def dump_file():
    # 将字节流写入文件
    with open("data.pickle", "wb") as file:
        pickle.dump(res_dict, file)

    # for k, v in res_dict.items():
    #     print(f'{k} list_size:{len(v)}')

    print(f'\nFinished Curl Pickle File, Size:{len(res_dict)}')


def load_pickle():
    global res_dict
    global load_size

    if os.path.exists('./data.pickle'):
        with open("data.pickle", "rb") as file:
            tmp = pickle.load(file)

        res_dict = tmp
        load_size = len(res_dict)
        print(f'Load Pickle File, size:{len(res_dict)}')


def cal_diff(all_keys):
    a = set(list(res_dict.keys()))

    difference = all_keys - a

    print(f'cal_diff: {len(difference)}\n{list(difference)}')


if __name__ == '__main__':
    load_pickle()

    url_vec = get_url('2015-10-10', nday=1)

    for url in url_vec:
        random_number = random.randint(1, 4)
        time.sleep(random_number)
        print(f'start process url {url}')
        get_interpret_soup(url)

        if load_size != len(res_dict):
            dump_file()

    # dump_file()

    cal_diff(all_keys)

