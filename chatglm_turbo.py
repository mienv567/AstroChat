# -*- coding: utf-8 -*-
import configparser
import json
import os
import random
import time
import datetime
from typing import Dict, List
import streamlit as st
import zhipuai
from utils import greeting_msg, greeting_msg2
from utils import init_llm_knowledge_dict
from utils import time_loc_task, date_task, time_task, loc_task, confirm_task, ixingpan_task, moon_solar_asc_task
from core import Core

task_chain = [date_task, time_task, loc_task, confirm_task, ixingpan_task, moon_solar_asc_task]

def set_next_task():
    cur_task = st.session_state.cur_task

    if cur_task == task_chain[-1]:
        st.session_state.cur_task = None

    for i in range(len(task_chain)):
        if cur_task == task_chain[i] and i < len(task_chain) - 1:
            st.session_state.cur_task = task_chain[i + 1]
            print('cur_task is:', st.session_state.cur_task)
            break


def set_cur_task(cur):
    st.session_state.cur_task = cur


class FakeData:
    def __init__(self, data):
        self.data = data


def do_pipeline(bot_msg) -> str:
    queue = st.session_state.task_queue
    if len(queue) == 0:
        # TODO: 解盘结束，欢迎继续咨询每年运势
        pass

    cur_task = queue[0]

    if cur_task == time_loc_task:
        birthday, dist, is_dst, toffset, loc = _prepare_http_data(bot_msg)
        soup_ixingpan = _fetch_ixingpan_soup(dist=dist, birthday_time=birthday, dst=is_dst, female=1)

        print(birthday, dist, is_dst, toffset, loc)

        if birthday != '无' and loc != '无' and dist != '':
            st.session_state.task_queue.remove(time_loc_task)
            st.session_state.task_queue.remove(time_task)
            st.session_state.task_queue.remove(loc_task)

            msg = f'\n\n将按如下信息排盘：<br>出生日期:{birthday}\t出生地点:{loc}\t区域ID:{dist}\t日光时:{is_dst}'
            return msg


def add_user_history(text):
    msg = {'role': 'user', 'content': text}
    st.session_state.history.append(msg)


def add_robot_history(text):
    msg = {'role': 'assistant', 'content': text}
    st.session_state.history.append(msg)


def fake_robot_response(text):
    blocks = []
    while len(text) > 5:
        block_length = random.randint(2, 5)
        block = text[:block_length]

        d = FakeData(data=block)
        blocks.append(d)
        text = text[block_length:]

    # 处理剩余的文本
    if len(text) > 0:
        d = FakeData(data=text)
        blocks.append(d)

    return blocks


def fetch_chatglm_turbo_response(user_input):
    # if st.session_state.cur_task == time_loc_task:
        # user_input = prompt_time_loc.format(user_input)

    response = zhipuai.model_api.sse_invoke(
        model="chatglm_turbo",
        prompt=[
            {"role": "user", "content": user_input},
        ],
        temperature=0.95,
        top_p=0.7,
        incremental=True
    )

    # return response
    return response.events()


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


# 设置页面标题、图标和布局
st.set_page_config(page_title="桥下指北", page_icon=":robot:")
# st.set_page_config(page_title="桥下指北", page_icon=":robot:", layout="wide")

# 初始化历史记录和past key values
if "history" not in st.session_state:
    def init_session():
        zhipuai.api_key = st.session_state.llm_dict['chatglm_turbo']['token']

        # st.session_state.task_queue = [time_loc_task, date_task, time_task, loc_task, confirm_task, ixingpan_task, moon_solar_asc_task]
        st.session_state.history = []
        st.session_state.cur_task = task_chain[0]
        # st.session_state.birthday = ''
        # st.session_state.birthloc = ''
        st.session_state.date_of_birth = datetime.datetime.now().date()
        st.session_state.time_of_birth = datetime.time(12, 30)
        st.session_state.age = 0
        st.session_state.start_btn = 0
        st.session_state.finished_curl_natal = 0

        # st.session_state.province_of_birth = '北美洲'
        # st.session_state.city_of_birth = '美国'
        # st.session_state.area_of_birth = '加利福尼亚 旧金山'

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
    print('llm_dict size:', len(st.session_state.llm_dict))

    init_session()


if "past_key_values" not in st.session_state:
    st.session_state.past_key_values = None



