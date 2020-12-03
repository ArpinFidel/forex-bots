import time

from helpers import logger as log

last_time = None

def start():
    global last_time
    last_time = time.time()

def elapsed():
    global last_time
    log.add()
    t = time.time() - last_time
    log.log(t)
    log.red()
    last_time = time.time()
    return t

def get_elapsed():
    global last_time
    t = time.time()
    el = t - last_time
    last_time = t
    return el
