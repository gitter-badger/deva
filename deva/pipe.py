#!/usr/bin/env python

"""Module enabling a sh like infix syntax (using pipes).
"""

import functools
import itertools
import socket
import sys
from contextlib import closing
from collections import deque
import dill


try:
    import builtins
except ImportError:
    import __builtin__ as builtins


__all__ = [
    'Pipe', 'tail', 'skip', 'all', 'any', 'average', 'count',
    'as_dict', 'as_set', 'permutations', 'netcat', 'netwrite',
    'traverse', 'concat', 'as_list', 'as_tuple', 'stdout', 'lineout',
    'tee', 'add', 'first', 'chain', 'select', 'where', 'take_while',
    'skip_while', 'aggregate', 'groupby', 'sort', 'reverse',
    'chain_with', 'islice', 'izip', 'passed', 'index', 'strip',
    'lstrip', 'rstrip', 'run_with', 'append', 'to_type', 'transpose',
    'dedup', 'uniq', 'to_dataframe', 'P', 'pmap', 'pfilter', 'post_to',
    'head', 'read', 'tcp_write'
]


class Pipe:
    """
    Represent a Pipeable Element :
    Described as :
    first = Pipe(lambda iterable: next(iter(iterable)))
    and used as :
    print [1, 2, 3] | first
    printing 1

    Or represent a Pipeable Function :
    It's a function returning a Pipe
    Described as :
    select = Pipe(lambda iterable, pred: (pred(x) for x in iterable))
    and used as :
    print [1, 2, 3] | select(lambda x: x * 2)
    # 2, 4, 6
    """

    def __init__(self, function):
        self.function = function
        functools.update_wrapper(self, function)

    def __ror__(self, other):  # |
        return self.function(other)

    def __rrshift__(self, other):  # 左边的 >>
        return self.function(other)

    def __rmatmul__(self, other):  # 左边的@
        return self.function(other)

    def __lshift__(self, other):  # 右边的<<
        return self.function(other)

    def __call__(self, *args, **kwargs):
        return Pipe(lambda x: self.function(x, *args, **kwargs))

    def __repr__(self):
        return '<func %s.%s in Pipe mode>' % (self.function.__module__, self.function)


@Pipe
def P(func):
    """
    [1,2,3]>>print@P
    """
    return Pipe(func)


@Pipe
def to_dataframe(iterable, orient='index'):
    """
    orient='index'
    orient='columne'
    """
    import pandas as pd
    return pd.DataFrame.from_dict(iterable, orient=orient)


@Pipe
def head(iterable, qte):
    "Yield qte of elements in the given iterable."
    for item in iterable:
        if qte > 0:
            qte -= 1
            yield item
        else:
            return


@Pipe
def tail(iterable, qte):
    "Yield qte of elements in the given iterable."
    return deque(iterable, maxlen=qte)


@Pipe
def skip(iterable, qte):
    "Skip qte elements in the given iterable, then yield others."
    for item in iterable:
        if qte == 0:
            yield item
        else:
            qte -= 1


@Pipe
def dedup(iterable, key=lambda x: x):
    """Only yield unique items. Use a set to keep track of duplicate data."""
    seen = set()
    for item in iterable:
        dupkey = key(item)
        if dupkey not in seen:
            seen.add(dupkey)
            yield item


@Pipe
def uniq(iterable, key=lambda x: x):
    """Deduplicate consecutive duplicate values."""
    iterator = iter(iterable)
    try:
        prev = next(iterator)
    except StopIteration:
        return
    yield prev
    prevkey = key(prev)
    for item in iterator:
        itemkey = key(item)
        if itemkey != prevkey:
            yield item
        prevkey = itemkey


@Pipe
def pmap(iterable, func):
    """Returns True if ALL elements in the given iterable are true for the
    given pred function"""
    return (func(x) for x in iterable)


@Pipe
def pfilter(iterable, func):
    """pfilter == where"""
    return (x for x in iterable if func(x))


@Pipe
def all(iterable, pred):
    """Returns True if ALL elements in the given iterable are true for the
    given pred function"""
    return builtins.all(pred(x) for x in iterable)


@Pipe
def any(iterable, pred):
    """Returns True if ANY element in the given iterable is True for the
    given pred function"""
    return builtins.any(pred(x) for x in iterable)


@Pipe
def average(iterable):
    """Build the average for the given iterable, starting with 0.0 as seed
    Will try a division by 0 if the iterable is empty...
    """
    total = 0.0
    qte = 0
    for element in iterable:
        total += element
        qte += 1
    return total / qte


@Pipe
def count(iterable):
    "Count the size of the given iterable, walking thrue it."
    count = 0
    for element in iterable:
        count += 1
    return count


@Pipe
def as_dict(iterable):
    return dict(iterable)


@Pipe
def as_set(iterable):
    return set(iterable)


@Pipe
def permutations(iterable, r=None):
    # permutations('ABCD', 2) --> AB AC AD BA BC BD CA CB CD DA DB DC
    # permutations(range(3)) --> 012 021 102 120 201 210
    for x in itertools.permutations(iterable, r):
        yield x


