import re
import warnings

import streamlit as st
from ui.snowchat_ui import message_func


st.set_page_config(page_title="MBTI助手", page_icon="🦈")
st.markdown("##### :rainbow[MBTI助手] ")
st.caption("一个基于大数据的占星机器人")


INITIAL_MESSAGE = [
    {"role": "user", "content": "Hi!"},
    {"role": "assistant", "content": "Hey 你有什么想问我的~"},
]


with open("ui/style.md", "r") as styles_file:
    styles_content = styles_file.read()


# st.sidebar.markdown(
#     "**Note:** <span style='color:red'>The snowflake data retrieval is disabled for now.</span>",
#     unsafe_allow_html=True,
# )

st.write(styles_content, unsafe_allow_html=True)

# Initialize the chat messages history
if "messages" not in st.session_state.keys():
    st.session_state["messages"] = INITIAL_MESSAGE

if "history" not in st.session_state:
    st.session_state["history"] = []

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

for message in st.session_state.messages:
    message_func(
        message["content"],
        True if message["role"] == "user" else False,
        True if message["role"] == "data" else False,
    )
