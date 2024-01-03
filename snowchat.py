import re
import streamlit as st

from knowledge import Knowledge
from ui.snowchat_ui import message_func, get_bot_message_container
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

st.set_page_config(page_title="MBTI 助手", page_icon="🦈")
st.markdown("##### :blue[MBTI 助手] ")
st.caption("一个基于大数据的占星对话机器人")

with open("ui/style.md", "r") as styles_file:
    styles_content = styles_file.read()

st.write(styles_content, unsafe_allow_html=True)
INITIAL_MESSAGE = [{"role": "user", "content": "Hi!"}, {"role": "assistant", "content": "Hey 你有什么想问我的~"}]



class FakeAnwser:
    def __init__(self, data):
        self.data = data


# st.sidebar.markdown(
#     "**Note:** <span style='color:red'>The snowflake data retrieval is disabled for now.</span>",
#     unsafe_allow_html=True,
# )


# Initialize the chat messages history
if "messages" not in st.session_state.keys():
    def load_knowledge_file():
        # Load knowledge_web.ini
        config = configparser.ConfigParser()

        knowledge_dict: Dict[str, Dict[str, str]] = {}
        file_name = './file/llm_knowledge.ini'
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

    # st.session_state["messages"] = INITIAL_MESSAGE
    st.session_state["messages"] = []

    def init_session():
        zhipuai.api_key = st.session_state.llm_dict['chatglm_turbo']['token']

        st.session_state.history = []
        st.session_state.date_of_birth = datetime.datetime.now().date()
        st.session_state.time_of_birth = datetime.time(12, 30)
        st.session_state.age = 0
        st.session_state.start_btn = 0
        st.session_state.is_curl_natal = 0
        st.session_state.filtered_dict = {}
        st.session_state.need_sun_moon_display = True
        st.session_state.need_asc_display = True

        st.session_state.areaid = '4515'

        # 防止location重置(没用)
        st.session_state.province_index = 0
        st.session_state.city_index = 0
        st.session_state.area_index = 0

        # Prompt Dict
        st.session_state.prompt_dict = {}

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
st.markdown("")
st.markdown('\n\n\n\n')
st.markdown(' ')

# ---------------------------------Start 搞生日 --------------------------
col_date, col_time = st.columns(2)

with col_date:
    v = datetime.datetime(year=2000, month=1, day=20)
    today = datetime.datetime.now()
    min_v, max_v = datetime.date(today.year - 100, 1, 1), datetime.date(today.year + 1, 12, 31)

    st.date_input(label=':date: 请选择生日', format="YYYY-MM-DD", key="date_of_birth", min_value=min_v, max_value=max_v)

with col_time:
    st.time_input(label=':alarm_clock: 请选择生时', key='time_of_birth', step=60)
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


# -------------------------------Start 搞Button 开始排盘 ----------------------
st.markdown(""" <style> .stButton > button { float: right; } </style> """, unsafe_allow_html=True)


def on_button_click():
    reset()
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

        mysterious_wait = random.random() * 0.5 + 0.1
        time.sleep(mysterious_wait)
        progress_bar.progress((i + 1)*step_vol, text='排盘中，请稍后....')

    time.sleep(0.1)
    progress_bar.empty()

    st.session_state.knowledge = Knowledge(guest_dict=get_attri('core').interpret_dict)

    st.session_state.is_curl_natal = 1

    st.session_state.prompt_dict = filter_nested_dict(st.session_state.knowledge_dict, get_attri('core').interpret_dict.keys())
    # print('hahahahah')
    # print(st.session_state.prompt_dict)
# -------------------------------End 搞Button 开始排盘 ----------------------


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


def filter_nested_dict(knowledge_dict, filter_keys):
    white_section = ['行星落宫']
    filtered_dict = {}
    for section_name, sub_dict in knowledge_dict.items():
        if section_name not in white_section:
            continue
        filtered_sub_dict = {}
        for sub_key, val in sub_dict.items():
            if sub_key in filter_keys:
                filtered_sub_dict[sub_key] = val
        if filtered_sub_dict:
            filtered_dict[section_name] = filtered_sub_dict

    # print(filtered_dict)

    st.session_state.filtered_dict = filtered_dict
    return filtered_dict


def show_chat_history():
    for message in st.session_state.messages:
        message_func(text=message["content"], role=message["role"])


def reset():
    st.session_state.is_curl_natal = 0
    st.session_state.start_btn = 0


