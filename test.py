from tracer import Trace
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

def double_assignment_loop_fn(end_range):
    # x = 1
    some_dict = {"one": 1, "two": 2}
    for key, value in some_dict.items():
    # for i in list(range(end_range)):
        x = (key, value)


def loop_fn(end_range):
    # x = 1
    for i in range(end_range):
    # for i in list(range(end_range)):
        x = i
    return None


def complex_fxn():
    x = 6666
    #y = [x for x in range(5)]
    #y = {k: v for k, v in zip(["one", "two"], (1, 2))}
    ##<generator object complex_fxn.<locals>.<genexpr> at 0x7f1ae9ba2dc0>
    #y = (r for r in range(5))
    #y = Vector(0, 1)
    # context_manager()
    y = simple_fxn()
    # y = loop_fn(2)
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


@Trace()
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

@Trace()
def test_custom_objects(input_arg):
    input_arg = 321
    vect = Vector(0, 1)
    x = 10
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

@Trace()
def test_multi_line_statements(input_arg):
    string = "a String "
    # thirdVar = string * 2
    # here, other.update({ is the first traced line as opposed to other multi-line statements that start on the second line
    # other = {}
    # other.update({
    #     "hello": "world",
    #     "one": 1,
    #     "last": input_arg,
    #     # "last": thirdVar,
    # })

    def wtf(
            bruh
        ):
        return bruh

    for i in range(0,
                   2):
        x = i

    other = {
        "hello": "world",
        "one": 1,
        "last": input_arg,
        # "last": thirdVar,
    }
    # how do I check for when I am at the end of a multi-line statement

    # # if "one" in other and other["one"] \
    if other["one"] \
        and True:
        x = other
    else:
        x = 10

@Trace()
def test_function_call(input_arg):
    string = "a String "
    thirdVar = string * 2

    # x = 1
    x = list(range(10))
    x = complex_fxn() # NOTE: this is not getting marked as a change
    y = [2]
    y += ["a"]
    # NOTE: this is getting marked as a change for the next line not this one
    # but its getting added to the correct lines[-1]
    y = [12345]

    return y[-1]


@Trace()
def test_lots(input_arg):
    x = 10
    string = "a String "
    thirdVar = string * 2
    x = y = "different multiple assignment"

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
    try:
        x = 1
        x = 2
        fnn = 1
        fnn = lambda x: x * 10
        x = 1
        x = fnn(20)
    except:
        print("EXCEPT")
    finally:
        x = 99
    return z[-2]
    # return idk


@Trace()
def test_dict(input_arg):
    string = "a String "
    thirdVar = string * 2
    string = 'a'

    idk = {"hello": "world"} | {"yo": "hello!!"}
    return idk

@Trace()
def test_nested_loops(end_range):
    # x = 1
    before_1 = True
    for i in range(end_range):
        before_2 = True
        for j in range(end_range):
            before_3 = True
            for q in range(end_range):
                x = j
            after_3 = True
        after_2 = True
    after_1 = True
    x = before_1, before_3, before_2, after_1, after_2, after_3, x, j, i, q
    return None





if __name__ == "__main__":
    # call the function
    # idk = test_dict(666)
    # idk = test_function_call(444)
    test_nested_loops(3)

    # idk = test_multi_line_statements(444)
    # idk = test_custom_objects(123)
    # test_multiple_assignments(123)
