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
from utils import init_llm_knowledge_dict
from utils import time_loc_task, date_task, time_task, loc_task, confirm_task, ixingpan_task, moon_solar_asc_task
from core import Core
from streamlit_date_picker import date_range_picker, PickerType, Unit, date_picker


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
st.set_page_config(page_title="MBTI助手", page_icon="🦈")
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
        st.session_state.filtered_dict = {}

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
    # print('llm_dict size:', len(st.session_state.llm_dict))

    init_session()


if "past_key_values" not in st.session_state:
    st.session_state.past_key_values = None



# --------------------------------- 搞 Greeting --------------------
st.markdown("##### :rainbow[MBTI助手] ")
st.caption("一个基于大数据的占星机器人")

st.markdown("> MBTI/星座服务，请选择您的 :rainbow[出生日期] 和 :rainbow[出生地点]，建议提供尽可能准确的小时和区县信息。")
# st.markdown("> MBTI/星座服务，请选择:rainbow[「诞生日」]和:rainbow[「诞生地」]，建议精确到小时、区县。   ")
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
    # st.write(label)
    st.time_input(label=label, key='time_of_birth', on_change=on_time_change, step=60)
    # date_picker(picker_type=PickerType.time.string_value, unit=Unit.minutes.string_value, key='time_of_birth')

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


def filter_nested_dict(knowledge_dict, filter_keys):
    filtered_dict = {}
    for section_name, sub_dict in knowledge_dict.items():
        filtered_sub_dict = {}
        for sub_key, val in sub_dict.items():
            if sub_key in filter_keys:
                filtered_sub_dict[sub_key] = val
        if filtered_sub_dict:
            filtered_dict[section_name] = filtered_sub_dict

    # print(filtered_dict)

    st.session_state.filtered_dict = filtered_dict
    return filtered_dict


def debug():
    msg = ['| section | key |', '| --- | --- |']
    for section, sub_dict in st.session_state.filtered_dict.items():
        for key, val in sub_dict.items():
            msg.append(f'|{section}|{key}|')

    st.markdown('\n'.join(msg))


topic_term_dict = {'高中前学业': ['学业-高中前'],
                   '高中后学业': ['学业-高中后'],
                   '婚姻': ['婚姻', '配偶'],
                   '财富': ['财富'],
                   '职业': ['职业'],
                   '恋爱': ['恋爱']}

def generate_context(intent_vec):
    filtered_dict = st.session_state.filtered_dict


    llm_dict = {}
    for section, sub_dict in filtered_dict.items():
        for skey, interpret in sub_dict.items():
            interpret = interpret.strip('。')
            for topic, svec in topic_term_dict.items():
                if topic not in intent_vec:
                    continue

                for term in svec:
                    if term in section or term in interpret:
                        if topic not in llm_dict:
                            llm_dict[topic] = []

                        llm_dict[topic].append(f'{skey} = {interpret}')

    final_context = []
    for k, svec in llm_dict.items():
        topic = f'\n关于{k}:'
        interpret = '\n'.join(svec)

        msg = f'{topic}\n{interpret}'
        final_context.append(msg)

    return '\n'.join(final_context)


def user_intent(query):
    def fetch_intent(user_input):
        response = zhipuai.model_api.invoke(
            model="chatglm_turbo",
            prompt=[
                {"role": "user", "content": user_input},
            ]
        )

        # print(response)
        # print(type(response))
        if response['success']:
            c = response['data']['choices'][0]['content']
            # print(c)
            # print(type(c))
            obj = json.loads(c)
            # print(obj)
            # print(type(obj))
            return json.loads(obj)['intent']
        else:
            return None


    prompt_template = f'从下面话题集合中找出query涉及的话题（可能涉及到多个话题），返回的结果限定在如下话题集合内，若集合中没有匹配到结果就返回空，不要编造；' \
                      '返回JSON格式的结果，要包含intent键，如：{"intent": ["婚姻", "财富"]}。' \
                      '\n话题集合：占星教学、高中前学业、高中后学业、婚姻、财富、职业、恋爱、健康、推运' \
                      f'\nquery：{query}'
    # print(prompt_template)

    intent_vec = fetch_intent(prompt_template)

    return intent_vec


def get_prompt(intent_vec, question='我的恋爱怎么样'):
    # prompt_template = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, NEVER try to make up an answer.
    # Context:{context}
    # Question: {question}
    # """
    context = generate_context(intent_vec)
    guest_info = '。\n'.join(st.session_state.core.guest_desc_vec)
    # question = '我的婚姻怎么样？'

    prompt_tmplate = f'现在你是一名占星师，' \
                     f'请仅根据提供的上下文和星盘信息回答问题，不要使用任何外部知识。如果你不知道答案，请直说你不知道，不要试图编造答案。\n' \
                     f'\n提示：若客户星盘中星体得分>=2要解读旺的部分，<-2解读衰的部分，严重受克也属于衰。' \
                     f'\n在上下文中，旺：表示星体得分>1时候，衰：表示星体得分<-1时候\n' \
                     f'\n\n上下文：{context}\n' \
                     f'\n星盘信息：{guest_info}\n' \
                     f'\n：{question}'

    prompt = f"""
    现在你是一名占星师，请仅根据提供的上下文回答问题，不要使用任何外部知识，如果你不知道答案，请直说你不知道，不要试图编造答案。
    提示：星盘信息和上下文以键值对的形式组织，通过匹配上下文中的键与星盘信息中的键，利用上下文的值来解读。当星盘中的星体得分大于等于1时，上下文中的旺势部分更有可能发生；而当得分小于等于-2时，上下文中的衰弱部分更有可能发生。
    
    上下文：{context}
    
    星盘信息：{guest_info}
    
    Question：{question}
    """

    print('\n')
    print(prompt)

    return prompt


if st.session_state.finished_curl_natal:
    st.markdown('----')
    st.markdown('#### :rainbow[星图信息]')
    st.markdown(st.session_state.core.chart_svg_html, unsafe_allow_html=True)

    key_all = []
    key_all.extend(st.session_state.core.guest_desc_vec)
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
    else:  # TODO：目前走http，之后抓下来（放小红书）
        # for k, v in st.session_state.core.interpret_asc.items():
        #     st.markdown('----')
        #     st.markdown(f'#### :rainbow[{k}]')
        #     st.markdown(f'> {v}')
        for k, v in st.session_state.core.interpret_dict.items():
            st.markdown('----')
            st.markdown(f'#### :rainbow[{k}]')
            st.markdown(f'> {v}')





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
    if user_input:
        input_placeholder.markdown(user_input)
        add_user_history(user_input)

        intent_vec = user_intent(query=user_input)
        print(intent_vec)
        print(type(intent_vec))

        if intent_vec is None or len(intent_vec) == 0:
            response = fake_robot_response('我只回答占星相关的问题哦~')
        elif '占星教学' in intent_vec:
            response = fake_robot_response('你好像在让我教你？我只能回答有限的占星问题哦~')
        else:
            final_user_input = get_prompt(question=user_input, intent_vec=intent_vec)
            # print(final_user_input)

            response = fetch_chatglm_turbo_response(final_user_input)

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

        add_robot_history(''.join(res_vec))