# 参考流式 fake bot 回答
def fake_response(text) -> List[FakeAnwser]:
    blocks = []
    while len(text) > 7:
        block_length = random.randint(3, 7)
        block = text[:block_length]

        d = FakeAnwser(data=block)
        blocks.append(d)
        text = text[block_length:]

    # 处理剩余的文本
    if len(text) > 0:
        d = FakeAnwser(data=text)
        blocks.append(d)

    return blocks


def get_attri(key):
    if key not in st.session_state:
        return None
    else:
        return st.session_state[key]


def display_fake_message(response):
    bot_placeholder = None
    res_vec = []
    for event in response:
        response_data = event.data
        res_vec.append(response_data)

        container_content = get_bot_message_container(''.join(res_vec))
        if bot_placeholder is None:
            bot_placeholder = st.markdown(container_content, unsafe_allow_html=True)
        else:
            bot_placeholder.markdown(container_content, unsafe_allow_html=True)

        time.sleep(random.uniform(0.02, 0.15))

    st.session_state.messages.append({"role": "assistant", "content": ''.join(res_vec)})


def get_prompt(question='我的恋爱怎么样'):
    # prompt_template = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, NEVER try to make up an answer.
    # Context:{context}
    # Question: {question}
    # """
    # context = generate_context(intent_vec)
    # guest_info = '。\n'.join(st.session_state.core.guest_desc_vec)
    # question = '我的婚姻怎么样？'
    context_vec = []
    for k, v in st.session_state.prompt_dict['行星落宫'].items():
        msg = f'{k}={v}'
        context_vec.append(msg)

    context = '\n'.join(context_vec)

    prompt = f"""
    现在你是一名占星师，请根据上下文回答问题，不要使用任何外部知识，如果你不知道答案，请直说你不知道，不要试图编造答案。
    提示：上下文以键值对的形式组织。当星盘中的星体得分大于等于1时，上下文中的旺势部分更有可能发生；而当得分小于等于-2时，上下文中的衰部分更有可能发生。

    上下文：\n{context}
    Question：{question}
    """

    print('\n')
    print(prompt)

    return prompt


st.button("开始排盘", type='primary', on_click=on_button_click)
progress_bar = st.progress(0, text='排盘中，请稍后....')
progress_bar.empty()



if st.session_state.is_curl_natal:
    st.markdown('----')
    st.markdown('#### :blue[星图信息]')
    st.markdown(get_attri('core').chart_svg_html, unsafe_allow_html=True)
    st.markdown('----')


# 展示历史聊天
if st.session_state.is_curl_natal == 1:
    st.markdown('  ')
    show_chat_history()


# 展示日月星座的144中组合
if st.session_state.need_sun_moon_display \
        and get_attri('core') is not None \
        and get_attri('core').sun_moon_sign in get_attri('knowledge_dict')["日月星座组合-144种"]:
    st.session_state.need_sun_moon_display = False

    new_key = get_attri('core').sun_moon_sign
    sun_moon_answer = get_attri("knowledge_dict")["日月星座组合-144种"][new_key]
    sun_moon_answer = f'{new_key}\n{sun_moon_answer}'

    response = fake_response(sun_moon_answer)
    display_fake_message(response)


# 展示上升
if st.session_state.need_asc_display \
        and get_attri('core') is not None \
        and get_attri('core').asc_sign in get_attri('knowledge_dict')["上升太阳星座"]:
    st.session_state.need_asc_display = False

    key2 = get_attri('core').asc_sun_sign
    answer2 = get_attri("knowledge_dict")["上升太阳星座"][key2]

    new_key = get_attri('core').asc_sign
    sun_moon_answer = get_attri("knowledge_dict")["上升太阳星座"][new_key]
    sun_moon_answer = f'{new_key}\n{sun_moon_answer}\n{answer2}'

    response = fake_response(sun_moon_answer)
    display_fake_message(response)


# Prompt for user input and save
if st.session_state.is_curl_natal == 1:
    if user_input := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": user_input})
        message_func(text=user_input, role='user')

        recall = st.session_state.knowledge.find_top_n(user_input, top_n=3)

        # prompt = get_prompt(question=user_input)
        # response = fetch_chatglm_turbo_response(prompt)
        #
        # bot_placeholder = None
        # res_vec = []
        # for event in response:
        #     response_data = event.data
        #     res_vec.append(response_data)
        #
        #     container_content = get_bot_message_container(''.join(res_vec))
        #     if bot_placeholder is None:
        #         bot_placeholder = st.markdown(container_content, unsafe_allow_html=True)
        #     else:
        #         bot_placeholder.markdown(container_content, unsafe_allow_html=True)
        #
        # bot_answer = ''.join(res_vec)
        # st.session_state.messages.append({"role": "assistant", "content": bot_answer})

