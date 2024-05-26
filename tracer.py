import sys
from types import GeneratorType
import inspect
import functools
import os
import traceback
from re import search
from colorama import Fore, Back, Style, init
import colorful as cf

# next: save this in git, see how it looks with printed on the same line and just fix formatting in general

# NEXT: WORK ON THE ASSIGNED_CONSTANT PART TO USE THE FUNCTION INTERPRET_EXPRESSION
# try to do a substitution for an if statement ?
# or commit the work and start working on the one that generates a file
# NEXT: when showing objects with changed fields, only record the field that changed, not both X and Y when only X is changed


# global classes don't work :(((
#class LineInformation:
#    fxn_locals=None
#    code=None
#    def __init__(self, fxn_locals=None, code=None):
#        pass
        # self.fxn_locals = fxn_locals
        # self.code = code

"""
Note on classes:
    def Vector(x, y)
    ...
    y = Vector(0, 1)
-- first the variables x, y, self are created in the LOCAL SCOPE BEFORE the new function call appends a set() to the prev_line_locals_stack stack

"""




"""
NOT WORKING:
    - make if statements do replacement ie: if x: ==> if 10:
        -- what about if some_dict.get("key"):
        -- and return y[-1]
        -- the python side of things may need to run "exec" to get these values however this may not be safe to do
        test function calls: x.append(Vector(x,y)) # x.append(Vector(1, 2))
    - object properties changing
        - object.some_value = 10

Done:
    - make loops work
    test: [] += [a]
    - return x, y, z()
    - del some_dict[key]
    some_dict[key] = 2

    *  63 │   y = {**{"some": "dict"}, **y}  # y = {'some': 'dict', 'one': 1, 'two': 22}
        y=(('one', 1), ('two', 22)) ──> new value: {'some': 'dict', 'one': 1, 'two': 22}


Todo:
    - ASYNC
    - Note: I think if statements wont work great since we wont show the code paths that dont execute and there is a chance we have to interpret those values ourselves
        -- this should be a flag "eval_all_branch_paths"
    - add more substitution logic for function calls and such
    ie: Vector(x,y) shows Vector(0, 1)
    -- same for loops -- maybe not possible though


    I think I need to use the dis module to find intermediate fxn return values

    INSTEAD OF:
        y=<generator object complex_fxn.<locals>.<genexpr> at 0x7ffb2d46ae90> ──> new value: <__main__.Vector object at 0x7ffb2d2caa10>
    WE DO:
        y=generator --> new value: Vector(0,1)
    ==> need to remember that signature for an object declaration

convert to file writing:
    - then I can just print things and not have intermediate functions print in order of execution
"""


"""
Not working:

    currently printing the next line number instead of the last one
    how I handle lists

    not sure if I should be using a set anymore ..
    cuz i gotta convert hella other stuff to set each time

    Returns:
        a returned value doesnt print unless its a reassignment
            y = 5
            y = othh()
            works

            y = othh()
            -- prints nothing
"""


# for attr in dir(frame.f_code):
# print("obj.%s = %r" % (attr, getattr(frame.f_code, attr)))


def print_on_func_call(fxn_name, fxn_args):
    # add to variable stack
    # pop from function stack when I leave)
    prev_line_locals_stack.append(set())
    signature = fxn_name + fxn_args
    print(cf.yellow(f'... calling {signature}'))


def on_return(frame, arg):
    global JUST_PRINTED_RETURN
    # first arg is fxn name
    print_on_return(frame.f_code.co_name, arg)

    # pop the function's variables
    prev_line_locals_stack.pop()
    JUST_PRINTED_RETURN = True

def trace_this_func(fxn_name):
    # if fxn_name in list(should_trace): return True
    return True



def once_per_func_tracer(frame, event, arg):
    # how this works: -- this function is called each new function and it prints "calling {signature}" then returns the trace_lines tracer for the next part
    # print("===================================================================================================== once per func")
    global FIRST_FUNCTION
    global NEED_TO_PRINT_FUNCTION
    name = frame.f_code.co_name
    if event == 'call':
        fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
        if "dictcomp" in name:
            print("DICTCOMP")
            return
        if "listcomp" in name:
            print("LISTCOMP")
            return
        if FIRST_FUNCTION:
            print_on_func_call(name, fxn_args)
            FIRST_FUNCTION = False
        else:
            NEED_TO_PRINT_FUNCTION = True

        if trace_this_func(name):
            return trace_lines
        # print(inspect.getcomments(frame.f_code))
        # comments will need to be read from the file along with the lines they appear in

    print("=============== no tracer returned kinda")
    return once_per_func_tracer


