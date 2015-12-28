#!/usr/bin/python3
#-*- coding:utf-8  -*-
#app.py

'''
是一个简单的aiohttp的框架
'''

__author__ = 'xueqiang'

import asyncio
from aiohttp import web
import logging; logging.basicConfig(level=logging.INFO)

import os,json,time
from datetime import datetime

from  jinja2 import Environment,FileSystemLoader

import orm
from coroweb import add_routes,add_static

from config import configs 
from handlers import COOKIE_NAME,cookie2user

def init_jinja2(app,**kw):
    logging.info("init jinja2.....")
    options = dict(
        autoescape  = kw.get('autoescape',True),
        block_start_string = kw.get('block_start_string','{%'),
        block_end_string  = kw.get('block_end_string','%}'),
        variable_start_string = kw.get('variable_start_string','{{'),
        variable_end_string = kw.get('variable_end_string','}}'),
        auto_reload = kw.get('auto_reload',True)
        )
    path = kw.get('path',None)
    if path is None:
        path  = os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')

    logging.info('set jinja2 the template path:%s' % path)
    env = Environment(loader=FileSystemLoader(path),**options)
    filters = kw.get('filters',None)
    if filters is not None:
        for name,f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


@asyncio.coroutine
def logger_factory(app,handler):
    @asyncio.coroutine
    def loger(request):
        logging.info('Request:%s %s' % (request.method,request.path))
        return (yield from handler(request))
    return loger

@asyncio.coroutine
def auth_factory(app,handler):
    @asyncio.coroutine
    def auth(request):
        cookstr = request.cookies.get(COOKIE_NAME)
        request.__user__ = None
        user = yield from cookie2user(cookstr)
        if user:
            request.__user__ = user
        #定义强制登陆的访问页面
        if request.path.startswith("/manage") and request.__user__ is None :
            return web.HTTPFound("/signin")
        return (yield from handler(request))
    return auth

@asyncio.coroutine
def response_factory(app,handler):
    @asyncio.coroutine
    def response(request):
        r = yield from handler(request)
        
        logging.info("Response handler.... %s %s" % (type(r),str(r)))
        if isinstance(r,web.StreamResponse):
            return r
        
        if isinstance(r,bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        
        if isinstance(r,str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp

        if isinstance(r,dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r,ensure_ascii=False,default=lambda o:o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                #app['__templating__']是创建的一个envrionment
                user = getattr(request,'__user__',None)
                if user is not None:
                    r['user'] = user
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp

        if isinstance(r,int) and r >= 100 and r <= 600:
            return web.Response(r)

        if isinstance(r,tuple)  and len(r) ==2:
            t,m = r
            if isinstance(r,int) and r >= 100 and r <= 600:
                return web.Response(r,str(m))

        #default
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response

def datetime_filter(t):
    delta = int(time.time()-t) 
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)

    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

@asyncio.coroutine
def init(loop):
    '''各种初始化'''
    #初始化数据库连接池
    yield from orm.create_pool(loop=loop,**configs.db)

    #给aiohttp的web添加，拦截器middleware,
    #处理请求时，打印日志，处理请求以后，根据处理函数返回对象的类型，转换Response返回给aiohttp框架
    app = web.Application(loop=loop,middlewares=[
        logger_factory,auth_factory,response_factory
        ])

    #初始化jinja2
    init_jinja2(app,filters=dict(datetime=datetime_filter))
    #app.router.add_route("GET","/",index)
    #自动添加对应处理方法
    add_routes(app,'handlers')
    add_static(app)
    svr = yield from loop.create_server(app.make_handler(),configs.server.serverip,configs.server.port)
    logging.info("server start at : %s:%s" % (configs.server.serverip,configs.server.port))
    return svr

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.run_forever()