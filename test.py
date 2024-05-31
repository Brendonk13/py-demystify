from tracer import trace, Trace
import os

class Oth:
    def __init__(self, o):
        self.o = o

class Vector:
    def __init__(self, x, y, z=None):
        qq = "hello"
        # self.x = Oth(x)
        self.x = x
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
    x, y = 11, 22
    vect.y = y
    # vect.x.o = 99
    # vect.x.o = y
    # y = vect.x.o

    y = vect.x
    vect.x, b = 99, vect.x
    vect.x, vect.y = 99, vect.x

    # y = vect.x.o
    # vect.x.o, b = 99, vect.x.o
    # vect.x.o, vect.y = 99, vect.x.o

    # vect.x, b = 99, vect.x
    # vect.x.o = x
    # vect.x.o = y
    # vect.x, b = 99, x
    # a, b = "a", input_arg

@trace
def test_custom_objects(input_arg):
    input_arg = 321
    vect = Vector(0, 1)
    vect.x = 22
    x = list(a for a in [1,2])
    vect.x = x

    # vect = Vector(0, 1)
    # vect.x = 22
    # vect.x = 33
    # # vect = vect + Vector(0, 1)

    # vect.x = ["a"]
    vect.x = input_arg
    # vect = vect + Vector(0, 1)
    return vect.x

# @Trace()
# @trace
def test_multi_line_statements(input_arg):
    # string = "a String "
    # thirdVar = string * 2

    other = {
        "hello": "world",
        "one": 1,
        "last": input_arg,
        # "last": thirdVar,
    }

    # # if "one" in other and other["one"] \
    # if other["one"] \
    #     and True:
    #     x = other
    # else:
    #     x = 10

@Trace()
# @trace
def test_function_call(input_arg):
    string = "a String "
    thirdVar = string * 2

    x = list(range(10))
    y = [2]
    # print("==================", type(y))
    y += ["a"]

    return y[-1]


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
    idk = test_function_call(444)
    # idk = test_multi_line_statements(444)
    # idk = test_custom_objects(123)
    # test_multiple_assignments(123)