def init_tracer_globals():
    cf.use_style("solarized")
    global prev_line_code
    # global prev_line_locals_stack_dict
    global prev_line_locals_stack
    global prev_line_num

    global SELF_IN_LOCALS
    global PRINTED_LINE
    global ADDITIONAL_LINE
    global JUST_PRINTED_RETURN
    global FIRST_FUNCTION
    global NEED_TO_PRINT_FUNCTION
    # use list to store string since lists are mutable.
    prev_line_code = ["0"]

    FIRST_FUNCTION = True
    NEED_TO_PRINT_FUNCTION = False
    JUST_PRINTED_RETURN = False
    PRINTED_LINE = []
    ADDITIONAL_LINE = []
    SELF_IN_LOCALS = False

    # is a set of var_name, val tuples.
    # ie: == { ('var_name1', "value1"), ('var_name2', 123), ... }
    # prev_line_locals_stack = set()
    prev_line_locals_stack = []
    # prev_line_locals_stack_dict = dict()
    prev_line_num = [0]



def trace(function):
    """
    trace the decorated function before changing back to default sys.gettrace value.
    """
    @functools.wraps(function)
    def setup_tracing(*args, **kwds):
        """
            use a try because of the finally functionality.
        """
        try:
            #done before decorated function
            old = sys.gettrace()
            init_tracer_globals()

            sys.settrace(once_per_func_tracer)
            return function(*args, **kwds) #executes decorated function
        finally:
            sys.settrace(old)
    return setup_tracing


def extract_original_code():
    global JUST_PRINTED_RETURN
    global PRINTED_LINE
    if JUST_PRINTED_RETURN:
        JUST_PRINTED_RETURN = False
        return

    # no print on first call (where value isss empty string
    if prev_line_code[0] != "0":
        # should do more stuff instead of always printing lstrip'd lines
        # need to show conditionals/their indentations better.
        PRINTED_LINE += [cf.cyan(f'*  {prev_line_num[0]} │  '), f'{prev_line_code[0].lstrip(" ")}']


def update_line_code(next_line_executed):
    prev_line_code[0] = next_line_executed

def update_line_num(line_num):
    prev_line_num[0] = line_num

def is_custom_object(name, value):
    return name != "self" and hasattr(value, "__dict__")
    # https://stackoverflow.com/a/52624678
    #^ wont work with __slots__
    # will only detect user defined types

def convert_to_set(locals):
    # try:
    #     return set(locals.items())
    hashable_locals = set()
    # for var_name, value in locals.items():
    for var_name, value in locals:
        if isinstance(value, dict):
            # todo: recurse over nested dicts
            hashable_locals.add((var_name, tuple(value.items())))
        elif isinstance(value, list):
            hashable_locals.add((var_name, tuple(value)))
        else:
            hashable_locals.add((var_name, value))
    return hashable_locals


