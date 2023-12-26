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



if __name__ == '__main__':
    load_pickle()

    for k, svec in res_dict.items():
        match = re.search(r"水星\d+宫", k)

        if match:
        # if '1宫' in k and '11宫' not in k and '飞' not in k:
            print(f'\n\n{k}')

            final_vec = []
            for msg in svec:
                if isinstance(msg, list):
                    for sub_msg in msg:
                        if sub_msg not in final_vec:
                            final_vec.append(sub_msg)
                else:
                    if msg not in final_vec:
                        final_vec.append(msg)

            for i, msg in enumerate(final_vec):
                idx = i + 1
                print(f'解释{idx}、{msg}')

        '''
        if k == '太阳8宫':
            print('size:', len(svec))
            for msg in svec:
                print(type(msg))
                if isinstance(msg, list):
                    print(len(msg))
                    for sub_msg in msg:
                        print(f'\n{sub_msg}')
                else:
                    print(f'{msg}')
        '''
        # print(k, '-->',len(svec))
        # if len(svec) >= 1:
        #     print(k, '\t', len(svec))