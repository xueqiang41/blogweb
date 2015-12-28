#!/usr/bin/python3
#-*- coding:utf-8  -*-
#config.py

'''
解析配置文件
'''

__author__ = 'xueqiang'

import config_default


class Dict(dict):
    '''重写dict类，让它支持点取功能'''
    def __init__(self,name=(),value=(),**kw):
        '''初始化，可以传入key，value对应的元祖'''
        super(Dict,self).__init__(**kw)
        for k,v in zip(name,value):
            self[k] = v

    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r'Dict object has no attribute %s'  % key)

    def __setattr__(self,key,value):
        self[key] = value

def merge(default,override):
    '''合并是以默认配置文件为基础的，重载配置文件里面只有在默认配置文件出现过的key才有用'''
    r = {}
    for k,v in default.items():
        if k in override:
            if isinstance(v,dict):
                r[k] = merge(v,override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r


def toDict(d):
    D = Dict()
    for k,v in d.items():
        D[k] = toDict(v) if isinstance(v,dict) else v
    return D

#获取默认的配置文件
configs = config_default.configs

#如果定义了重写的配置文件，就合并到默认的配置文件
try:
    import config_override
    configs = merge(configs,config_override.configs)
except ImportError:
    pass

#把字典转换操作更方便的方式
configs = toDict(configs)
