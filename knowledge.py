#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Time    : 12/16/23 21:09
# @Author  : jackietan@tencent.com
# @File    : parse_xingpan.py
import configparser
import pickle
import time
from typing import List, Dict
import numpy as np
import jieba
from numpy import ndarray

stopwords = ['不', '是', '和', '与', '这', '那', '个', '为', '以', '对', '好', '吗', '呢', '啊', '着', '了', '在']


class Knowledge:
    def __init__(self, guest_dict:Dict):
        for k, v in guest_dict.items():
            print(k)
        self.term_index = {}
        self.embedding_matrix = None
        self.stop_words = set()

        self.kv_dict = {}  # 过滤后的 knowledge_dict
        self.kv_embed_dict = {}

        # self.star_loc_dict = {}  # xx1宫
        # self.star_loc_dict_marriage = {}  # xx1宫
        #
        # self.star_fly_dict = {}  # xx非xx
        # self.star_aspect_dict = {}  # 太阳合月亮
        #
        # self.embed_star_loc = {}  # 太阳1宫：embedding
        # self.embed_star_loc_marriage = {}  # 太阳1宫：embedding
        #
        # self.embed_star_fly = {}
        # self.embed_aspect = {}

        """Load embedding_dict"""
        start_time = time.time()
        with open("./file/term_index.pkl", "rb") as file:
            self.term_index = pickle.load(file)

        with open("./file/embedding.pkl", "rb") as file:
            self.embedding_matrix = pickle.load(file)

        end_time = time.time()
        print('\nFinshed Load Embedding Dict... Cost:', end_time - start_time)

        """Load Stopwords"""
        with open('./file/stop_word.txt', 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                self.stop_words.add(line)
        print('Finished Load stop_word.txt...')

        self.filer_knowledge(guest_dict)

    def filer_knowledge(self, guest_dict: Dict):
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

        section_whitelist = ['行星落宫', '配偶-宫内星', '配偶-年龄', '宫主飞星', '行星相位']
        for section in section_whitelist:
            tmp = {k: v for k, v in llm_knowledge_dict[section].items() if k in guest_dict.keys()}
            tmp2 = {k: self._avg_pooling(v) for k, v in tmp.items()}
            self.kv_dict[section] = tmp
            self.kv_embed_dict[section] = tmp2

    def _avg_pooling(self, sentence) -> ndarray:
        key_segs = jieba.cut(sentence, cut_all=False)
        # print(f'Cut Word:{" ".join(list(key_segs))}')
        sentence = [item for item in key_segs if item not in self.stop_words]
        ids = [self.term_index.get(word, -1) for word in sentence]
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

    def cosine_similarity(self, a, b):
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        similarity = dot_product / (norm_a * norm_b)
        return similarity

    def find_top_n(self, question, top_n=50) -> List[str]:
        print('haha')
        q_embed = self._avg_pooling(question)
        # print(q_embed)

        final_vec = []
        for section, sub_dict in self.kv_embed_dict.items():
            similarity = {key: self.cosine_similarity(q_embed, value) for key, value in sub_dict.items()}
            sorted_similarity = sorted(similarity.items(), key=lambda x: x[1], reverse=True)
            top_n_similarity = sorted_similarity[:top_n]
            ret_vec = [f'{pair[0]},{self.kv_dict[section][pair[0]]}' for pair in top_n_similarity]
            final_vec.extend(ret_vec)

        # print('ret_star_loc:', ret_star_loc)
        for pair in final_vec:
            print(pair)

        return final_vec

def generate_embedding_file():
    term_dict = {}
    embedding_vec = []
    row = 0
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

    with open('./file/term_index.pkl', "wb") as file:
        pickle.dump(term_dict, file)

    with open('./file/embedding.pkl', "wb") as file:
        pickle.dump(embedding_matrix, file)


if __name__ == '__main__':
    k = Knowledge({})
    k.filer_knowledge({})
    # top_n_star_loc, top_n_star_fly, top_n_aspect = k.find_top_n_similar('我的财富如何？', 50)
    top_n_star_loc = k.find_top_n('我的财富如何？', 50)
    for pair in top_n_star_loc:
        print(pair)
    # k._avg_pooling('你好李焕英')
    # generate_embedding_file()
    # k.init(guest_dict={})
    # print(k._sentence_avg_pooling('你好李焕英'))