# --------------------------------- 搞 Greeting --------------------
st.markdown("#### 占星机器人:rainbow[「小乔」]为您服务:tulip::cherry_blossom::rose::hibiscus::sunflower::blossom:   ")
st.markdown("> 占星服务，请选择:rainbow[「诞生日」]和:rainbow[「诞生地」]，建议精确到小时、区县。   ")
st.markdown("")

# --------------------------------- 搞生日 --------------------------
st.markdown('\n\n\n\n')
st.markdown(' ')

col_date, col_time = st.columns(2)

with col_date:
    def on_date_change():
        st.session_state.age = int(datetime.datetime.now().date().year - st.session_state.date_of_birth.year)
        st.session_state.start_btn = 0

        set_next_task()
        # update_birthday()

    label, fmt = ':date: 请选择生日', "YYYY-MM-DD"
    v = datetime.datetime(year=2000, month=1, day=20)
    today = datetime.datetime.now()
    min_v, max_v = datetime.date(today.year - 100, 1, 1), datetime.date(today.year + 1, 12, 31)

    st.date_input(label=label, format=fmt, key="date_of_birth", min_value=min_v, max_value=max_v, on_change=on_date_change)


with col_time:
    def on_time_change():
        st.session_state.start_btn = 0
        set_next_task()
        print('生日是 ', st.session_state.time_of_birth)
        # update_birthday()


    label = ':alarm_clock: 请选择生时'
    st.time_input(label=label, key='time_of_birth', on_change=on_time_change)


def update_birthday():
    # https://streamlit-emoji-shortcodes-streamlit-app-gwckff.streamlit.app/
    msg = f'将使用如下信息排盘 :crystal_ball: ：`{st.session_state.date_of_birth} {st.session_state.time_of_birth}, {st.session_state.province_of_birth} {st.session_state.city_of_birth} {st.session_state.area_of_birth}, 区位ID:{st.session_state.areaid}`'
    add_robot_history(f'{msg}')


# ------------------------------- 搞位置 -------------------------------
col_province, col_city, col_area = st.columns([0.3, 0.3, 0.4])
def on_loc_change():
    st.session_state.start_btn = 0

    p = st.session_state.province_of_birth
    c = st.session_state.city_of_birth
    a = st.session_state.area_of_birth

    # st.session_state.province_index = list(st.session_state.area_dict.keys()).index(st.session_state.province_of_birth)
    # st.session_state.city_index = list(st.session_state.area_dict[st.session_state.province_of_birth].keys()).index(st.session_state.city_of_birth)
    # st.session_state.area_index = list(st.session_state.area_dict[st.session_state.province_of_birth][st.session_state.city_of_birth].keys()).index(st.session_state.area_of_birth)

    # if p in st.session_state.area_dict and c in st.session_state.area_dict[p] and a in st.session_state.area_dict[p][c]:
    #     st.session_state.areaid = st.session_state.area_dict[p][c][a]

    # print(st.session_state.areaid, st.session_state.area_of_birth, option3)


with col_province:
    # 创建第一个下拉菜单
    # option1 = st.selectbox(label=':cn: 请选择诞生地', options=st.session_state.area_dict.keys(), key='province_of_birth', on_change=on_loc_change)
    option1 = st.selectbox(label=':cn: 请选择诞生地', index=st.session_state.province_index, options=st.session_state.area_dict.keys(), key='province_of_birth', on_change=on_loc_change)

with col_city:
    # 根据第一个下拉菜单的选项，更新第二个下拉菜单的选项
    # option2 = st.selectbox(label='1', options=st.session_state.area_dict[option1].keys(), key='city_of_birth', on_change=on_loc_change, label_visibility='hidden')
    option2 = st.selectbox(label='1', index=st.session_state.city_index, options=st.session_state.area_dict[option1].keys(), key='city_of_birth', on_change=on_loc_change, label_visibility='hidden')

with col_area:
    # option3 = st.selectbox(label='1', options=st.session_state.area_dict[option1][option2].keys(), key='area_of_birth', on_change=on_loc_change, label_visibility='hidden')
    option3 = st.selectbox(label='1', index=st.session_state.area_index, options=st.session_state.area_dict[option1][option2].keys(), key='area_of_birth', on_change=on_loc_change, label_visibility='hidden')


