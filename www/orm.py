#!/usr/bin/python3
#-*- coding:utf-8  -*-
#orm.py

'''
访问数据库的orm框架,数据库连接池
'''

__author__ = 'xueqiang'

import asyncio,logging
import aiomysql


@asyncio.coroutine
def create_pool(loop,**kw):
    logging.info("create database connection pool....")
    global __pool
    __pool = yield from aiomysql.create_pool(
        host = kw.get('host','localhost'),
        port = kw.get('port',3306),
        user = kw['user'],
        password = kw['password'],
        db = kw['db'],
        charset = kw.get('charset','utf8'),
        autocommit  =  kw.get('autocommit',True),
        maxsize = kw.get('maxsize',10),
        minsize = kw.get('minsize',1),
        loop = loop
        )

@asyncio.coroutine
def select(sql,args,size=None):
    logging.info("SQL:%s,args:%s" % (sql,str(args)))
    global __pool
    with  (yield from __pool)  as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?','%s'),args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        logging.info("row returned：%s" % len(rs))
        return rs

@asyncio.coroutine
def execute(sql,args,autocommit=True):
    logging.info("SQL:%s,args:%s" % (sql,str(args)))
    global __pool
    with  (yield from __pool) as conn:
        if not  autocommit:
            yield from conn.begin()
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?','%s'),args or ())
            affected = cur.rowcount
            yield from cur.close()
            if not autocommit:
                yield from conn.commit()
        except BaseException as e:
            if not autocommit:
                yield from conn.rollback()
            raise 
        return affected
        
def create_args(num):
    L = []
    for n in range(num):
        L.append('?')

    return ', '.join(L)

class Field(object):
    """docstring for Field"""
    def __init__(self, name,column_type,primary_key,default):
        super(Field, self).__init__()
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s,%s,%s>' % (self.__class__.__name__,self.name,self.column_type)
        
class StringField(Field):
    def __init__(self,name,primary_key=False,default=None,column_type='varchar(100)'):
        super(StringField,self).__init__(name,column_type,primary_key,default)

class BooleanField(Field):
    def __init__(self,name,default=False):
        super(BooleanField,self).__init__(name,"boolean",False,default)

class IntegerField(Field):
    def __init__(self,name,primary_key=False,default=0):
        super(IntegerField,self).__init__(name,"bigint",primary_key,default)

class FloatField(Field):
    """docstring for FloatField"""
    def __init__(self, name,primary_key=False,default=0.0):
        super(FloatField, self).__init__(name,"real",primary_key,default)

class TextField(Field):
    def __init__(self,name,default=None):
        super(TextField,self).__init__(name,"text",False,default)
        
class ModelMetaclass(type):
    """docstring for ModelMetaclass"""
    def __new__(cls, name,bases,attrs):
        if name=='Model':
            return type.__new__(cls,name,bases,attrs)
        tableName = attrs.get('__table__',None) or name
        logging.info("found moduel:%s (table:%s)" % (name,tableName))
        mappings = dict()
        fileds  = []   #数据库中的字段名
        filed_keys = []   #对象属性key值

        primaryKey_key = None    #对象属性key值
        primaryKey = None    #数据库中的字段名

        for k,v in attrs.items():
            if isinstance(v,Field):
                logging.info("found the field:(%s,%s)" % (k,v))
                mappings[k] = v
                if v.primary_key:
                    #已经存在主键
                    if primaryKey:
                        raise StandardError('Duplicate primary key for field:%s' % k)
                    primaryKey = v.name
                    primaryKey_key = k
                else:
                    fileds.append(v.name)
                    filed_keys.append(k)

        if not primaryKey:
            raise StandardError('primary key not found')

        for k in mappings.keys():
            attrs.pop(k)

        escaped_field = list(map(lambda f : '%s' % f,fileds))
        attrs['__mappings__'] = mappings
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey
        attrs['__primary_key_key__'] = primaryKey_key
        attrs['__fileds__'] = fileds
        attrs['__fileds_keys__'] = filed_keys
        attrs['__select__'] = 'select %s,%s from %s ' % (primaryKey,', '.join(escaped_field),tableName)
        attrs['__insert__'] = 'insert into %s (%s,%s) values(%s)' % (tableName,', '.join(escaped_field),primaryKey,create_args(len(escaped_field)+1))
        attrs['__update__'] = 'update %s set %s where %s = ?' % (tableName,', '.join(map(lambda f : '%s = ?' % f,fileds)),primaryKey)
        attrs['__delete__'] = 'delete from %s where %s = ?' % (tableName,primaryKey)

        return type.__new__(cls,name,bases,attrs)

