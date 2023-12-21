#!/usr/bin/env python
# coding=utf-8

#########################################################################
#
# Copyright (c) 2017 Tencent Inc. All Rights Reserved
#
#########################################################################

import pickle, os

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
        print(k, '-->',len(svec))
