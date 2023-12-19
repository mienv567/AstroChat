#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Time    : 12/16/23 21:09
# @Author  : jackietan@tencent.com
# @File    : parse_xingpan.py
import configparser
import json
import re
from typing import Tuple, List, Dict

import cpca
import requests
from bs4 import BeautifulSoup


pattern_constellation = re.compile(r'\([^)]*\)'r'(.+?)\s*\((\d+).*?\)(?:\s*\((.*?)\))?$')
pattern_house = re.compile(r'\d+')
constellation_whitelist = {'天王', '海王', '冥王', '太阳', '月亮', '水星', '火星', '木星', '土星', '金星'}
seven_star_list = ['太阳', '月亮', '水星', '火星', '木星', '土星', '金星']


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
        self.chart_svg_html = ''

        # 核心字典数据, x落x座、x落x宫、x宫主飞x宫
        self.star_dict: Dict[str, Star] = {}
        self.house_dict: Dict[int, House] = {}
        self.constellation_dict: Dict[str, Constellation] = {}
        self.afflict_dict: Dict[str, Affliction] = {}  # {木星: afflict}
        self.star_ruler_dict: Dict[str, List[int]] = {}
        self.afflict_dict: Dict[str, Affliction] = {}  # {木星: afflict}

        # File Dict From knowledge_web.ini
        self.knowledge_dict: Dict[str, Dict[str, str]] = {}
        self.boundry_dict: Dict[str, Dict[str, List[int]]] = dict()  # {白羊: {木星: [0, 6]}}

        # 用于prompt召回的key，和用户的描述
        self.llm_recall_key = []
        self.ruler_fly_vec = []
        self.star_loc_vec = []
        self.guest_desc_vec = []

        # Web-Interpret, 找 <div class='interpretation-section'>, <div class='moreinterp'>
        self.interpret_asc = {}
        self.interpret_sum = {}
        self.interpret_moon = {}

    def execute(self,):
        self._init_knowledge_dict()
        self._http_ixingpan()
        self._parse_glon_glat()  # 获取经纬度，Optional
        # soup_ixingpan = _get_basic_soup_from_http(customer_name=customer_name, content=content)

        # 解析爱星盘结果
        self._parse_ixingpan_house()
        self._parse_ixingpan_star()
        self._parse_ixingpan_aspect()

        # 互溶接纳
        self._is_received_or_mutal()

        # 设置受克信息
        self._set_session_afflict()

    # 根据排盘信息，生成用户描述
    def gen_guest_info(self,):
        """
        统一话说：n宫主飞n宫、x落几宫、2宫主被1宫主接纳、
        :return:
        """

        # 144种日月落星座
        def ctx_key_sun_moon_const():
            rec_vec = []

            solar, moon = '', ''
            for star_name, star_obj in self.star_dict.items():
                if star_name not in {'太阳', '月亮'}:
                    # logger.debug(f'{star_name} continue....')
                    continue

                degree = star_obj.degree
                house = star_obj.house
                score = star_obj.score
                is_afflicted = '严重受克' if star_obj.is_afflicted else ''
                constellation = star_obj.constellation

                if star_name == '太阳':
                    solar = constellation
                elif star_name == '月亮':
                    moon = constellation

            self.llm_recall_key.append(f'太阳{solar}月亮{moon}')
            # return f'太阳{solar}月亮{moon}'

        # 上升、太阳星座
        def ctx_key_asc_const():
            rec_vec = []

            solar, asc = '', ''
            for star_name, star_obj in self.star_dict.items():
                if star_name not in {'太阳', '上升'}:
                    continue

                degree = star_obj.degree
                house = star_obj.house
                score = star_obj.score
                is_afflicted = '严重受克' if star_obj.is_afflicted else ''
                constellation = star_obj.constellation

                if star_name == '太阳':
                    solar = constellation
                elif star_name == '上升':
                    asc = constellation

            print(solar, asc)
            self.llm_recall_key.append(f'上升{asc}')
            self.llm_recall_key.append(f'上升{asc}太阳{solar}')

            # return f'上升{asc}', f'上升{asc}太阳{solar}'

        ctx_key_sun_moon_const()
        ctx_key_asc_const()

        # llm 召回的key
        # ruler_fly_vec = []
        # star_loc_vec = []
        # guest_desc_vec = []
        for star_name, star_obj in self.star_dict.items():
            if star_name in {'北交', '上升', '中天', '下降', '天底'}:
                continue

            degree = star_obj.degree
            house = star_obj.house
            score = star_obj.score
            is_afflicted = '严重受克' if star_obj.is_afflicted else ''
            constellation = star_obj.constellation
            lord_house_vec = star_obj.lord_house_vec

            # 互容接纳
            rec_vec = []
            for k, obj in star_obj.recepted_dict.items():
                msg = f'与「{obj.star_b}」互容'

                if obj.action_name == '接纳':
                    msg = f'被「{obj.star_b}」接纳'

                rec_vec.append(msg)

            rec_msg2 = ''
            if len(rec_vec) != 0:
                rec_msg = ';'.join(rec_vec)
                rec_msg2 = f'{rec_msg}'

            # 搞飞宫
            if star_name in seven_star_list:
                for lord_house in lord_house_vec:
                    tmp = f'{lord_house}宫主落{house}宫'
                    self.ruler_fly_vec.append(tmp)

                    if lord_house == 1:
                        self.star_loc_vec.append(f'命主星落{house}宫')

            # 搞落宫
            self.star_loc_vec.append(f'{star_name}落{house}宫')

            msg_star_loc = f'{star_name}落{house}宫，在{constellation}座'
            msg_lord = '' if len(star_obj.lord_house_vec) == 0 else f'是{"、".join([str(item) for item in star_obj.lord_house_vec])}的宫主星'
            msg_score = f'星体得分:{score}' if star_name not in {'天王', '海王', '冥王', '凯龙', '婚神', '福点'} else ''
            msg_hurong = '' if rec_msg2 == '' else f'互溶接纳信息：{rec_msg2}'

            # msg = f'{msg_star_loc}，{msg_lord}，在{constellation}座，{msg_score} {msg_hurong}， {is_afflicted}'
            tmp = [msg_star_loc, msg_score, msg_lord, msg_hurong, f'{is_afflicted}']
            print('-->', tmp)
            self.guest_desc_vec.append('，'.join([item for item in tmp if item != '']))
            # logger.debug(msg)

    def get_chart_svg(self):
        html_str = '<html><meta http-equiv="Content-type" content="text/html; charset=utf-8" /><link href="https://xp.ixingpan.com/statics/css/bootstrap.min.css" rel="stylesheet" type="text/css" /><link rel="stylesheet" href="https://xp.ixingpan.com/statics/css/style.css?v=2021030401"/><link rel="stylesheet" href="https://xp.ixingpan.com/statics/css/font-xp-gryph.css?v=2016083101" /><link rel="stylesheet" type="text/css" href="https://xp.ixingpan.com/statics/css/chart.css?v=2016082402" title="chart-default" media="all" /><link rel="stylesheet" type="text/css" href="https://xp.ixingpan.com/statics/css/graphy-chart.css?v=2016062801" id="chartMode"/><link rel="stylesheet" href="https://xp.ixingpan.com/statics/css/chart-extend.css?v=2016082402" id="aspect-line-type-css"/><div style="width: 100%;margin:0px;padding:0px"><div id="achart" class="text-center" style="margin: auto;padding:5px 10px 15px 5px;">{}</div></div></html>'

        svg_tags = self.soup.find_all('svg')

        svg_content = svg_tags[0].prettify()  # 获取SVG标签的内容
        # print(svg_content)
        res = html_str.format(svg_content)
        # print(res)

        self.chart_svg_html = res

    def _parse_web_interpret(self):
        div_tags = self.soup.find_all('div', class_='interpretation-section')
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

    def _http_ixingpan(self):
        def _load_ixingpan_dist():
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

            print(f'in is_dst, time_str:{time_str}, is_dst={is_dst}')

            if is_dst:
                return 1
            else:
                return 0


        _load_ixingpan_dist()

        birthday = self.birthday_time.split(' ')[0]
        birth_time = self.birthday_time.split(' ')[1]
        short_time_string = ":".join(birth_time.split(":")[:2])


        female = 1
        new_name = generate_random_string()
        dst = _get_is_dst(self.birthday_time)
        url = f"https://xp.ixingpan.com/xp.php?type=natal&name={new_name}&sex={female}&dist={self.dist}&date={birthday}&time={short_time_string}&dst={dst}&hsys=P"
        print(url)

        # 发送GET请求
        response = requests.get(url, cookies={'chart_mode': 'classic-chart', 'xp_planets_natal': '0,1,2,3,4,5,6,7,8,9,25,26,27,28,15,19,10,29', 'xp_aspects_natal': '0:8,180:8,120:8,90:8,60:8'})

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
        tables = self.soup.find_all('table')

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

            self.house_dict[house] = house_obj

            if lord not in self.star_ruler_dict:
                self.star_ruler_dict[lord] = []

            self.star_ruler_dict[lord].append(house)


    def _parse_ixingpan_star(self,):
        '''
        解析包括：
            星体、四轴、富点、婚神、凯龙、北交
            落入星座
            落入宫位
        :param soup:
        :return:
        '''

        tables = self.soup.find_all('table')

        table = tables[5]
        tbody = table.find('tbody')
        trs = tbody.find_all('tr')
        for tr in trs:
            tds = tr.find_all('td')
            star = tds[0].text.strip()
            constellation_ori = tds[1].text.strip()
            house = tds[2].text.strip()

            constellation, degree, status = self._extract_constellation(constellation_ori)

            # constellation = pattern_constellation.sub('', constellation_ori).strip()

            match = pattern_house.search(house)

            if match:
                house = int(match.group())
            else:
                house = -1

            if star in self.star_dict:
                self.star_dict[star].constellation = constellation

                if house != self.star_dict[star].house:
                    pass
                    # print(f'{star} {star_dict[star].house} {house}')
            else:
                r = Star(star=star, house=house)
                r.constellation = constellation
                self.star_dict[star] = r

            self.star_dict[star].degree = int(degree)
            # self.degree: int  # 度数
            # self.is_triplicity = 0  # 三份
            # self.is_term_ruler = 0  # 界
            # self.is_face = 0  # 十度

            # self.is_domicile = 0  # 入庙
            # self.is_exaltation = 0  # 耀升
            # self.is_fall = 0  # 弱 -5'
            # self.is_detriment = 0  # 陷 -4'

            is_domicile = 1 if status == '庙' else 0
            is_exaltation = 1 if status == '旺' else 0  # 抓的结果如果是庙,则不会写耀升

            if is_exaltation == 0:
                is_exaltation = 1 if self._is_exaltation_ruler(star, constellation) else 0

            is_fall = 1 if status == '弱' else 0
            is_detriment = 1 if status == '陷' else 0
            is_triplicity = 1 if self._is_triplicity_ruler(star, constellation) else 0
            is_face = 1 if self._is_face_ruler(star, constellation) else 0
            is_term = 1 if self._is_term_ruler(star, constellation) else 0

            self.star_dict[star].is_domicile = is_domicile
            self.star_dict[star].is_exaltation = is_exaltation
            self.star_dict[star].is_fall = is_fall
            self.star_dict[star].is_detriment = is_detriment

            self.star_dict[star].is_triplicity = is_triplicity
            self.star_dict[star].is_face = is_face
            self.star_dict[star].is_term = is_term

            score = 5 * is_domicile + 4 * is_exaltation + 3 * is_triplicity + 2 * is_term + 1 * is_face - 4 * is_detriment - 5 * is_fall
            if star not in seven_star_list:
                score = -1

            self.star_dict[star].score = score

            if star in self.star_ruler_dict:
                self.star_dict[star].lord_house_vec = self.star_ruler_dict[star]

            if house != -1:
                self.house_dict[house].loc_star.append(star)

            # logger.debug(f'-->星体:{star} 星座:{constellation} 度数:{degree} 庙:{is_domicile} 旺:{is_exaltation} 三:{is_triplicity} 界:{is_term} 十:{is_face}  得分:{score}\t宫神分:{web.ctx.env["star_dict"][star].score}宫位:{house}')

            # Update Constellation
            if star in constellation_whitelist:
                if constellation in self.constellation_dict:
                    self.constellation_dict[constellation].star_vec.append(star)
                else:
                    c = Constellation(name=constellation)
                    c.star_vec.append(star)
                    self.constellation_dict[constellation] = c


    def _parse_ixingpan_aspect(self,):
        tables = self.soup.find_all('table')

        # 选择第7个<table>下的<td>标签
        table = tables[7]
        tbody = table.find('tbody')
        trs = tbody.find_all('tr')

        # print_module_info('DEBUG 爱星盘-相位信息')
        for tr in trs:
            tds = tr.find_all('td')
            star_a = tds[0].text.strip()
            star_b = tds[2].text.strip()
            aspect = tds[1].text.strip()
            degree = int(tds[4].text.strip().split('°')[0])  # 7°38

            # logger.debug(f'{star_a} {star_b} {aspect}')

            aspect = aspect if aspect != '拱' else '三合'

            aspect_obj = Aspect(star_b=star_b, aspect=aspect, degree=degree)
            # star_dict[star_a].aspect_vec_old.append(aspect_obj)
            self.star_dict[star_a].aspect_dict[star_b] = aspect_obj

            # 反过来填充
            aspect_obj_reverse = Aspect(star_b=star_a, aspect=aspect, degree=degree)
            self.star_dict[star_b].aspect_dict[star_a] = aspect_obj_reverse


    def _is_received_or_mutal(self,):
        def is_mutal(a: Star, b: Star):
            if a.star in black_key or b.star in black_key:
                return False, ''

            domicile_dict = self.knowledge_dict['入庙']  # {星座: 星体}
            exaltation_dict = self.knowledge_dict['耀升']  # {星座: 星体}

            # 接纳：本垣、曜升、三分
            name_a, name_b, const_a, const_b = a.star, b.star, a.constellation, b.constellation

            # 本垣: a的落座是否在b的入庙星座
            a_ret, b_ret = False, False
            if domicile_dict[const_a] == name_b or (const_a in exaltation_dict and exaltation_dict[const_a] == name_b):
                a_ret = True

            if domicile_dict[const_b] == name_a or (const_b in exaltation_dict and exaltation_dict[const_b] == name_a):
                b_ret = True

            if a_ret and b_ret:
                return True

            return False

        def is_received(a: Star, b: Star):
            name_a, name_b, const_a, const_b = a.star, b.star, a.constellation, b.constellation
            # logger.debug(f'解析接纳: {name_a}, {const_a} {name_b} {const_b}')

            if a.star in black_key or b.star in black_key:
                return False, ''

            # 先判断是否有相位
            if b.star not in a.aspect_dict:
                return False, ''

            domicile_dict = self.knowledge_dict['入庙']  # {星座: 星体}
            exaltation_dict = self.knowledge_dict['耀升']  # {星座: 星体}

            # 接纳：本垣、曜升、三分

            # 本垣: a的落座是否在b的入庙星座
            if domicile_dict[const_a] == name_b:
                return True, '本垣'

            # 曜升: a的落座是否在b的耀升星座
            if const_a in exaltation_dict and exaltation_dict[const_a] == name_b:
                return True, '耀升'

            # # 三分计算逻辑：若 b 在a的星座，是否三分界主？
            # if is_triplicity_ruler(star_name=name_b, target_constellation=const_a):
            #     return True, '三分'

            return False, ''

            # if const_a not in domicile_dict:
            #     logger.warning(f'星座:{const_a} 不在 knowledge_dict 字典...')
            #     return False
            #
            # if const_b not in domicile_dict:
            #     logger.warning(f'星座:{const_b} 不在 knowledge_dict 字典...')
            #     return False

        black_key = {'天王', '海王', '冥王', '北交', '福点', '凯龙', '婚神', '上升', '中天', '下降', '天底'}

        keys = self.star_dict.keys()

        for star_a in keys:
            for star_b in keys:
                if star_a == star_b:
                    continue

                if star_a in black_key or star_b in black_key:
                    continue

                b_receive, level = is_received(self.star_dict[star_a], self.star_dict[star_b])
                b_mutal = is_mutal(self.star_dict[star_a], self.star_dict[star_b])

                if b_receive or b_mutal:
                    feature = '接纳' if b_receive else '互容'
                    lvl = level if b_receive else '耀升起'
                    r = Recepted(star_a=star_a, star_b=star_b, action_name=feature, level=lvl)

                    self.star_dict[star_a].recepted_dict[star_b] = r

                if b_receive:
                    # print(f'{star_a} 被 {star_b} 接纳，{level}')
                    pass
                if b_mutal:
                    # print(f'{star_a} {star_b} 互容')
                    pass


    """ ----------------------- 受克情况 ------------------------ """
    def _set_session_afflict(self,):
        '''
        灾星系统
            第一档（被一个克到就有明显事件）：8宫主 ≥ 命主星(上升点也算) > 12宫主
            第二档（被两个克到才有明显事件）：土星 = 海王 = 冥王 = 天王
            第三档（辅助参考）：火星 = 凯龙

        受克程度：0° > 90 > 180
        宫主星与灾星受克：
            1. 与灾星0、90、180
            2. 与除灾星外的宫主星形成：0、90、180
            3. 与四轴成0度，等同于
        :return:
        '''
        # Step 1. 获取三挡灾星
        ruler_1 = self.house_dict[1].ruler
        ruler_8 = self.house_dict[8].ruler
        ruler_12 = self.house_dict[12].ruler


        level_vec_1 = [ruler_1, ruler_8, ruler_12]
        level_vec_2 = ['土星', '海王', '冥王', '天王']
        zip_1 = zip(level_vec_1, ['命主星', '8宫主', '12宫主'])

        for target in seven_star_list:
            if len(self.star_dict[target].aspect_dict) == 0:
                continue

            for ruler, name in zip_1:
                if ruler not in self.star_dict[target].aspect_dict:
                    continue

                if self.star_dict[target].aspect_dict[ruler].aspect not in {'刑', '冲', '合'}:
                    continue

                if target not in self.afflict_dict:
                    a = Affliction(star=target)
                    self.afflict_dict[target] = a

                self.afflict_dict[target].level_1.append(name)

            for name in level_vec_2:
                if name not in self.star_dict[target].aspect_dict:
                    continue

                if self.star_dict[target].aspect_dict[name].aspect not in {'刑', '冲', '合'}:
                    continue

                if target not in self.afflict_dict:
                    a = Affliction(star=target)
                    self.afflict_dict[target] = a

                self.afflict_dict[target].level_2.append(name)

        # 设置得吉受克信息到 star_dict
        for star, afflict_obj in self.afflict_dict.items():
            if len(afflict_obj.level_1) >= 1:
                self.star_dict[star].is_afflicted = True
            elif len(afflict_obj.level_2) >= 2:
                self.star_dict[star].is_afflicted = True


    def _extract_constellation(self, input_str):
        pattern = r'(.+?)\s*\((\d+).*?\)(?:\s*\((.*?)\))?$'
        match = re.search(pattern, input_str)
        if match:
            name, degree, extra = match.groups()
            return name, degree, extra
        else:
            return None, None, None


    """ ----------------------- 计算先天尊贵 -------------------- """
    def _is_triplicity_ruler(self, star_name: str, target_constellation: str):
        '''
        # 三分
        [星体-四元素]
        火象 = 太阳、木星、土星
        风象 = 土星、水星、木星
        水象 = 金星、火星、月亮
        土象 = 金星、月亮、火星

        [星座-四元素]
        火象 = 射手、狮子、白羊
        风象 = 双子、天秤、水瓶
        水象 = 巨蟹、双鱼、天蝎
        土象 = 摩羯、处女、金牛
        :param constellation:
        :param star_name:
        :return:
        '''
        star_element_dict = self.knowledge_dict['星体-四元素']
        constellation_element_dict = self.knowledge_dict['星座-四元素']

        for element, star_list_str in star_element_dict.items():
            if star_name not in star_list_str:
                continue

            recall_constellation = constellation_element_dict[element]
            if target_constellation in recall_constellation:
                return True

        return False

    # 界主
    def _is_term_ruler(self, star: str, target_const: str):
        star_degree = self.star_dict[star].degree

        if target_const not in self.boundry_dict:
            return False

        if star not in self.boundry_dict[target_const]:
            return False

        if self.boundry_dict[target_const][star][0] < star_degree and star_degree <= self.boundry_dict[target_const][star][1]:
            return True

        return False

    # 十度
    def _is_face_ruler(self, star: str, target_const: str):
        # 白羊 = 火星 太阳 金星
        face_dict = self.knowledge_dict['十度']

        if target_const not in face_dict:
            return False

        vec = face_dict[target_const].split()
        if len(vec) != 3:
            return False

        loc_degree = self.star_dict[star].degree

        idx = 0
        if loc_degree > 10 and loc_degree <= 20:
            idx = 1
        elif loc_degree > 20 and loc_degree <= 30:
            idx = 2

        candi_star = vec[idx]
        if star == candi_star:
            return True

        return False

    # 十度
    def _is_exaltation_ruler(self, star: str, target_const: str):
        a_dict = self.knowledge_dict['耀升']

        if target_const in a_dict and a_dict[target_const] == star:
            return True

        return False


    def _init_knowledge_dict(self, ):
        def _load_knowledge_file():
            # Load knowledge_web.ini
            config = configparser.ConfigParser()

            file_name = './file/knowledge_web.ini'
            config.read(file_name)

            # 遍历指定section的所有option
            for section_name in config.sections():
                for option_name in config.options(section_name):
                    value = config.get(section_name, option_name)

                    if section_name in self.knowledge_dict:
                        self.knowledge_dict[section_name][option_name] = value
                    else:
                        self.knowledge_dict[section_name] = {option_name: value}

        def _init_star_boundry_dict():
            '''
            白羊 = 木星:6 金星:14 水星:21 火星:26 土星:30
            金牛 = 金星:8 水星:15 木星:22 土星:26 火星:30
            双子 = 水星:7 木星:14 金星:21 土星:25 火星:30
            巨蟹 = 火星:6 木星:13 水星:20 金星:27 土星:30
            狮子 = 土星:6 水星:13 金星:19 木星:25 火星:30
            处女 = 水星:7 金星:13 木星:18 土星:24 火星:30
            天秤 = 土星:6 金星:11 木星:19 水星:24 火星:30
            天蝎 = 火星:6 木星:14 金星:21 水星:27 土星:30
            射手 = 木星:8 金星:14 水星:19 土星:25 火星:30
            摩羯 = 金星:6 水星:12 木星:19 火星:25 土星:30
            水瓶 = 土星:6 水星:12 金星:20 木星:25 火星:30
            双鱼 = 金星:8 木星:14 水星:20 火星:26 土星:30
            '''
            boundry_orgin_dict = self.knowledge_dict['界']

            for const, star_str in boundry_orgin_dict.items():
                star_degree_vec = star_str.split()

                degree_before = -1
                for star_degree in star_degree_vec:
                    star = star_degree.split(':')[0]
                    degree = int(star_degree.split(':')[1])

                    if const not in self.boundry_dict:
                        self.boundry_dict[const] = {star: [degree_before, degree]}
                        degree_before = degree
                        continue

                    self.boundry_dict[const].update({star: [degree_before, degree]})

                    degree_before = degree


        _load_knowledge_file()

        _init_star_boundry_dict()




