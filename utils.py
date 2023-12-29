# -*- coding: utf-8 -*-
import configparser
import json
from typing import Dict, Tuple, List
import re

import zhipuai

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






if __name__ == '__main__':
    prompt_template = f'从下面话题集合中找出query涉及的话题（可能涉及到多个话题），返回的结果限定在如下话题集合内，若集合中没有匹配到结果就返回空，不要编造；' \
                      '返回JSON格式的结果，要包含intent键，如：{"intent": ["婚姻", "财富"]}。' \
                      '\n话题集合：教学类、高中前学业、高中后学业、婚姻、财富、职业、恋爱、健康、推运' \
                      f'\nquery：我的健康如何'
    print(prompt_template)

    print(response['intent'])
    #area_dict = load_ixingpan_area()
    #print(area_dict)