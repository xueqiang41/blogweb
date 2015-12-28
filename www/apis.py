#!/usr/bin/python3
#-*- coding:utf-8  -*-
#apis.py

'''
定义一些公用的函数，或者异常
'''

__author__ = 'xueqiang'

class APIError(Exception):
    """docstring for APIError"""
    def __init__(self, error,data='',message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message

class APIValueError(APIError):
    """输入的数错误或者异常"""

    def __init__(self,field,message=''):
        super(APIValueError, self).__init__('value:invaild',field,message)

class APIResourceNotFoundError(APIError):
    '''
    Indicate the resource was not found. The data specifies the resource name.
    '''
    def __init__(self, field, message=''):
        super(APIResourceNotFoundError, self).__init__('value:notfound', field, message)

class APIPermissionError(APIError):
    '''
    Indicate the api has no permission.
    '''
    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)
