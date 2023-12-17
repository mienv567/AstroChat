# -*- coding: utf-8 -*-
import configparser
import json
from typing import Dict, Tuple, List
import re


greeting_msg = '您好，我是「桥下指北」自助占星机器人，请叫我小乔~~'
greeting_msg2 = '占星选择出生时间和地址，最好精确到小时和区县'

time_loc_task, date_task, time_task, loc_task, confirm_task, ixingpan_task, moon_solar_asc_task = '输入时间地点', '输入出生日期', '输入出生时间', '输入出生地点', '确认出生信息', '开始排盘', '日月升'
prompt_time_loc = '格式化下面问题中的时间、位置信息。\n返回格式为：时间:%Y-%m-%d %H:%M 位置：省市区。\n不要回复额外信息，如果问题中提取不到的信息就回复无，不要编造回答。\n问题：{}'

# 1992年8月4日 9点58分 地点:山东省济南市历下区
def init_llm_knowledge_dict():
    # print('Call init_llm_knowledge_dict...')
    llm_knowledge_dict: Dict[str, Dict[str, str]] = {}

    # Load knowledge_web.ini
    config = configparser.ConfigParser()

    file_name = './file/knowledge.ini'
    config.read(file_name)

    # 遍历指定section的所有option
    for section_name in config.sections():
        for option_name in config.options(section_name):
            value = config.get(section_name, option_name)

            if section_name in llm_knowledge_dict:
                llm_knowledge_dict[section_name][option_name] = value
            else:
                llm_knowledge_dict[section_name] = {option_name: value}

    return llm_knowledge_dict


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


def _parse_ixingpan_star(soup):
    '''
    解析包括：
        星体、四轴、富点、婚神、凯龙、北交
        落入星座
        落入宫位
    :param soup:
    :return:
    '''

    star_ruler_dict = get_session(SESS_KEY_STAR_RULER)
    star_dict = web.ctx.env[SESS_KEY_STAR]

    tables = soup.find_all('table')

    table = tables[5]
    tbody = table.find('tbody')
    trs = tbody.find_all('tr')
    for tr in trs:
        tds = tr.find_all('td')
        star = tds[0].text.strip()
        constellation_ori = tds[1].text.strip()
        house = tds[2].text.strip()

        constellation, degree, status = extract_constellation(constellation_ori)

        # constellation = pattern_constellation.sub('', constellation_ori).strip()

        match = pattern_house.search(house)

        if match:
            house = int(match.group())
        else:
            house = -1

        # 重新填充 star_dict
        if star in web.ctx.env['star_dict']:
            web.ctx.env['star_dict'][star].constellation = constellation

            if house != web.ctx.env['star_dict'][star].house:
                pass
                # print(f'{star} {star_dict[star].house} {house}')
        else:
            r = Star(star=star, house=house)
            r.constellation = constellation
            web.ctx.env['star_dict'][star] = r

        star_dict[star].degree = int(degree)
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
            is_exaltation = 1 if is_exaltation_ruler(star, constellation) else 0

        is_fall = 1 if status == '弱' else 0
        is_detriment = 1 if status == '陷' else 0
        is_triplicity = 1 if is_triplicity_ruler(star, constellation) else 0
        is_face = 1 if is_face_ruler(star, constellation) else 0
        is_term = 1 if is_term_ruler(star, constellation) else 0

        star_dict[star].is_domicile = is_domicile
        star_dict[star].is_exaltation = is_exaltation
        star_dict[star].is_fall = is_fall
        star_dict[star].is_detriment = is_detriment

        star_dict[star].is_triplicity = is_triplicity
        star_dict[star].is_face = is_face
        star_dict[star].is_term = is_term

        score = 5 * is_domicile + 4 * is_exaltation + 3 * is_triplicity + 2 * is_term + 1 * is_face - 4 * is_detriment - 5 * is_fall
        if star not in seven_star_list:
            score = -1

        star_dict[star].score = score

        if star in star_ruler_dict:
            star_dict[star].lord_house_vec = star_ruler_dict[star]

        if house != -1:
            web.ctx.env[SESS_KEY_HOUSE][house].loc_star.append(star)

        # logger.debug(f'-->星体:{star} 星座:{constellation} 度数:{degree} 庙:{is_domicile} 旺:{is_exaltation} 三:{is_triplicity} 界:{is_term} 十:{is_face}  得分:{score}\t宫神分:{web.ctx.env["star_dict"][star].score}宫位:{house}')

        # Update Constellation
        if star in constellation_whitelist:
            if constellation in get_session(SESS_KEY_CONST):
                get_session(SESS_KEY_CONST)[constellation].star_vec.append(star)
            else:
                c = Constellation(name=constellation)
                c.star_vec.append(star)
                web.ctx.env[SESS_KEY_CONST][constellation] = c


def _parse_ixingpan_aspect(soup):
    tables = soup.find_all('table')

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
        web.ctx.env['star_dict'][star_a].aspect_dict[star_b] = aspect_obj

        # 反过来填充
        aspect_obj_reverse = Aspect(star_b=star_a, aspect=aspect, degree=degree)
        web.ctx.env['star_dict'][star_b].aspect_dict[star_a] = aspect_obj_reverse


def parse_pan(dist, birthday, is_dst):
    # soup_ixingpan = _fetch_ixingpan_soup(dist=dist, birthday_time=birthday, dst=is_dst, female=1)
    _parse_ixingpan_house(soup_ixingpan)
    _parse_ixingpan_star(soup_ixingpan)
    _parse_ixingpan_aspect(soup_ixingpan)


if __name__ == '__main__':
    area_dict = load_ixingpan_area()
    print(area_dict)