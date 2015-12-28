#!/usr/bin/python3
#-*- coding:utf-8  -*-
#config_deault.py

'''
定义默认的配置文件
'''

__author__ = 'xueqiang'

configs = {
    'debug':True,
    'db':{
        'host': '120.25.102.253',
        'port': 3306,
        'user': 'blogwebuser',
        'password': 'blogwebuser',
        'db': 'blogweb'
    },
    'server':{
        'serverip':'0.0.0.0',
        'port':'9000'
    },
    'session':{
        'secret': 'blogweb',
        'name':'blogweb'
    }
}