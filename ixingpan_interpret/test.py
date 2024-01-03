#!/usr/bin/env python
# coding=utf-8

#########################################################################
#
# Copyright (c) 2017 Tencent Inc. All Rights Reserved
#
#########################################################################

import pickle, os
import re

"""
File: test.py
Author: root@tencent.com
Date: 2023/12/20 22:12:01
Brief: 
"""

res_dict = {}
load_size = 0

def load_pickle():
    global res_dict
    global load_size

    if os.path.exists('./data.pickle'):
        with open("data.pickle", "rb") as file:
            tmp = pickle.load(file)

        res_dict = tmp
        load_size = len(res_dict)
        print(f'Load Pickle File, size:{len(res_dict)}')

pattern = r'^(太阳|月亮|水星|金星|火星|木星|土星|冥王星|海王|天王|婚神)([1-9]|1[0-2])宫$'
pattern_sign = r'^(太阳|月亮|水星|金星|火星|木星|土星|冥王|海王|天王|婚神)(白羊|金牛|双子|巨蟹|狮子|处女|天秤|天蝎|射手|魔羯|水瓶|双鱼)$'
pattern_sign_tmp = r'^(太阳)(白羊|金牛|双子|巨蟹|狮子|处女|天秤|天蝎|射手|魔羯|水瓶|双鱼)$'

if __name__ == '__main__':
    load_pickle()

    for k, svec in res_dict.items():
        print(k)
        # if re.search(r'太阳.*(月亮)', k):
        #     print('\n',k)
        #     for msg in svec:
        #         if not isinstance(msg, list):
        #             print(msg)
        #         else:
        #             for sub_msg in msg:
        #                 print(sub_msg)
        # match = re.search(pattern_sign_tmp, k)
        #
        # if match:
        #     print(f'\n\n{k}')
        #
        #     final_vec = []
        #     for msg in svec:
        #         if isinstance(msg, list):
        #             for sub_msg in msg:
        #                 if sub_msg not in final_vec:
        #                     final_vec.append(sub_msg)
        #         else:
        #             if msg not in final_vec:
        #                 final_vec.append(msg)
        #
        #     for i, msg in enumerate(final_vec):
        #         idx = i + 1
        #         print(f'解释{idx}、{msg}')