class Recepted:
    def __init__(self, star_a, star_b, action_name, level=''):
        self.star_a = star_a
        self.star_b = star_b
        self.action_name = action_name
        self.level = level  # (本垣+三分)

    def get_debug_info(self):
        msg = f'{self.star_b}{self.action_name}({self.level})'

        return msg

    def __str__(self):
        # msg = f'{self.star_a} 被 {self.star_b} {self.action_name}({self.level})'
        msg = f'{self.star_b} {self.action_name}({self.level})'

        return msg


class Aspect:
    def __init__(self, star_b, aspect='', degree: int = 0):
        self.star_b: str = star_b
        self.aspect: str = aspect  # 60°: 六合, 30°: 三合
        self.degree = degree

    def get_debug_info(self):
        msg = f'{self.aspect}{self.star_b}'

        return msg


class Star:
    def __init__(self, star: str, house: int, score=-1, lord_house_vec=[]):
        self.star: str = star
        self.house: int = house  # 落宫
        self.score = score
        self.lord_house_vec: List = lord_house_vec  # 几宫主
        self.is_afflicted = False  # 是否被克

        self.recepted_dict: Dict[str, Recepted] = {}  # {star_b: ReceptedObj}
        self.aspect_dict: Dict[str, Aspect] = {}  # {star_b, Aspect}

        # self.recepted_vec_old: List[Recepted] = []  # 被互溶接纳
        self.aspect_vec_old: List[Aspect] = []  # 相位

        self.jiena = []
        self.hurong = []

        self.constellation: str = ''

        self.degree = 0
        self.is_term = 0  # 界
        self.is_domicile = 0  # 入庙
        self.is_exaltation = 0  # 耀升
        self.is_triplicity = 0  # 三份
        self.is_face = 0  # 十度
        self.is_fall = 0  # 弱
        self.is_detriment = 0  # 陷


    def __str__(self):
        # msg_recepted = [msg.get_debug_info() for msg in self.recepted_vec_old]
        msg_recepted = [msg.get_debug_info() for key, msg in self.recepted_dict.items()]
        msg_aspect = [msg.get_debug_info() for key, msg in self.aspect_dict.items()]
        # msg_aspect = [msg.get_debug_info() for msg in self.aspect_vec_old]

        if len(msg_recepted) == 0:
            msg = f'{self.star}: {self.score}分，是{self.lord_house_vec}宫主, 飞{self.house}宫，{msg_aspect}, 无互容接纳.'
        else:
            msg = f'{self.star}: {self.score}分，是{self.lord_house_vec}宫主, 飞{self.house}宫，{msg_aspect}, 被{msg_recepted}'

        # if self.star in {'天王', '海王', '冥王', '北交', '凯龙', '婚神', '上升', '中天', '下降', '天底', '富点'}:
        #     msg = f'{self.star}: 落{self.house}宫, {msg_aspect}'

        return msg


class Constellation:
    def __init__(self, name: str):
        self.name: str = name
        self.star_vec: List[str] = []


class House:
    def __init__(self, house_num: int, ruler: str, ruler_loc: int):
        self.house_num = house_num
        self.ruler = ruler
        self.ruler_loc = ruler_loc
        self.loc_star: List[str] = []
        self.constellation: str = ''

    def __str__(self):
        return f'{self.house_num}宫主{self.ruler} 落{self.ruler_loc}宫, {self.house_num}宫宫内落星:{self.loc_star}, 宫头星座:{self.constellation}'


class Affliction:
    def __init__(self, star: str):
        self.star = star  # 被克星
        self.level_1 = []  # 第一档灾星: 8r ≥ 1r ＞ 12r
        self.level_2 = []  # 第二档灾星: 土星 = 海王 = 冥王 = 天王
        self.level_3 = []  # 第三档灾星: 土星 = 凯龙

