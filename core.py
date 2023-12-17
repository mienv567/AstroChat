#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Time    : 12/16/23 21:09
# @Author  : jackietan@tencent.com
# @File    : parse_xingpan.py
import json
import re
from typing import Tuple

import cpca
import requests
from bs4 import BeautifulSoup


class Core():
    def __init__(self, birthday, province, city, area):
        self.area_dict = dict()
        self.dist = '0'
        self.province = province
        self.city = city
        self.area = area
        self.birthday_time = birthday
        self.soup = None
        self.glon_deg = ''


    def do(self,):
        self._http_ixingpan()
        self.__parse_glon_glat()  # 获取经纬度，Optional
        # soup_ixingpan = _get_basic_soup_from_http(customer_name=customer_name, content=content)

        # 解析爱星盘结果
        _parse_ixingpan_house(soup_ixingpan)
        _parse_ixingpan_star(soup_ixingpan)
        _parse_ixingpan_aspect(soup_ixingpan)

        # 互溶接纳
        is_received_or_mutal()

        # 设置受克信息
        set_session_afflict()




    def _http_ixingpan(self):
        def _load_ixingpan_dist(self, ):
            area_dict = {'山东省':
                             {'济南市':
                                  {'长清区': 1557, 'xx': 123},
                              '烟台市':
                                  {'长岛县': 1611, '福山区': 123}}}
            area_dict.clear()
            with open('./file/ixingpan_area.json', 'r') as file:
                json_data = json.load(file)
                for province in json_data.keys():
                    if province not in area_dict:
                        area_dict[province] = {}

                    city_json = json_data[province].keys()
                    for city in city_json:
                        if city not in area_dict[province]:
                            area_dict[province][city] = {'未选择': '0'}

                        area_vec = json_data[province][city].split(',')
                        for sub in area_vec:
                            area = sub.split('|')[0]
                            areaid = sub.split('|')[1]

                            area_dict[province][city].update({area: areaid})

            self.area_dict = area_dict
            self.dist = area_dict[self.province][self.city][self.area]


        def generate_random_string():
            import random, string
            length = random.randint(3, 9)  # 随机生成长度在4到8之间的整数
            characters = string.ascii_lowercase + string.digits  # 包含小写字母和数字的字符集
            return ''.join(random.choice(characters) for _ in range(length))


        """ ----------------------- 夏令时 ------------------------- """
        def _get_is_dst(time_str):
            # 重庆（Chongqing）：Asia / Chongqing
            # 天津（Tianjin）：Asia / Shanghai
            # 香港（Hong
            # Kong）：Asia / Hong_Kong
            # 澳门（Macau）：Asia / Macau
            # 台北（Taipei）：Asia / Taipei
            # 乌鲁木齐（Urumqi）：Asia / Urumqi
            # 哈尔滨（Harbin）：Asia / Harbin

            from datetime import datetime
            import pytz

            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            localized_dt = pytz.timezone('Asia/Shanghai').localize(dt)
            is_dst = localized_dt.dst().total_seconds() != 0

            return is_dst


        birthday = self.birthday_time.split(' ')[0]
        birth_time = self.birthday_time.split(' ')[1]
        short_time_string = ":".join(birth_time.split(":")[:2])


        female = 1
        new_name = generate_random_string()
        dst = _get_is_dst(self.birthday_time)
        url = f"https://xp.ixingpan.com/xp.php?type=natal&name={new_name}&sex={female}&dist={self.dist}&date={birthday}&time={short_time_string}&dst={dst}&hsys=P"

        # 发送GET请求
        response = requests.get(url, cookies={'xp_planets_natal': '0,1,2,3,4,5,6,7,8,9,25,26,27,28,15,19,10,29', 'xp_aspects_natal': '0:8,180:8,120:8,90:8,60:8'})

        # 获取返回的HTML源码
        html_str = response.text
        soup = BeautifulSoup(html_str, 'html.parser')

        self.soup = soup


    def _parse_glon_glat(self,):
        tables = self.soup.find_all('table')
        table = tables[0]

        # print(table)
        tbody = table.find('tbody')
        trs = tbody.find_all('tr')

        soup_tmp = trs[1]
        td = trs[1].find_all('td')[1]
        # print(td)
        pattern = r'(\d+°\d+[EW]\s\d+°\d+[NS])'
        match = re.search(pattern, td.text.strip())

        if match:
            self.glon_deg = match.group(1).strip()
            print(f'获取经纬度结果：{self.glon_deg}')
            # print('获取经纬度结果：', coordinates)
        else:
            print('未匹配到数据')
            # print("未匹配到数据")
            return '服务器内部错误', '', ''


    def _parse_ixingpan_house(self,):
        '''
        解析包括：
            宫头宫位
        :param soup:
        :return:
        '''

        star_ruler_dict = get_session(SESS_KEY_STAR_RULER)

        tables = soup.find_all('table')

        table = tables[6]
        tbody = table.find('tbody')
        trs = tbody.find_all('tr')
        for tr in trs:
            tds = tr.find_all('td')
            if len(tds) != 5:
                continue

            house = tds[0].text.strip()
            constellation = tds[1].text.strip()
            lord = tds[2].text.strip()
            lord_loc = tds[4].text.strip()

            constellation = pattern_constellation.sub('', constellation).strip()

            match = pattern_house.search(house)

            if match:
                house = int(match.group())
            else:
                house = -1

            ruler_loc = int(lord_loc.replace('宫', ''))

            house_obj = House(house_num=house, ruler=lord, ruler_loc=ruler_loc)
            house_obj.constellation = constellation

            web.ctx.env['house_dict'][house] = house_obj

            if lord not in star_ruler_dict:
                star_ruler_dict[lord] = []

            star_ruler_dict[lord].append(house)