@Pipe
def netcat(to_send, host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.connect((host, port))
        for data in to_send | traverse:
            s.send(data.encode("utf-8"))
        while 1:
            data = s.recv(4096)
            if not data:
                break
            yield data


@Pipe
def netwrite(to_send, host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.connect((host, port))
        for data in to_send | traverse:
            s.send(data.encode("utf-8"))


@Pipe
def traverse(args):
    for arg in args:
        try:
            if isinstance(arg, str):
                yield arg
            else:
                for i in arg | traverse:
                    yield i
        except TypeError:
            # not iterable --- output leaf
            yield arg


@Pipe
def tcp_write(to_send, host='127.0.0.1', port=1234):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.connect((host, port))
        s.send(dill.dumps(to_send))
        s.send(b'\n')


@Pipe
def concat(iterable, separator=", "):
    return separator.join(map(str, iterable))


@Pipe
def as_list(iterable):
    return list(iterable)


@Pipe
def as_tuple(iterable):
    return tuple(iterable)


@Pipe
def stdout(x):
    sys.stdout.write(str(x))
    return x


@Pipe
def lineout(x):
    sys.stdout.write(str(x) + "\n")
    return x


@Pipe
def tee(iterable):
    for item in iterable:
        sys.stdout.write(str(item) + "\n")
        yield item


@Pipe
def write(iterable, fname, glue='\n'):
    with open(fname, 'w') as f:
        for item in iterable:
            f.write(str(item) + glue)

    return iterable


@Pipe
def add(x):
    return sum(x)


@Pipe
def first(iterable):
    return next(iter(iterable))


@Pipe
def chain(iterable):
    return itertools.chain(*iterable)


@Pipe
def select(iterable, selector):
    return (selector(x) for x in iterable)


@Pipe
def where(iterable, predicate):
    return (x for x in iterable if (predicate(x)))


@Pipe
def take_while(iterable, predicate):
    return itertools.takewhile(predicate, iterable)


@Pipe
def skip_while(iterable, predicate):
    return itertools.dropwhile(predicate, iterable)


@Pipe
def aggregate(iterable, function, **kwargs):
    if 'initializer' in kwargs:
        return functools.reduce(function, iterable, kwargs['initializer'])
    return functools.reduce(function, iterable)


@Pipe
def groupby(iterable, keyfunc):
    return itertools.groupby(sorted(iterable, key=keyfunc), keyfunc)


@Pipe
def sort(iterable, **kwargs):
    return sorted(iterable, **kwargs)


@Pipe
def reverse(iterable):
    return reversed(iterable)


@Pipe
def passed(x):
    pass


@Pipe
def index(iterable, value, start=0, stop=None):
    return iterable.index(value, start, stop or len(iterable))


@Pipe
def strip(iterable, chars=None):
    return iterable.strip(chars)


@Pipe
def rstrip(iterable, chars=None):
    return iterable.rstrip(chars)


@Pipe
def lstrip(iterable, chars=None):
    return iterable.lstrip(chars)


@Pipe
def run_with(iterable, func):
    return (func(**iterable) if isinstance(iterable, dict) else
            func(*iterable) if hasattr(iterable, '__iter__') else
            func(iterable))


@Pipe
def append(iterable, y):
    """追加元素到列表尾部，[]>>t('c')>>t('b') == ['c', 'b']"""
    if hasattr(iterable, '__iter__') and not isinstance(iterable, str):
        return iterable + type(iterable)([y])
    return [iterable, y]


@Pipe
def to_type(x, t):
    """转换类型 '3'>>to_type(int)==3"""
    return t(x)


@Pipe
def read(x, mode='r'):
    """ 按行读入文本文件，mode参数为读到方式 'xxx.log'>>read>>tail(2)"""
    with open(x, mode) as f:
        for line in f:
            yield line


@Pipe
def transpose(iterable):
    return list(zip(*iterable))


chain_with = Pipe(itertools.chain)
#[1,2,3]>> chain_with([4,5,6])>>to_list == [1,2,3,4,5,6]
islice = Pipe(itertools.islice)
#range(10)>>islice(2,100,2)>>to_list == [2,4,6,8]

# Python 2 & 3 compatibility
if "izip" in dir(itertools):
    izip = Pipe(itertools.izip)
else:
    izip = Pipe(zip)


@Pipe
def size(x):
    return sys.getsizeof(x)


from tornado import gen, httpclient


@Pipe
@gen.coroutine
def post_to(body, url='http://127.0.0.1:9999', headers=None):
    """ post a str to url,use async http client,Future对象，jupyter中可直接使用
    jupyter 之外需要loop = IOLoop.current(instance=True)，loop.start()
    :{'a':1}>>post_to(url)

    """
    if not isinstance(body, bytes):
        try:
            import json
            body = json.dumps(body)
        except:
            import dill
            body = dill.dumps(body)

    from tornado import httpclient
    http_client = httpclient.AsyncHTTPClient()
    headers = {}
    request = httpclient.HTTPRequest(
        url, body=body, method="POST", headers=headers)

    result = yield http_client.fetch(request)
    return result



# 转换内置函数为pipe
for i in builtins.__dict__.copy():
    f = 'to_'+i
    builtins.__dict__[f] = Pipe(builtins.__dict__[i])

if __name__ == "__main__":
    import doctest
    doctest.testfile('README.md')
