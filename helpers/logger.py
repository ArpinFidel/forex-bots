__log_level = 0
def log( *args, **kwargs):
    print('\t'*__log_level, end='')
    print(*args, **kwargs)
    
def add(): 
    global __log_level
    __log_level += 1
    
def red():
    global __log_level
    __log_level = max(0, __log_level-1)

def has_log( func):
    def wrapper(*args, **kwargs):
        add()
        r = func(*args, **kwargs)
        red()
        return r
    return wrapper
