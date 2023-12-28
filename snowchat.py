import re
import streamlit as st
from ui.snowchat_ui import message_func
import configparser
import json
import os
import random
import time
import datetime
from typing import Dict, List
import zhipuai
from utils import init_llm_knowledge_dict
from utils import time_loc_task, date_task, time_task, loc_task, confirm_task, ixingpan_task, moon_solar_asc_task
from core import Core
# from streamlit_date_picker import date_range_picker, PickerType, Unit, date_picker

st.set_page_config(page_title="MBTI助手", page_icon="🦈")
st.markdown("##### :rainbow[MBTI助手] ")
st.caption("一个基于大数据的占星机器人")

with open("ui/style.md", "r") as styles_file:
    styles_content = styles_file.read()

st.write(styles_content, unsafe_allow_html=True)
INITIAL_MESSAGE = [{"role": "user", "content": "Hi!"}, {"role": "assistant", "content": "Hey 你有什么想问我的~"}]


# st.sidebar.markdown(
#     "**Note:** <span style='color:red'>The snowflake data retrieval is disabled for now.</span>",
#     unsafe_allow_html=True,
# )


def load_knowledge_file():
    # Load knowledge_web.ini
    config = configparser.ConfigParser()

    knowledge_dict: Dict[str, Dict[str, str]] = {}
    file_name = './file/knowledge.ini'
    config.read(file_name)

    # 遍历指定section的所有option
    for section_name in config.sections():
        for option_name in config.options(section_name):
            value = config.get(section_name, option_name)

            if section_name in knowledge_dict:
                knowledge_dict[section_name][option_name] = value
            else:
                knowledge_dict[section_name] = {option_name: value}

    st.session_state.knowledge_dict = knowledge_dict


def load_ixingpan_area():
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

    return area_dict



# Initialize the chat messages history
if "messages" not in st.session_state.keys():
    st.session_state["messages"] = INITIAL_MESSAGE

    def init_session():
        zhipuai.api_key = st.session_state.llm_dict['chatglm_turbo']['token']

        st.session_state.history = []
        st.session_state.date_of_birth = datetime.datetime.now().date()
        st.session_state.time_of_birth = datetime.time(12, 30)
        st.session_state.age = 0
        st.session_state.start_btn = 0
        st.session_state.finished_curl_natal = 0
        st.session_state.filtered_dict = {}

        st.session_state.areaid = '4515'

        # 防止location重置(没用)
        st.session_state.province_index = 0
        st.session_state.city_index = 0
        st.session_state.area_index = 0

        # 日月升
        # st.session_state.solar_moon_constell = ''
        # st.session_state.asc_constell = ''
        # st.session_state.asc_solar_constell = ''

        load_knowledge_file()

    st.session_state.llm_dict = init_llm_knowledge_dict()
    st.session_state.area_dict = load_ixingpan_area()

    init_session()


if "history" not in st.session_state:
    st.session_state["history"] = []


st.markdown("> MBTI/星座服务，请选择您的 :rainbow[出生日期] 和 :rainbow[出生地点]，建议提供尽可能准确的小时和区县信息。")
# st.markdown("> MBTI/星座服务，请选择:rainbow[「诞生日」]和:rainbow[「诞生地」]，建议精确到小时、区县。   ")
st.markdown("")
st.markdown('\n\n\n\n')
st.markdown(' ')

# ---------------------------------Start 搞生日 --------------------------
col_date, col_time = st.columns(2)

with col_date:
    label, fmt = ':date: 请选择生日', "YYYY-MM-DD"
    v = datetime.datetime(year=2000, month=1, day=20)
    today = datetime.datetime.now()
    min_v, max_v = datetime.date(today.year - 100, 1, 1), datetime.date(today.year + 1, 12, 31)

    st.date_input(label=label, format=fmt, key="date_of_birth", min_value=min_v, max_value=max_v)

with col_time:
    label = ':alarm_clock: 请选择生时'
    # st.write(label)
    st.time_input(label=label, key='time_of_birth', step=60)
    # date_picker(picker_type=PickerType.time.string_value, unit=Unit.minutes.string_value, key='time_of_birth')
# ---------------------------------End 搞生日 --------------------------


# -------------------------------Start 搞位置 -------------------------------
col_province, col_city, col_area = st.columns([0.3, 0.3, 0.4])

