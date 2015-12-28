#!/usr/bin/python3
#-*- coding:utf-8  -*-
#handlers.py

'''
定义相关路径的处理函数,需要带装饰器
'''

__author__ = 'xueqiang'


import time,hashlib,json,re,logging

from aiohttp import web
import asyncio

from apis import APIValueError,APIError,APIPermissionError
from coroweb import get,post
from models import User,Blog,next_id
from config import configs


_COOKIE_KEY = configs.session.secret
COOKIE_NAME = configs.session.name

def user2cookie(user,maxage):
    expires = str(int(time.time()+maxage))
    s = '%s-%s-%s-%s' % (user.id,user.passwd,expires,_COOKIE_KEY)
    L = [user.id,expires,hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

@asyncio.coroutine
def cookie2user(cookerstr):
    if not cookerstr:
        return None
        
    try:
        logging.info("cookerstr:%s" % cookerstr)
        L = cookerstr.split('-')
        if len(L) != 3:
            return None

        userid,expires,digest = L
        if int(expires) <= time.time():
            return None

        #获取用户信息
        user = yield from User.find(userid)
        if user is None:
            return None

        #验证session是否修改
        s = '%s-%s-%s-%s' % (userid,user.passwd,expires,_COOKIE_KEY)
        if digest != hashlib.sha1(s.encode('utf-8')).hexdigest():
            return None

        user.passwd = "******"

        return user
    except Exception as e:
        print(str(e))
        return  None
    
def get_int(strs):
    p = 1
    try:
        p = int(strs)
    except ValueError as e:
        pass
    if p <= 0 :
        p = 1
    return p

@get('/')
def index(*,page="1",pagesize="3"):
    #编写model，访问逻辑，获取数据
    page_index = get_int(page)     
    page_size = get_int(pagesize)
    num  = yield from Blog.findNumber('count(`id`)')
    #获取分页
    page_count = num // page_size  + (1 if num % page_size > 0 else 0)
    page_index = page_count if page_index  > page_count else page_index
    offset = page_size * (page_index - 1)
    pagedict = dict()
    pagedict['has_next'] = 1 if page_index < page_count else 0
    pagedict['has_previous'] = 1 if page_index > 1 else 0
    pagedict['page_index'] = page_index
    pagedict['previous'] = page_index-1 if  pagedict['has_previous'] == 1 else page_index
    pagedict['next'] = page_index+1 if  pagedict['has_next'] == 1 else page_index

    blogs = yield from Blog.findall(orderBy='created_at desc',limit=(offset, page_size))

    r = dict()
    r['__template__'] = 'blogs.html'
    
    r['blogs'] = blogs
    r['page']  = pagedict
    return r

@get('/register')
def register():
    return {
        '__template__':'register.html'
    }

@get('/signin')
def signin():
    return {
        '__template__':'signin.html'
    }

@get('/manage/blogs')
def manage_blogs(*,page='1'):
    return {
    '__template__':'manage_blog.html',
    'page_index':get_int(page)
    }

@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__':'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }

@get('/manage/blogs/edit')
def manage_edit_blog(*,id):
    return {
        '__template__':'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' % id
    }

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME,'-deleted-',max_age=0,httponly=True)
    logging.info("user sign out")
    return r

#正则表达式
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{30,40}$')

