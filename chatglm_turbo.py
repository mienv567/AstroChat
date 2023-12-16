# -*- coding: utf-8 -*-

import os
import random
import time
import datetime
from typing import Dict, List
import streamlit as st
import zhipuai
from utils import greeting_msg, greeting_msg2
from utils import init_llm_knowledge_dict, load_ixingpan_area
from utils import time_loc_task, date_task, time_task, loc_task, confirm_task, ixingpan_task, moon_solar_asc_task
from utils import _prepare_http_data, _fetch_ixingpan_soup
from utils import prompt_time_loc

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
    msg = f'将使用如下信息排盘 :crystal_ball: ：`{st.session_state.date_of_birth} {st.session_state.time_of_birth}, {st.session_state.province_of_birth} {st.session_state.city_of_birth} {st.session_state.area_of_birth}`'
    add_robot_history(f'{msg}')


# ------------------------------- 搞位置 -------------------------------
col_province, col_city, col_area = st.columns([0.3, 0.3, 0.4])
def on_loc_change():
    st.session_state.start_btn = 0


with col_province:
    # 创建第一个下拉菜单
    option1 = st.selectbox(label=':cn: 请选择诞生地', index=0, options=st.session_state.area_dict.keys(), key='province_of_birth', on_change=on_loc_change)

with col_city:
    # 根据第一个下拉菜单的选项，更新第二个下拉菜单的选项
    option2 = st.selectbox(label='1', index=0, options=st.session_state.area_dict[option1].keys(), key='city_of_birth', on_change=on_loc_change, label_visibility='hidden')

with col_area:
    option3 = st.selectbox(label='1', index=0, options=st.session_state.area_dict[option1][option2].keys(), key='area_of_birth', on_change=on_loc_change, label_visibility='hidden')


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
    update_birthday()

st.button("开始排盘", type='primary', on_click=on_button_click)


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