# ------------------------------- 搞Button 开始排盘 ----------------------
st.markdown(
    """
    <style>
    .stButton > button {
        float: right;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def on_button_click():
    st.session_state.start_btn = 1

    p,c,a = st.session_state.province_of_birth, st.session_state.city_of_birth, st.session_state.area_of_birth
    st.session_state.areaid = st.session_state.area_dict[p][c][a]

    # update_birthday()

    btime = f'{st.session_state.date_of_birth} {st.session_state.time_of_birth}'
    print(btime)

    core = Core(birthday=btime, province=st.session_state.province_of_birth, city=st.session_state.city_of_birth, area=st.session_state.area_of_birth)
    st.session_state.core = core

    # st.session_state.core.execute()
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


def filter_nested_dict(knowledge_dict, filter_keys):
    filtered_dict = {}
    for section_name, sub_dict in knowledge_dict.items():
        filtered_sub_dict = {}
        for sub_key, val in sub_dict.items():
            if sub_key in filter_keys:
                filtered_sub_dict[sub_key] = val
        if filtered_sub_dict:
            filtered_dict[section_name] = filtered_sub_dict

    print(filtered_dict)
    return filtered_dict


if st.session_state.finished_curl_natal:
    st.markdown('----')
    st.markdown('#### :rainbow[星图信息]')
    st.markdown(st.session_state.core.chart_svg_html, unsafe_allow_html=True)

    key_all = st.session_state.core.guest_desc_vec
    key_all.extend(st.session_state.core.star_loc_vec)
    key_all.extend(st.session_state.core.ruler_fly_vec)
    key_all.extend(st.session_state.core.llm_recall_key)
    key_all = list(set(key_all))
    filtered_dict = filter_nested_dict(st.session_state.knowledge_dict, key_all)

    for key, val in filtered_dict["日月星座组合-144种"].items():
        st.markdown('----')
        new_key = key[:4] + " " + key[4:]
        st.markdown(f'#### :rainbow[{new_key}]')
        st.markdown(f'> {val}')

    if "上升太阳星座" in filtered_dict:
        for key, val in filtered_dict["上升太阳星座"].items():
            if len(key) > 5:
                key = key[:4] + " " + key[4:]
            st.markdown('----')
            st.markdown(f'#### :rainbow[{key}]')
            st.markdown(f'> {val}')


    # 搞日月升
    # for key in st.session_state.core.llm_recall_key:
    #     st.markdown('----')
    #     st.markdown(f'#### :rainbow[{key}]')

    st.markdown(st.session_state.core.guest_desc_vec)
    st.markdown(st.session_state.core.star_loc_vec)
    st.markdown(st.session_state.core.ruler_fly_vec)
    # asc_key, asc_solar_key = st.session_state.core.get_asc_const()
    # solar_moon_key = st.session_state.core.get_solar_moon_const()
    # st.session_state.solar_moon_constell = solar_moon_key
    # st.session_state.asc_constell = asc_key
    # st.session_state.asc_solar_constell = asc_solar_key

    # st.session_state.chart_html = st.session_state.core.get_chart_svg()

    # add_robot_history(st.session_state.knowledge_dict['日月星座组合-144种'][solar_moon_key])


# 渲染聊天历史记录
for i, message in enumerate(st.session_state.history):
    if message['content'] == '':
        continue
    if message["role"] == "user":
        with st.chat_message(name="user", avatar="user"):
            st.markdown(message["content"])
    else:
        with st.chat_message(name="assistant", avatar="assistant"):
            st.markdown(message["content"])


if st.session_state.start_btn == 1:
    # 输入框和输出框
    with st.chat_message(name="user", avatar="user"):
        input_placeholder = st.empty()
    with st.chat_message(name="assistant", avatar="assistant"):
        message_placeholder = st.empty()


    user_input = st.chat_input("请输入问题... ")


    # 如果用户输入了内容,则生成回复
    if st.session_state.cur_task not in [time_task, date_task] and user_input:
        input_placeholder.markdown(user_input)
        add_user_history(user_input)

        response = fetch_chatglm_turbo_response(user_input)

        # llm_flag = False
        res_vec = []
        for event in response:
            response_data = event.data
            res_vec.append(response_data)
            message_placeholder.markdown(''.join(res_vec))

            if isinstance(event, FakeData):
                time.sleep(0.05)
            else:
                llm_flag = True

        # if llm_flag:
        #     pipeline_msg = do_pipeline(bot_msg=''.join(res_vec))

            # res_vec.append(pipeline_msg)

        # history.append({'content': ''.join(res_vec), 'role': "assistant"})
        add_robot_history(''.join(res_vec))

        # 更新历史记录和past key values
        # st.session_state.history = history
        # st.session_state.past_key_values = past_key_values