def trace_lines(frame, event, arg):
    """ called before "next_line_executed" is ran, so we see the changes in frame.f_locals late
    """
    global PRINTED_LINE
    global ADDITIONAL_LINE
    global JUST_PRINTED_RETURN
    global NEED_TO_PRINT_FUNCTION
    global prev_line_locals_stack

    # clear last results
    PRINTED_LINE.clear()
    ADDITIONAL_LINE.clear()

    curr_line_locals_dict = frame.f_locals
    # curr_line_locals_set = convert_to_set(curr_line_locals_dict.items())
    # print("CURR LOCALS", curr_line_locals_dict)
    if event == 'exception':
        name = frame.f_code.co_name
        fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
        signature = name + fxn_args
        print('The function call: %s produced an exception:\n' % signature)
        # tb = ''.join(traceback.format_exception(*arg)).strip()
        # print('%s raised an exception:%s%s' % (name, os.linesep, tb))
        #set a flag to print nothing else
        return

    # if not len(prev_line_locals_stack[-1]):
    if not prev_line_locals_stack[-1]:
        # appended for each new function call so we have variables local to the current function
        # this happens when new functions are called and all the function args are added to locals at once right below
        # prev_line_locals_stack[-1].update(curr_line_locals_set)
        curr_line_locals_set = convert_to_set(curr_line_locals_dict.items())
        print("========== prev_line_locals[-1] is empty, new:", curr_line_locals_set)
        prev_line_locals_stack[-1].update(curr_line_locals_set)

    # prints the current line about to execute
    extract_original_code()

    # changed_values = update_locals(curr_line_locals_dict)
    # think I should keep the prints elsewhere to increase modularity
    # update_stored_vars(curr_line_locals_dict, curr_line_locals_set)
    update_stored_vars(curr_line_locals_dict)

    print(*PRINTED_LINE)
    if ADDITIONAL_LINE:
        print(*ADDITIONAL_LINE)

    if NEED_TO_PRINT_FUNCTION:
        # append set() to prev_line_locals_stack, then add the initial function args to this set
        add_new_function_args_to_locals(frame, curr_line_locals_dict)
        NEED_TO_PRINT_FUNCTION = False
    if event == 'return':
        on_return(frame, arg)

    # if len(prev_line_locals_stack):
        # print("locals", prev_line_locals_stack[-1])
        # print(list(val for _,val in prev_line_locals_stack[-1]))

    skip_lane = "with" in prev_line_code[0]
    next_line_executed = inspect.getframeinfo(frame).code_context[0].rstrip() if not skip_lane else ""
    # do this at the end since update_locals uses prev_line_code
    update_line_code(next_line_executed)
    update_line_num(frame.f_lineno)


def add_new_function_args_to_locals(frame, curr_line_locals_dict):
    """
        Append set() to prev_line_locals_stack,
        then add the initial function args to this set
    """
    name = frame.f_code.co_name
    fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
    print_on_func_call(name, fxn_args)
    curr_line_locals_set = convert_to_set(curr_line_locals_dict.items())
    prev_line_locals_stack[-1].update(curr_line_locals_set)



def print_on_return(fxn_name, arg):
    global SELF_IN_LOCALS
    SELF_IN_LOCALS = False
    print(f"{cf.cyan(f'{fxn_name} returned')} {arg}")


def make_dict_hashable(locals):
    for key, value in locals.items():
        # list's are unhashable so store as a tuple for now,
        # can probs make a hashable list wrapper class later on.
        # big inneficiency doing this err time.
        if isinstance(value, list):
            locals[key] = tuple(value)
        if isinstance(value, dict):
            # todo: recurse over nested dicts
            locals[key] = tuple(value.items())
            # hashable_locals.add((var_name, tuple(value.items())))

def add_object_fields_to_locals(curr_line_locals_dict):
    # curr_line_objects = convert_to_set(
    curr_line_objects = [
        (f"_TRACKED_{name}", vars(value))
        for name,value
        in curr_line_locals_dict.items()
        # in prev_line_locals_stack[-1]
        if is_custom_object(name, value)
    ]

    # add the objects to the hashset
    # curr_line_locals_set.update(curr_line_objects)

    # for each object, extract its fields (using vars) so we can track when their fields change
    for tracked_name, field_values in curr_line_objects:
        curr_line_locals_dict[tracked_name] = field_values

    make_dict_hashable(curr_line_locals_dict) # convert lists to tuples
    curr_line_locals_set = convert_to_set(curr_line_locals_dict.items())
    return curr_line_locals_set, curr_line_objects


def update_stored_vars(curr_line_locals_dict):
    """ need to make lists hashable somehow for storing lists in the set.
        maybe I store lists differently
        and give the option to search lists
        could eventually make it so u pass a parameter to @trace which
        will look thru lists and return the values changed in a list as well
        as the indices where they are found.
    """
    global SELF_IN_LOCALS

    curr_line_locals_set, curr_line_objects = add_object_fields_to_locals(curr_line_locals_dict)
    # new objects should be new and not "changed" ????
    new_variables = curr_line_locals_set - prev_line_locals_stack[-1]

    # Note: need curr_line_locals_dict since it is a dict and curr_line_locals_set is a set
    changed_values = {
        # key: curr_line_locals_dict[key] # now the key stores the new value
        key: curr_line_locals_dict[key] # now the key stores the new value
        for key,_
        in new_variables
    }

    # Note on classes:
    #     def Vector(x, y)
    #     ...
    #     y = Vector(0, 1)
    # -- first the variables x, y, self are created in the LOCAL SCOPE BEFORE the new function call appends a set() to the prev_line_locals_stack stack
    if not SELF_IN_LOCALS and "self" in changed_values:
        SELF_IN_LOCALS = True
        print("============== self in locals, returning...")
        return

    if NEED_TO_PRINT_FUNCTION:
        print("about to return, curr locals", curr_line_locals_dict)
        # for ==> def loop_fn(end): for i in range(end): x = i
        # curr_line_locals_dict is currently the function arg, and not the loop arg (i)


    gather_additional_data(changed_values, curr_line_objects)
    replace_old_values(changed_values)



