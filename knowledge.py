#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Time    : 12/16/23 21:09
# @Author  : jackietan@tencent.com
# @File    : parse_xingpan.py
import configparser
import pickle
import re
import time
from typing import List, Dict
import numpy as np
import jieba
from numpy import ndarray

from core import Core

stopwords = ['不', '是', '和', '与', '这', '那', '个', '为', '以', '对', '好', '吗', '呢', '啊', '着', '了', '在']
# fly_pattern = re.compile(r'(\d+)宫宫主飞(\d+)宫')  # 9宫主落1宫 --> 9宫宫主飞1宫
fly_pattern = re.compile(r"(\d+)宫宫主飞(\d+)宫")  # 9宫主落1宫 --> 9宫宫主飞1宫

section_whitelist = ['行星落宫', '命主星落宫',
                     '婚姻-婚神星', '配偶-宫内星', '配偶-年龄',
                     '恋爱-宫内星', '恋爱-飞星',
                     '学业-高中后', '学业-高中前',
                     '财富-2宫', '财富-福点']
                     #'宫主飞星', '行星相位']
topic_dict = {
    '财富-2宫': '财富,财运,赚钱,有钱,发财',
    '财富-福点': '财富,财运,赚钱,有钱,发财',
    '婚姻-婚神星': '婚恋,恋爱,结婚,配偶,对象,婚姻,老婆,老公,另一半',
    '配偶-宫内星': '婚恋,恋爱,结婚,配偶,对象,婚姻,老婆,老公,另一半',
    '配偶-年龄': '婚恋,恋爱,配偶,对象,婚姻,另一半,老婆,老公',
    '恋爱-宫内星': '婚恋,恋爱,配偶,对象,婚姻,另一半,老婆,老公',
    '恋爱-飞星': '婚恋,恋爱,配偶,对象,婚姻,另一半,老婆,老公',
    '学业-高中后': '考试,学习,学业,成绩,考试,考研,考本科',
    '学业-高中前': '考试,学习,学业,成绩,考试,考研,考本科',
    '行星落宫': '占星',
    '命主星落宫': '占星'
}


class RankItem:
    def __init__(self, section, key, interpret, similarity):
        self.section = section
        self.key = key
        self.interpret = interpret
        self.similarity = similarity

    def get_kv_str(self):
        return f'{self.key}={self.interpret}'

    def __str__(self):
        return f"Key: {self.key}, Sim: {self.similarity}, Section: {self.section}, Interpret: {self.interpret}"


