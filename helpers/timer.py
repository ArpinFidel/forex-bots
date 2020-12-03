import time

from helpers import logger as log

last_time = None

def start():
    global last_time
    last_time = time.time()

def elapsed():
    global last_time
    log.add()
    t = time.time()
    log.log(t - last_time)
    last_time = t
    log.red()
