# -*- coding: utf-8 -*-
import configparser
from typing import Dict

greeting_msg = '您好，我是「桥下指北」自助占星机器人，请叫我小乔~~'
greeting_msg2 = '占星请输入出生时间和地址，最好精确到小时(默认用12点排盘)和区县，越准问答效果越好。 参考输入：\n> 出生时间: 2000.06.06 09:58； 地点: 山东省济南市历下区'

time_loc_task, time_task, loc_task, confirm_task, ixingpan_task, moon_solar_asc_task = '输入时间地点', '输入出生时间', '输入出生地点', '确认出生信息', '开始排盘', '日月升'
prompt_time_loc = '格式化下面问题中的时间、位置信息。\n格式为：时间:%Y-%m-%d %H:%M 位置：省市区，不要回复额外信息，如果问题中提取不到的信息就回复无，不要编造回答。\n问题：{}'


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
