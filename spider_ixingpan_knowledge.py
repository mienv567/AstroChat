# -*- coding: utf-8 -*-
import configparser
import json
import re
from typing import Tuple, List, Dict

import cpca
import requests
from bs4 import BeautifulSoup


# base_url = 'https://xp.ixingpan.com/xp.php?type=natal&name={}&sex=1&dist=1550&date=1989-08-05&time=12:58&dst=1&hsys=P'

base_url = 'https://xp.ixingpan.com/xp.php?type=natal&name={}&sex=1&dist=1550&date={}&time={}&dst=0&hsys=P'


if __name__ == '__main__':
    pass

def generate_random_string():
    import random, string
    length = random.randint(3, 9)  # 随机生成长度在4到8之间的整数
    characters = string.ascii_lowercase + string.digits  # 包含小写字母和数字的字符集
    return ''.join(random.choice(characters) for _ in range(length))


def get_soup(url):
    response = requests.get(url, cookies={'chart_mode': 'classic-chart',
                                          'xp_planets_natal': '0,1,2,3,4,5,6,7,8,9,25,26,27,28,15,19,10,29',
                                          'xp_aspects_natal': '0:8,180:8,120:8,90:8,60:8'})

    # 获取返回的HTML源码
    html_str = response.text
    soup = BeautifulSoup(html_str, 'html.parser')

    return soup


def _parse_web_interpret(soup):
    div_tags = soup.find_all('div', class_='interpretation-section')
    for div_tag in div_tags:
        # 找:太阳双子这样的标题
        span_tag = div_tag.find('span')
        if span_tag:
            title = span_tag.text
            if not title.startswith("上升"):
                continue

        # 找解析
        p_tags = div_tag.find_all('p')
        filtered_p_tags = [p_tag for p_tag in p_tags if not p_tag.find_parent(class_='interpretation-section-header')]
        interpret = filtered_p_tags[0].text.strip().replace('来源：点击查看', '')
        # print('-->', interpret)

        self.interpret_asc[title] = interpret
        break
