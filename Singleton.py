# -*- coding: utf-8 -*-

import threading

class CSingleton(object):
    # objs_locker = Lock()
    #
    # def __new__(cls, *args, **kwargs):
    #     cls.objs_locker.acquire()
    #
    #     try:
    #         if '_inst' not in vars(cls):
    #             cls._inst = super(CSingleton, cls).__new__(cls, *args, **kwargs)
    #         return cls._inst
    #
    #     finally:
    #         cls.objs_locker.release()

    objs = {}
    objs_locker = threading.Lock()

    def __new__(cls, *args, **kv):
        if cls in cls.objs:
            return cls.objs[cls]['obj']

        cls.objs_locker.acquire()
        try:
            if cls in cls.objs:
                return cls.objs[cls]['obj']
            obj = object.__new__(cls)
            cls.objs[cls] = {'obj': obj, 'init': False}
            setattr(cls, '__init__', cls.decorate_init(cls.__init__))
        finally:
            cls.objs_locker.release()

        return cls.objs[cls]['obj']


    @classmethod
    def decorate_init(cls, fn):
        def init_wrap(*args):
            if not cls.objs[cls]['init']:
                fn(*args)
                cls.objs[cls]['init'] = True
            return
        return init_wrap