@post('/api/users')
def api_register_usr(*,email,name,passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')

    #验证邮箱是否重复
    users = yield from User.findall('`email`=?',email)
    if len(users) > 0:
        raise APIError('register:failed','email','邮箱已经注册')

    #密码保存成摘要
    uid =  next_id()
    sha1_passwd = '%s:%s' % (uid,passwd)
    #保存用户信息
    user =  User(id=uid,name=name.strip(),email=email,passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    yield from user.save()

    #返回给客户端JSON数据，包含cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
    user.passwd = '******'
    r.content_type ='application/json'
    r.body = json.dumps(user,ensure_ascii=False).encode('utf-8')
    return r

@post('/api/authenticate')
def authenticate(*,email,passwd):
    #判断参数合法
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')

    #获取用户信息
    user = yield from User.findall('`email`=?',email)
    if not user or len(user) != 1:
        raise APIError("signin:not regist","注册","没有该用户,请先注册")

    #验证用户密码是否正确
    #数据库的密码，是（id:客户端送的密码）计算的摘要值
    s = "%s:%s" % (user[0].id,passwd)
    if hashlib.sha1(s.encode("utf-8")).hexdigest() != user[0].passwd:
        raise APIPermissionError("用户密码错误")

    #设置cookie，并返回
    r = web.Response()
    r.set_cookie(COOKIE_NAME,user2cookie(user[0],86400),max_age=86400,httponly=True)
    user[0].passwd = "******"
    r.content_type ='application/json'
    r.body = json.dumps(user[0],ensure_ascii=False).encode('utf-8')
    return r

@post("/api/blogs")
def api_create_blog(request,*,name,summary,content):
    #检查用户是否具有编写日志的功能
    '''if request.__user__ is None or  not request.__user__.admin:
        raise APIPermissionError("没有权限编辑日志")'''

    if request.__user__ is None:
        raise APIPermissionError("没有权限编辑日志")

    #检查值
    if not name or not name.strip():
        raise APIValueError('name','name is empty')

    if not summary or not summary.strip():
        raise APIValueError('summary','summary is empty')

    if not content or not content.strip():
        raise APIValueError('content','content is empty')

    #生成Blog
    blog = Blog(userid=request.__user__.id,username=request.__user__.name,userimage=request.__user__.image,name=name.strip(),summary=summary.strip(),content=content.strip())
    yield from blog.save()

    return blog

@post('/api/blogs/{id}')
def api_update_blog(id,request,*,name,content,summary):
    #检查用户是否具有编写日志的功能
    '''if request.__user__ is None or  not request.__user__.admin:
        raise APIPermissionError("没有权限编辑日志")'''

    if request.__user__ is None:
        raise APIPermissionError("没有权限编辑日志")

    blog = yield from Blog.find(id)
     #检查值
    if not name or not name.strip():
        raise APIValueError('name','name is empty')

    if not summary or not summary.strip():
        raise APIValueError('summary','summary is empty')

    if not content or not content.strip():
        raise APIValueError('content','content is empty')

    #更新值
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    yield from blog.update()
    return blog


@get('/api/blogs')
def api_get_blogs(request,*,page='1',pagesize='3'):
    page_index = get_int(page)     
    page_size = get_int(pagesize)
    num  = yield from Blog.findNumber('count(`id`)',"user_id = '%s'" % request.__user__.id)
    #获取分页
    page_count = num // page_size  + (1 if num % page_size > 0 else 0)
    page_index = page_count if page_index  > page_count else page_index
    offset = page_size * (page_index - 1)
    pagedict = dict()
    pagedict['has_next'] = 1 if page_index < page_count else 0
    pagedict['has_previous'] = 1 if page_index > 1 else 0
    pagedict['page_index'] = page_index

    blogs = yield from Blog.findall(where="user_id = '%s'" % request.__user__.id,orderBy='created_at desc',limit=(offset, page_size))
    return dict(page=pagedict,blogs=blogs)




@get('/api/blogs/{id}')
def api_get_blog(*,id):
    blog = yield from Blog.find(id)
    return blog

@post('/api/blogs/{id}/delete')
def api_delete_blog(request,*,id):
    #检查用户是否具有编写日志的功能
    '''if request.__user__ is None or  not request.__user__.admin:
        raise APIPermissionError("没有权限编辑日志")'''
    if request.__user__ is None:
        raise APIPermissionError("没有权限编辑日志")
    blog =  yield from Blog.find(id)
    yield from blog.remove()
    return dict(id=id)