class Model(dict,metaclass=ModelMetaclass):
    """docstring for Model"""
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    #当类实例在属性通过__getattribute__未找到时，调用__getattr__
    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("'Model' object has no attribute '%s'" % key)

    def __setattr__(self,key,value):
        self[key] = value

    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):
        value = getattr(self,key,None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else  field.default
                logging.debug('using default value is for : %s %s' % (key,value))
                setattr(self,key,value)

        return value

    @classmethod
    @asyncio.coroutine
    def findall(cls,where=None,args=None,**kw):
        """查找满足条件的所有记录"""
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []

        orderBy = kw.get('orderBy',None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)

        limit = kw.get('limit',None)
        if limit:
            sql.append('limit')
            if isinstance(limit,int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit,tuple) and len(limit) == 2:
                sql.append('?,?')
                args.extend(limit)
            else:
                raise ValueError("Invalid limit value : %s" % str(limit))

        rstemp = yield from select(' '.join(sql),args)
        #r每个元素，应该是个tupple，怎么变成字典的呢？因为cls实例本身是继承dict?
        #cls是字典，那么r是tuple，转换成了字典
        #难道aiomysql返回的结果集，是个列表，列表元素是字典
        #如果需要支持数据库表字段与类字段不同，需要查询结果也要做处理。
        #因为查询结果，key值是数据库的字段名
        
        rslist = []
        for r in rstemp:
            rdict = dict()
            for k in cls.__fileds_keys__:
                if cls.__mappings__[k].name in r:
                    rdict[k] = r[cls.__mappings__[k].name]
            #主键
            if cls.__mappings__[cls.__primary_key_key__].name in r:
                rdict[cls.__primary_key_key__] = r[cls.__mappings__[cls.__primary_key_key__].name]

            rslist.append(cls(**rdict))
        
        return rslist

    @classmethod
    @asyncio.coroutine
    def findNumber(cls,selectField,where=None,args=None):
        sql  = ['select %s _num_  from %s' % (selectField,cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = yield from select(' '.join(sql),args,1)
        if len(rs) == 0:
            return None

        return rs[0]['_num_']

    @classmethod
    @asyncio.coroutine
    def find(cls,pk):
        rs = yield from select('%s where %s=?' % (cls.__select__,cls.__primary_key__),[pk],1)
        if  len(rs) == 0:
            return None

        rdict = dict()
        for k in cls.__fileds_keys__:
            if cls.__mappings__[k].name in rs[0]:
                rdict[k] = rs[0][cls.__mappings__[k].name]

        #主键
        if cls.__mappings__[cls.__primary_key_key__].name in rs[0]:
            rdict[cls.__primary_key_key__] = rs[0][cls.__mappings__[cls.__primary_key_key__].name]


        return cls(**rdict)

    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault,self.__fileds_keys__))
        args.append(self.getValueOrDefault(self.__primary_key_key__))
        rows = yield from execute(self.__insert__,args)
        if rows != 1:
            logging.warn("failed to insert, affected row:%d" % rows)

    @asyncio.coroutine
    def update(self):
        args = list(map(self.getValue,self.__fileds_keys__))
        args.append(self.getValue(self.__primary_key_key__))
        rows = yield from execute(self.__update__,args)
        if rows != 1:
            logging.warn("failed to update by primary key, affected row:%d" % rows)

    @asyncio.coroutine
    def remove(self):
        args=[self.getValue(self.__primary_key_key__)]
        rows = yield from execute(self.__delete__,args)
        if rows != 1:
            logging.warn("failed to delete by primary key, affected row:%d" % rows)
   
