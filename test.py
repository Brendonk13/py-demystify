from tracer import trace

def complex_fxn():
    x = 6666
    if not x:
        pass
    else:
        x += 1
    y = "adsd"
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
def test_function_call(input_arg):
    string = "a String "
    thirdVar = string * 2

    y = 5
    y = simple_fxn()
    return simple_fxn()


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
    idk = test_function_call(666)
