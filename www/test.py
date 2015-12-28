#!/usr/bin/python3
#-*- coding:utf-8  -*-
#test.py

'''
是一个简单的aiohttp的框架
'''

__author__ = 'xueqiang'

import orm,asyncio
from models import User

def test(loop):
    yield from orm.create_pool(loop=loop,user='blogwebuser',password='blogwebuser',host='120.25.102.253',db='blogweb')

    u = User(name='Test', email='test@example.com', passwd='1234567890', image='about:blank')

    yield from u.save()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
    #loop.run_forever()
    loop.run_forever()