class Knowledge:
    def __init__(self, guest_dict: Dict, ruler_fly_vec: List, core: Core, is_debug=False):
        print({k: '' for k, v in guest_dict.items()})
        print('\n')
        print(ruler_fly_vec)
        if False:
            for k in ruler_fly_vec:
                print('ruler_fly_vec:', k)
            print('\n---------------------')
            guest_dict = self._filter_ruler_fly(guest_dict, ruler_fly_vec, is_debug)
            for k, v in guest_dict.items():
                print('guest_dict: ', k)

        self.term_index = {}
        self.embedding_matrix = None
        self.stop_words = set()

        self.core = core

        self.kv_dict = {}  # 过滤后的 knowledge_dict
        self.kv_embed_dict = {}

        # Call Function
        self._load_file()
        self._filer_knowledge(guest_dict, is_debug)

    def find_top_n(self, question, top_n=50) -> List[str]:
        # print('haha')
        q_embed = self._avg_pooling(question)
        # print(q_embed)

        final_vec = []
        for section, sub_dict in self.kv_embed_dict.items():
            similarity = {key: self._cosine_similarity(q_embed, self._pooling_topic_interpret(interpret_embed, topic_dict[section])) for key, interpret_embed in sub_dict.items()}

            for key, sim in similarity.items():
                i = RankItem(section=section, key=key, interpret=self.kv_dict[section][key], similarity=round(sim, 4))
                final_vec.append(i)

        sorted_final_vec = sorted(final_vec, key=lambda x: x.similarity, reverse=True)
        sorted_final_vec = sorted_final_vec[:top_n]

        # print('\n\n\n')
        # for idx, i in enumerate(sorted_final_vec):
        #     print(f'{idx}、{i}')

        return [item.get_kv_str() for item in sorted_final_vec]

    def _filer_knowledge(self, guest_dict: Dict, is_debug=False):
        """初始化函数"""

        """ Load llm_knowledge.ini """
        llm_knowledge_dict: Dict[str, Dict[str, str]] = {}
        config = configparser.ConfigParser()
        config.read('./file/llm_knowledge.ini')

        for section_name in config.sections():
            for option_name in config.options(section_name):
                value = config.get(section_name, option_name)

                if section_name in llm_knowledge_dict:
                    llm_knowledge_dict[section_name][option_name] = value
                else:
                    llm_knowledge_dict[section_name] = {option_name: value}


        for section in section_whitelist:
            if is_debug:
                tmp = {k: v for k, v in llm_knowledge_dict[section].items() if k not in guest_dict.keys()}
            else:
                tmp = {k: v for k, v in llm_knowledge_dict[section].items() if k in guest_dict.keys()}
            tmp2 = {k: self._avg_pooling(v) for k, v in tmp.items()}
            self.kv_dict[section] = tmp
            self.kv_embed_dict[section] = tmp2

    def _avg_pooling(self, sentence) -> ndarray:
        key_segs = jieba.cut(sentence, cut_all=False)
        sentence = [item for item in key_segs if item not in self.stop_words]
        # print(sentence)

        ids = [self.term_index.get(word, -1) for word in sentence]
        # print(ids)
        # print(ids)
        # ids = [self.embedding_matrix.vocab.get(word, -1) for word in sentence]
        valid_ids = [id for id in ids if id != -1]

        if len(valid_ids) == 0:
            raise ValueError("No valid embeddings found for the given sentence")

        embeddings = self.embedding_matrix[valid_ids]
        # print(embeddings)
        pooled_vector = np.mean(embeddings, axis=0)

        # print(pooled_vector)

        return pooled_vector

    @staticmethod
    def _cosine_similarity(a, b):
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        similarity = dot_product / (norm_a * norm_b)
        return similarity

    def _load_file(self):
        """Load embedding_dict"""
        start_time = time.time()
        with open("./file/term_index.pkl", "rb") as file:
            self.term_index = pickle.load(file)
            print('Finished Load term_index.pkl, size:', len(self.term_index))

        with open("./file/embedding.pkl", "rb") as file:
            self.embedding_matrix = pickle.load(file)
            # print('Finished Load term_index.pkl, size:', len(self.term_index))

        end_time = time.time()
        print('\nFinshed Load Embedding Dict... Cost:', end_time - start_time)

        """Load Stopwords"""
        with open('./file/stop_word.txt', 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                self.stop_words.add(line)
        print('Finished Load stop_word.txt...')

    @staticmethod
    def _filter_ruler_fly(guest_dict, ruler_fly_vec: List[str], is_debug):
        # 9宫主落1宫 --> 9宫宫主飞1宫
        ret_dict = {}
        for k, interpret in guest_dict.items():
            matches = fly_pattern.findall(k)
            if len(matches) > 0:
                a = matches[0][0]
                b = matches[0][1]
                ret = f'{a}宫主落{b}宫'

                if is_debug:
                    if ret not in ruler_fly_vec:
                        ret_dict[k] = interpret
                else:
                    if ret in ruler_fly_vec:
                        ret_dict[k] = interpret
            else:
                print(f'k={k} not match...')
                ret_dict[k] = interpret

        return ret_dict

    @staticmethod
    def dump_embedding_file():
        term_dict = {}
        embedding_vec = []
        row = 0
        start_time = time.time()
        with open('/Users/tanzhen/Downloads/tencent-ailab-embedding-zh-d100-v0.2.0-s/tencent-ailab-embedding-zh-d100-v0.2.0-s.txt', 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                vec = line.split(' ')
                if len(vec) != 101:
                    print(f'tencent-ailab error, len is: {len(vec)},  {line}')
                    continue

                term = vec[0]
                embed = [float(item) for item in vec[1:]]
                term_dict[term] = row
                embedding_vec.append(embed)
                row += 1

        embedding_matrix = np.array(embedding_vec)
        print(f'term_dict size:{len(term_dict)}')
        print(f'embedding_vec:{len(embedding_vec)}')
        end_time = time.time()
        print('\nFinshed Load Embedding Dict... Cost:', end_time - start_time)

        with open('./file/term_index.pkl', "wb") as file:
            pickle.dump(term_dict, file)

        with open('./file/embedding.pkl', "wb") as file:
            pickle.dump(embedding_matrix, file)

    def _pooling_topic_interpret(self, interpret_embed: ndarray, topic_str: str):
        if topic_str == '占星':
            weighted_average = interpret_embed
        else:
            topic_embed = self._avg_pooling(topic_str)

            topic_weight = 0.35
            interpret_weight = 0.65
            weighted_average = (topic_embed * topic_weight) + (interpret_embed * interpret_weight)

        return weighted_average



if __name__ == '__main__':
    q = '我的恋爱怎么样'
    guest_dict = {'太阳1宫': '', '月亮11宫': '', '水星1宫': '', '金星12宫': '', '火星1宫': '', '木星5宫': '', '土星3宫': '', '天王5宫': '', '海王4宫': '', '冥王2宫': '', '婚神10宫': '', '福点3宫': '', '1宫射手': '', '2宫摩羯': '', '3宫水瓶': '' '', '8宫巨蟹': '', '9宫狮子': '', '10宫处女': '', '11宫天秤': '', '12宫天蝎': '', '1宫宫主飞5宫': '', '2宫宫主飞3宫': '', '3宫宫主飞3宫': '', '3宫宫主飞5宫': '', '4宫宫主飞4宫': '', '4宫宫主飞5宫': '', '5宫宫主飞1宫': '', '6宫宫': '', '10宫宫主飞1宫': '', '11宫宫主飞12宫': '', '12宫宫主飞1宫': '', '12宫宫主飞2宫': ''}
    ruler_fly_vec = ['9宫主落1宫', '8宫主落11宫', '7宫主落1宫', '10宫主落1宫', '6宫主落12宫', '11宫主落12宫', '5宫主落1宫', '12宫主落1宫', '1宫主落5宫', '4宫主落5宫', '2宫主落3宫', '3宫主落3宫']
    k = Knowledge(guest_dict=guest_dict, ruler_fly_vec=ruler_fly_vec, is_debug=False)
    k.find_top_n(question=q, top_n=10)
    # k = '2宫宫主飞3宫'
    # pattern = r"(\d+)宫宫主飞(\d+)宫"
    # matches = re.findall(pattern, k)
    #
    # if len(matches) > 0:
    #     print(matches[0][0])
    #     print(matches[0][1])
    # print(matches)

    # k = Knowledge({})
    # k._filer_knowledge({})
    # # top_n_star_loc, top_n_star_fly, top_n_aspect = k.find_top_n_similar('我的财富如何？', 50)
    # top_n_star_loc = k.find_top_n('我的财富如何？', 50)
    # for pair in top_n_star_loc:
    #     print(pair)
    # k._avg_pooling('你好李焕英')
    # k.init(guest_dict={})
    # print(k._sentence_avg_pooling('你好李焕英'))


    # Knowledge.dump_embedding_file()
