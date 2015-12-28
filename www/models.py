#!/usr/bin/python3
#-*- coding:utf-8  -*-
#models.py

'''
具体数据库表对象类
'''

__author__ = 'xueqiang'

import time,uuid
from orm import Model,StringField,BooleanField,FloatField,TextField

def next_id():
    return "%015d%s000" % (int(time.time()*1000),uuid.uuid4().hex)

class User(Model):
    """docstring for User"""
    
    __table__ = 'users'

    id = StringField('id',primary_key=True,default=next_id,column_type='varchar(50)')
    email = StringField('email',column_type='varchar(50)')
    passwd = StringField('passwd',column_type='varchar(50)')
    admin = BooleanField('admin')
    name = StringField('name',column_type='varchar(50)')
    image = StringField('image',column_type='varchar(500)')
    create_at = FloatField('created_at',default=time.time)

class Blog(Model):
    """docstring for Blog"""
    
    __table__ = 'blogs'

    #测试使用
    id = StringField('id',primary_key=True,default=next_id,column_type='varchar(50)')
    userid = StringField('user_id',column_type='varchar(50)')
    username = StringField('user_name',column_type='varchar(50)')
    userimage = StringField('user_image',column_type='varchar(500)')
    name = StringField('name',column_type='varchar(50)')
    summary = StringField('summary',column_type='varchar(200)')
    content = TextField('content')
    create_at = FloatField('created_at',default=time.time)

class Comment(object):
    """docstring for Comment"""
    
    __table__ = 'comments'

    id = StringField('id',primary_key=True,default=next_id,column_type='varchar(50)')
    blogid = StringField('blog_id',column_type='varchar(50)')
    userid = StringField('user_id',column_type='varchar(50)')
    username = StringField('user_name',column_type='varchar(50)')
    userimage = StringField('user_image',column_type='varchar(500)')
    content = TextField('content')
    create_at = FloatField('created_at',default=time.time)

