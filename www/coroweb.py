#!/usr/bin/python3
#-*- coding:utf-8  -*-
#coroweb.py

'''
进一步封装aiohttp
aiohttp基于方法，与url，选择处理函数，而且该处理函数必须是coroutine（协程的）
框架做的事情是，不管上层，定义什么函数来处理什么url
这样，首先，需要让函数关联url，这样可以动态添加，让框架自动添加到aiohttp里面
使用装饰器，让上层函数，都把方法名与url关联，通过装饰器发送给框架。
通过类似：
@get("/path")

接着需要添加有装饰器的函数，放入框架中
每个处理函数可能需要,传递过来的request对象里面的某些参数值，那就再包装下函数，所以定义一个RequestHanlder,
让它可以被aiohttp调用，定义__call__。这里面就把request里面的值解析出来，加到处理函数的参数里面

add_route函数只能添加某个具体的函数
框架需要自动添加函数，就需要，解析指定模块的里面的函数

在aiohttp框架底层，调用coroutine的函数，传入request对象。
上面封装aiohttp的调用函数RequestHandle函数。
反过来，把具体处理的函数设定的参数，需要的参数，全部通过inspect模块解析出来。
如果处理函数有关键字参数或者命名的关键字参数或者有request参数
那么就从底层传上来原始的request对象中，根据方法和content-type获取其中的全部参数。
然后根据命名关键字参数，剔除上述过程获得的字典参数。只保留处理函数命名的关键字参数。
如果从最初的request获取的参数，不包括处理函数定义的命名关键字参数，那就返回客户端，请求发送参数

然后把最终的关键字参数kw，传递给处理函数。

通过这一系列的处理，处理函数只需要管理命名关键字参数。
'''

__author__ = 'xueqiang'


import functools,logging,inspect,os
from aiohttp import web
import asyncio
from urllib import parse
from apis import APIError


def get(path):
    """定义一个装饰器@get('/path')"""
    def decorator(func):
        #真正的装饰函数
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator




def post(path):
    """定义一个装饰器@post('/path')"""
    def decorator(func):
        #真正的装饰函数
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator




class RequestHandler(object):
    """docstring for RequestHandler"""
    def __init__(self, app,fn):
        super(RequestHandler, self).__init__()
        self._app = app
        self._fn  = fn
        #分析fn函数的参数情况，方便把request本身或者request里面的值，传递给函数
        self._has_request_arg = RequestHandler.has_request_arg(fn)
        self._has_var_kw_arg = RequestHandler.has_var_kw_arg(fn)
        self._has_named_kw_arg = RequestHandler.has_named_kw_arg(fn)
        self._named_kw_arg = RequestHandler.get_named_kw_arg(fn)
        self._required_kw_arg = RequestHandler.get_required_kw_arg(fn)

    @staticmethod
    def get_required_kw_arg(fn):
        args = []
        params = inspect.signature(fn).parameters
        for name,param in params.items():
            if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
                args.append(name)
        return tuple(args)

    @staticmethod
    def get_named_kw_arg(fn):
        args = []
        params = inspect.signature(fn).parameters
        for name,param in params.items():
            if param.kind == inspect.Parameter.KEYWORD_ONLY:
                args.append(name)
        return tuple(args)

    @staticmethod
    def has_named_kw_arg(fn):
        '''判断函数是否有命名关键字参数'''
        params = inspect.signature(fn).parameters
        for name,param in params.items():
            if param.kind == inspect.Parameter.KEYWORD_ONLY:
                return True


    @staticmethod
    def has_var_kw_arg(fn):
        '''判断函数是否有关键字参数'''
        sig = inspect.signature(fn)
        params = sig.parameters
        found = False
        for name,param in params.items():
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                found = True
                break
        return found

    @staticmethod
    def has_request_arg(fn):
        '''判断函数对象，是否有一个request参数'''
        sig = inspect.signature(fn)
        params = sig.parameters
        found = False
        #是否有request参数，且request参数后不能包含可变参数、关键字参数、命名关键字参数
        for name,param in params.items():
            if name == 'request':
                found = True
                continue
            if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
                raise ValueError("request parameter must be the last named parameter in function:%s%s" % (fn.__name__,str(sig)))
        return found

    @asyncio.coroutine
    def __call__(self,request):
        '''该函数，是从aiohttp里面的request解析后，传递给处理函数的参数里面'''
        kw = None   #获取参数
        if self._has_var_kw_arg or self._has_named_kw_arg or self._has_request_arg:
            #根据方法类型，以及content-type获取参数
            if request.method == "POST":
                if not request.content_type:
                    return web.HTTPBadRequest('missing content_type')
                ct = request.content_type.lower()
                '''logging.info("content_type:%s" % ct)
                body =yield from  request.text()
                logging.info("content:%s" % body)
                '''
                if ct.startswith('application/json'):
                    params = yield from request.json()
                    if not isinstance(params,dict):
                        return web.HTTPBadRequest("json body must be object")
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params  = yield from request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest("Unsupported Content-type: %s" % ct)
            elif request.method == "GET":
                qs = request.query_string
                if qs:
                    kw =  dict()
                    for k,v in parse.parse_qs(qs,True).items():
                        kw[k] = v[0]

        #填充传给fn的参数
        if kw is  None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_arg:
                #remove all uname args
                #保存所有命名的参数
                copy = dict()
                for name in self._named_kw_arg:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            #检查命名参数,把match_info的参数放入kw
            for k,v in request.match_info.items():
                if k in kw:
                    logging.warning("duplicate arg name in named arg and kw args")
                kw[k] = v

        if self._has_request_arg:
            kw['request'] = request

        if self._required_kw_arg:
            for name in self._required_kw_arg:
                if not name  in kw:
                    return web.HTTPBadRequest("Missing argument:%s" % name)

        logging.info("call with args:%s " % str(kw))

        try:
            r = yield from self._fn(**kw)
            return r
        except APIError as e:
            return dict(error=e.error,data = e.data,message = e.message)
        

def add_static(app):
    '''添加静态页面的路径，到框架中'''
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
    app.router.add_static('/static/',path)
    logging.info("add static %s ==> %s" % ('/static/',path))


def add_route(app,fn):
    """该函数，向aiohttp的web框架，添加处理方法，fn方法是装饰后的函数"""
    method = getattr(fn,'__method__',None)
    path  = getattr(fn,'__route__',None)
    #加上判断是否传入了上面的值
    if path is None or method is None:
        raise ValueError('@get or @post is not define in %s' % str(fn))

    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info("add route %s %s ==> %s(%s)" % (method,path,fn.__name__,', '.join(inspect.signature(fn).parameters.keys())))
    #方法与url对应的函数，使用RequestHandler。底层的aiohttp会以函数方式调用RequestHandler
    app.router.add_route(method,path,RequestHandler(app,fn))



def add_routes(app,module_name):
    """该函数，通过传入的模块名，添加模块类被装饰了@get与@post的函数"""
    n = module_name.rfind('.')
    if n == -1:
        mod = __import__(module_name,globals(),locals())
    else:
        name  = module_name[n+1:]
        mod = getattr(__import__(module_name[:n],globals(),locals()),name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod,attr)
        if callable(fn):
            method = getattr(fn,'__method__',None)
            path = getattr(fn,'__path__',None)
            if method is not None or path is not None:
                add_route(app,fn)
