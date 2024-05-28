from tracer import trace
import os

class Oth:
    def __init__(self, o):
        self.o = o

class Vector:
    def __init__(self, x, y, z=None):
        qq = "hello"
        self.x = Oth(x)
        self.y = y
        # self._private = z
        # self.x, self.y = x, y

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)


def context_manager():
    x = 29
    with os.scandir(".") as entries:
        for entry in entries:
            x = 10

def loop_fn(end_range):
    # x = 1
    for i in range(end_range):
    # for i in list(range(end_range)):
        x = i


def complex_fxn():
    x = 6666
    #y = [x for x in range(5)]
    #y = {k: v for k, v in zip(["one", "two"], (1, 2))}
    ##<generator object complex_fxn.<locals>.<genexpr> at 0x7f1ae9ba2dc0>
    #y = (r for r in range(5))
    #y = Vector(0, 1)
    # context_manager()
    y = loop_fn(2)
    if not x:
        return
    else:
        x += 1
    y = "adsd"
    print("hello")
    return x


def simple_fxn():
    x = 6666
    # if not x:
    #     pass
    # else:
    #     x += 1
    y = "adsd"
    return x

@trace
def test_multiple_assignments(input_arg):
    vect = Vector(0, 1)
    x = 10
    # vect.x, b = 99, vect.x
    vect.x.o = x
    # vect.x, b = 99, x
    # a, b = "a", input_arg

@trace
def test_custom_objects(input_arg):
    input_arg = 321
    vect = Vector(0, 1)
    vect.x = 22
    x = list(a for a in [1,2])
    vect.x = x
    # vect.x = ["a"]
    vect.x = input_arg
    # vect = vect + Vector(0, 1)
    return vect.x

@trace
def test_function_call(input_arg):
    string = "a String "
    thirdVar = string * 2

    # if 1:
    #     x = 1
    # elif 2:
    #     x = 1
    # else:
    #     x = 1

    # vect = Vector(0, 1)
    # vect.x = 22
    # vect.x = 33
    # # vect = vect + Vector(0, 1)

    # y = {"one": 1, "two": 2}
    # del y["two"]
    # y["two"] = 22
    # y = {**{"some": "dict"}, **y}

    # y is a tuple for some reason, almost as if my tracer is changing the locals
    y = [2]
    # print("==================", type(y))
    y += ["a"]
    # if y + 1 * 3:
    #     y = 3
    # y = loop_fn(y)
    # y = simple_fxn()
    # return simple_fxn()
    # y = complex_fxn()
    # return complex_fxn()
    return y[-1]
    # return y[-1], simple_fxn()


@trace
def test_lots(input_arg):
    x = 10
    string = "a String "
    thirdVar = string * 2

    neerj = int('123d')
    x = simple_fxn()
    y = 5
    y = simple_fxn()
    for zz in range(4):
        x += zz

    oth = thirdVar.split() * 2
    neww = 666
    x = 20
    idk = {"hello": "world"}
    idk = list(range(30))
    z = idk + ["frig"] + [x]
    print(z)
    return z[-2]
    # return idk


@trace
def test_dict(input_arg):
    x = 10
    string = "a String "
    thirdVar = string * 2

    x = 20
    idk = {"hello": "world"}
    return idk



if __name__ == "__main__":
    # call the function
    # idk = test_dict(666)
    # idk = test_function_call(666)
    # idk = test_custom_objects(123)
    test_multiple_assignments(123)
