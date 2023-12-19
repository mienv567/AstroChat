# -*- coding: utf-8 -*-
import configparser
import json
from typing import Dict, Tuple, List
import re

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

    _parse_ixingpan_aspect(soup_ixingpan)


def generate_prompt():
    filtered_dict = init_llm_knowledge_dict()
    section_kv = {'高中前学业': ['学业-高中前'],
                  '高中后学业': ['学业-高中后'],
                  '婚姻': ['婚姻', '配偶'],
                  '财富': ['财富'],
                  '职业': ['职业'],
                  '恋爱': ['恋爱']}

    llm_dict = {}
    for section, sub_dict in filtered_dict.items():
        for skey, interpret in sub_dict.items():
            for topic, svec in section_kv.items():
                for term in svec:
                    if term in section or term in interpret:
                        if topic not in llm_dict:
                            llm_dict[topic] = []

                        llm_dict[topic].append(f'{skey} = {interpret}')

    final_context = []
    for k, svec in llm_dict.items():
        topic = f'\n下面关于{k}:'
        interpret = '\n'.join(svec)

        msg = f'{topic}\n{interpret}'
        final_context.append(msg)

    return '\n'.join(final_context)


if __name__ == '__main__':
    print(generate_prompt())
    #area_dict = load_ixingpan_area()
    #print(area_dict)