with col_province:
    option1 = st.selectbox(label=':cn: 请选择诞生地', index=st.session_state.province_index, options=st.session_state.area_dict.keys(), key='province_of_birth')

with col_city:
    option2 = st.selectbox(label='1', index=st.session_state.city_index, options=st.session_state.area_dict[option1].keys(), key='city_of_birth', label_visibility='hidden')

with col_area:
    option3 = st.selectbox(label='1', index=st.session_state.area_index, options=st.session_state.area_dict[option1][option2].keys(), key='area_of_birth', label_visibility='hidden')
# -------------------------------End 搞位置 -------------------------------


# ------------------------------- 搞Button 开始排盘 ----------------------
st.markdown(""" <style> .stButton > button { float: right; } </style> """, unsafe_allow_html=True)

def on_button_click():
    st.session_state.start_btn = 1

    p,c,a = st.session_state.province_of_birth, st.session_state.city_of_birth, st.session_state.area_of_birth
    st.session_state.areaid = st.session_state.area_dict[p][c][a]

    btime = f'{st.session_state.date_of_birth} {st.session_state.time_of_birth}'
    print(btime)

    core = Core(birthday=btime, province=st.session_state.province_of_birth, city=st.session_state.city_of_birth, area=st.session_state.area_of_birth)
    st.session_state.core = core

    # 使用 chain 调用，可以显示 progress 进度条
    execute_chain = ['_init_knowledge_dict',
                     '_http_ixingpan',
                     '_parse_glon_glat',
                     '_parse_ixingpan_house',
                     '_parse_ixingpan_star',
                     '_parse_ixingpan_aspect',
                     '_is_received_or_mutal',
                     '_set_session_afflict',
                     'get_chart_svg',
                     '_parse_web_interpret',
                     'gen_guest_info']

    step_vol = int(100.0/len(execute_chain))
    # progress_bar = st.progress(0, text='排盘中，请稍后....')
    for i in range(len(execute_chain)):
        method_name = execute_chain[i]
        method = getattr(st.session_state.core, method_name)
        method()

        mysterious_wait = random.random() * 0.9 + 0.1
        time.sleep(mysterious_wait)
        progress_bar.progress((i + 1)*step_vol, text='排盘中，请稍后....')

    time.sleep(0.1)
    progress_bar.empty()

    st.session_state.finished_curl_natal = 1


st.button("开始排盘", type='primary', on_click=on_button_click)
progress_bar = st.progress(0, text='排盘中，请稍后....')
progress_bar.empty()



if st.session_state.finished_curl_natal:
    st.markdown('----')
    st.markdown('#### :rainbow[星图信息]')
    st.markdown(st.session_state.core.chart_svg_html, unsafe_allow_html=True)

    # key_all = []
    # key_all.extend(st.session_state.core.guest_desc_vec)
    # key_all.extend(st.session_state.core.star_loc_vec)
    # key_all.extend(st.session_state.core.ruler_fly_vec)
    # key_all.extend(st.session_state.core.llm_recall_key)
    # key_all = list(set(key_all))
    # filtered_dict = filter_nested_dict(st.session_state.knowledge_dict, key_all)
    #
    # for key, val in filtered_dict["日月星座组合-144种"].items():
    #     st.markdown('----')
    #     new_key = key[:4] + " " + key[4:]
    #     st.markdown(f'#### :rainbow[{new_key}]')
    #     st.markdown(f'> {val}')
    #
    # if "上升太阳星座" in filtered_dict:
    #     for key, val in filtered_dict["上升太阳星座"].items():
    #         if len(key) > 5:
    #             key = key[:4] + " " + key[4:]
    #         st.markdown('----')
    #         st.markdown(f'#### :rainbow[{key}]')
    #         st.markdown(f'> {val}')
    # else:  # TODO：目前走http，之后抓下来（放小红书）
    #     # for k, v in st.session_state.core.interpret_asc.items():
    #     #     st.markdown('----')
    #     #     st.markdown(f'#### :rainbow[{k}]')
    #     #     st.markdown(f'> {v}')
    #     for k, v in st.session_state.core.interpret_dict.items():
    #         st.markdown('----')
    #         st.markdown(f'#### :rainbow[{k}]')
    #         st.markdown(f'> {v}')
    #



# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

    if prompt == 'sb':
        st.session_state.messages.append({"role": "assistant", "content": 'hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh'})

for message in st.session_state.messages:
    message_func(message["content"], message["role"])

