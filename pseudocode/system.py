import random



def RND():
    return random.random()

def RANDOMBETWEEN(start, end):
    if not (start < end):
        raise RuntimeError(f"{start} not less than {end}", None)
    return random.randint(start, end)