def replace_old_values(changed_values):
    # need to update since this is a set of pairs so we cant just update the value for this variable
    # remove old values according to changed_values
    for key_val_pair in prev_line_k_v_pairs(changed_values):
        prev_line_locals_stack[-1].remove(key_val_pair)

    # replace old  old values according to changed_values
    prev_line_locals_stack[-1].update(convert_to_set(changed_values.items()))

def assigned_constant():
    expression = prev_line_code[0].split('=')[-1].strip()

    # todo make this find dicts, differentiate between {1:1} and {1:1, **other_dict}
    if (expression.isdigit()
        or search(r'^".*"$', expression)
        or search(r"^'.*'$", expression)
        or expression.startswith('return')):
            return True
    return False


def gather_additional_data(changed_values, curr_line_objects):
    global ADDITIONAL_LINE
    if NEED_TO_PRINT_FUNCTION:
        # here, we return BEFORE entering a new function
        print("need to print function, returning...")
        return

    # add interpreted comment to the current line
    # ie show: * 123 | x = y  # x = 10
    if not assigned_constant():
        expression = prev_line_code[0].split('=')[-1].strip()
        interpret_expression(changed_values, curr_line_objects, expression)

    for (var_name, old_value) in prev_line_locals_stack[-1]:
        if var_name not in changed_values:
            continue
        new_value = changed_values[var_name]
        if var_name.startswith("_TRACKED"):
            # remove prefix: _TRACKED
            var_name = var_name[9:]
        ADDITIONAL_LINE += [cf.red(f"  {var_name}={old_value}"), "──>", cf.green(f"new value: {new_value}")]

def interpret_expression(changed_values, curr_line_objects, expression):
    global PRINTED_LINE
    # todo: maybe dont need this condition anymore, print prev_line_locals and see if it has both vect and _TRACKED_vect
    if len(changed_values) > 1 and not curr_line_objects:
        raise ValueError("multiple values changed in one line")

    # assuming no spaces means its getting assigned a variable such as self.x = x
    if len(changed_values) == 0 and len(expression.split()) == 1 and "(" not in expression:
        # Note: this conditional handles __init__()
        # Think this is supposed to do substitution
        var_name = expression
        value = [value for key,value in prev_line_locals_stack[-1] if key == var_name][0]
        PRINTED_LINE += [cf.bold(cf.cyan(" #")), f"{var_name} = {value}"]

    # ie: if not x:
    if not changed_values:
        return
    # print("changed", changed_values)
    # print("curr_line_objects", curr_line_objects)
    if curr_line_objects and len(changed_values) > 1:
        var_name = tuple(key for key in changed_values.keys() if key.startswith("_TRACKED"))[0]
        value = changed_values[var_name]
    elif len(changed_values) == 1:
        # value = tuple(val for val in changed_values.values() if key.startswith("_TRACKED"))
        var_name = tuple(changed_values.keys())[0]
        value = tuple(changed_values.values())[0]
    else:
        raise ValueError(f"Unexpected conditional case, changed_values: {changed_values}, curr_line_objects: {curr_line_objects}")
    if not isinstance(value, GeneratorType):
    # if "generator object" not in value:
        if var_name.startswith("_TRACKED"):
            var_name = var_name[9:]
        PRINTED_LINE += [cf.bold(cf.cyan(" #")), f"{var_name} = {value}"]

# change name(s) since I store var_name, value tuples, not key_val tup's
def prev_line_k_v_pairs(changed_values_keys):
    # need the previous values in order to remove them from "prev_line_locals_stack"
    # ie: if x got changed to 10, this stores: (x, prev_value)
    # todo: change to generator
    return [
            (key, v)
            for (key, v) in prev_line_locals_stack[-1]
            if key in changed_values_keys
    ]
