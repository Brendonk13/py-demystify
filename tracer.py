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
-- first the variables x, y, self are created in the LOCAL SCOPE BEFORE the new function call appends a set() to the prev_line_locals stack

"""




"""
Todo:
    - make loops work
        - for some reason we are adding loop variables too early when they are the first line in a function
        - problem is we are returning when we see a loop 
    - make if statements do replacement ie: if x: ==> if 10:
        -- what about if some_dict.get("key"):
    test: [] += [a]
    - return x, y, z()
    test function calls: x.append(Vector(x,y)) # x.append(Vector(1, 2))
    - object properties changing
        - del some_dict[key]
        - object.some_value = 10
    - y = {**other_dict, ...}
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
    prev_line_locals.append(set())
    # print("=================== APPEND", prev_line_locals)
    signature = fxn_name + fxn_args
    # print(cf.yellow('... calling'), signature)
    print(cf.yellow(f'... calling {signature}'))


def trace_this_func(fxn_name):
    # if fxn_name in list(should_trace): return True
    return True



def once_per_func_tracer(frame, event, arg):
    # how this works: -- this function is called each new function and it prints "calling {signature}" then returns the trace_lines tracer for the next part
    # print("===================================================================================================== once per func")
    global FIRST_FUNCTION
    global NEED_TO_PRINT_FUNCTION
    # print(f"FIRST_FUNCTION={FIRST_FUNCTION}")
    name = frame.f_code.co_name
    if event == 'call':
        fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
        # if fxn_args.startswith('()'): then no args
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
            # print("=============================================================")
            return trace_lines
        # print(inspect.getcomments(frame.f_code))
        # comments will need to be read from the file along with the lines they appear in

    print("=============== no tracer returned kinda")
    return once_per_func_tracer


def init_tracer_globals():
    cf.use_style("solarized")
    global prev_line_code
    # global prev_line_locals_dict
    global prev_line_locals
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
    # prev_line_locals = set()
    prev_line_locals = []
    # prev_line_locals_dict = dict()
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
        # print(cf.cyan(f'*  {prev_line_num[0]} │  '), f'{prev_line_code[0].lstrip(" ")}')
        PRINTED_LINE += [cf.cyan(f'*  {prev_line_num[0]} │  '), f'{prev_line_code[0].lstrip(" ")}']
    # else:
    #     # only exectuted on first iteration
    #     print() # was


def update_line_code(next_line_executed):
    prev_line_code[0] = next_line_executed

def update_line_num(line_num):
    prev_line_num[0] = line_num


def make_locals_hashable(curr_line_locals):
    # try:
    #     return set(curr_line_locals.items())
    hashable_locals = set()
    for var_name, value in curr_line_locals.items():
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
    global prev_line_locals

    # clear last results
    PRINTED_LINE.clear()
    ADDITIONAL_LINE.clear()

    curr_line_locals = frame.f_locals
    hashable_curr_line_locals = make_locals_hashable(curr_line_locals)
    # print("CURR LOCALS", curr_line_locals)
    if event == 'exception':
        name = frame.f_code.co_name
        fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
        signature = name + fxn_args
        print('The function call: %s produced an exception:\n' % signature)
        # tb = ''.join(traceback.format_exception(*arg)).strip()
        # print('%s raised an exception:%s%s' % (name, os.linesep, tb))
        #set a flag to print nothing else
        return


    # if not len(prev_line_locals[-1]):
    if not prev_line_locals[-1]:
        # appended for each new function call so we have variables local to the current function
        # prev_line_locals.update(set(curr_line_locals.items()))
        # prev_line_locals[-1].update(set(curr_line_locals.items()))
        print("========== prev_line_locals[-1] is empty, new:", hashable_curr_line_locals)
        # this happens when new functions are called and all the function args are added to locals at once right below
        prev_line_locals[-1].update(hashable_curr_line_locals)
        # prev_line_locals_dict.update(curr_line_locals)

    # print("trace lines locals", curr_line_locals)
    # print_code(frame.f_lineno)
    extract_original_code() # prints the current line about to execute

    # changed_values = update_locals(curr_line_locals)
    # think I should keep the prints elsewhere to increase modularity
    update_stored_vars(curr_line_locals, hashable_curr_line_locals)

    # print("prev line code", prev_line_code)
    skip_lane = "with" in prev_line_code[0]
    # if "with" in prev_line_code[0]:
    #     print("============", inspect.getframeinfo(frame), skip_lane)
        # print(dir(inspect.getframeinfo(frame))
        # print(dir(frame.f_code), frame.f_code.co_code.decode('utf-8'))
        # return

    print(*PRINTED_LINE)
    if ADDITIONAL_LINE:
        print(*ADDITIONAL_LINE)

    fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
    # if fxn_args.startswith('()'): then no args
    if NEED_TO_PRINT_FUNCTION:
        name = frame.f_code.co_name
        print_on_func_call(name, fxn_args)
        # here need to add curr_line_locals ???
        print("curr_line_locals", hashable_curr_line_locals)
        prev_line_locals[-1].update(hashable_curr_line_locals)
        NEED_TO_PRINT_FUNCTION = False

    # print("LOCALS", prev_line_locals[-1])
    if event == 'return':
        # first arg is fxn name
        print_on_return(frame.f_code.co_name, arg)

        # pop the function's variables
        # print("=================== POP ALL", prev_line_locals)
        # print("=================== POP", prev_line_locals[-1])
        prev_line_locals.pop()
        # print("=================== POP", prev_line_locals[-1])
        JUST_PRINTED_RETURN = True

    if len(prev_line_locals):
        print("locals", prev_line_locals[-1])
    next_line_executed = inspect.getframeinfo(frame).code_context[0].rstrip() if not skip_lane else ""
    # do this at the end since update_locals uses prev_line_code
    update_line_code(next_line_executed)
    update_line_num(frame.f_lineno)



def print_on_return(fxn_name, arg):
    global SELF_IN_LOCALS
    SELF_IN_LOCALS = False
    print('%s returned %r' % (fxn_name, arg))
    # print(f'{fxn_name} returned {arg}')
    # print() # was


def deal_with_lists(curr_line_locals):
    for key, val in curr_line_locals.items():
        # list's are unhashable so store as a tuple for now,
        # can probs make a hashable list wrapper class later on.
        # big inneficiency doing this err time.
        if isinstance(val, list):
            curr_line_locals[key] = tuple(val)


def update_stored_vars(curr_line_locals, hashable_curr_line_locals):
    """ need to make lists hashable somehow for storing lists in the set.
        maybe I store lists differently
        and give the option to search lists
        could eventually make it so u pass a parameter to @trace which
        will look thru lists and return the values changed in a list as well
        as the indices where they are found.
    """
    global SELF_IN_LOCALS
    deal_with_lists(curr_line_locals) # convert lists to tuples

    changed_values = {
        key: curr_line_locals[key] # now the key stores the new value
        for key,_
        in hashable_curr_line_locals - prev_line_locals[-1]
    }


    # Note on classes:
    #     def Vector(x, y)
    #     ...
    #     y = Vector(0, 1)
    # -- first the variables x, y, self are created in the LOCAL SCOPE BEFORE the new function call appends a set() to the prev_line_locals stack
    if not SELF_IN_LOCALS and "self" in changed_values:
        SELF_IN_LOCALS = True
        print("============== self in locals, returning...")
        return

    if NEED_TO_PRINT_FUNCTION:
        print("about to return, curr locals", curr_line_locals)
        # for ==> def loop_fn(end): for i in range(end): x = i
        # curr_line_locals is currently the function arg, and not the loop arg (i)
    gather_additional_data(changed_values)
    # print("hashable, prev_line_locals", hashable_curr_line_locals, prev_line_locals[-1])
    # print("CHANGED VARS", changed_values)

    # need to update since this is a set of pairs so we cant just update the value for this variable
    for key_val_pair in prev_line_k_v_pairs(changed_values):
        prev_line_locals[-1].remove(key_val_pair)

    # is this correct ?
    prev_line_locals[-1].update(make_locals_hashable(changed_values))


def assigned_constant():
    assignment = prev_line_code[0].split('=')[-1].strip()
    # print("assignment", assignment)

    # todo make this find dicts, differentiate between {1:1} and {1:1, **other_dict}
    if (assignment.isdigit()
        or search(r'^".*"$', assignment)
        or search(r"^'.*'$", assignment)
        or assignment.startswith('return')):
            return True
    return False


def gather_additional_data(changed_values):
    global PRINTED_LINE
    global ADDITIONAL_LINE
    if NEED_TO_PRINT_FUNCTION:
        # here, we return BEFORE entering a new function
        print("need to print function, returning...")
        # print("...locals", prev_line_locals[-1])
        return

    # have_printed = False
    for (var_name, old_value) in prev_line_locals[-1]:
    # for var_name in changed_values.keys():
    #     old_value = prev_line_locals[var_name]
        if var_name in changed_values:
            # have_printed = True
            # print(*PRINTED_LINE)
            # print(cf.red(f"  {var_name}={old_value}"), " ──>", cf.green(f"new '{var_name}' value: {changed_values[var_name]}"))
            ADDITIONAL_LINE += [cf.red(f"  {var_name}={old_value}"), "──>", cf.green(f"new value: {changed_values[var_name]}")]
            # print(cf.red(f"  {var_name}={old_value}"), "──>", cf.green(f"new value: {changed_values[var_name]}"))
            # print()

    if not assigned_constant():
        # have_printed = True
        # print(*PRINTED_LINE, cf.cyan(" #"), changed_values)
        # print("prev_line_locals", prev_line_locals[-1])
        assignment = prev_line_code[0].split('=')[-1].strip()
        if len(changed_values) > 1:
            raise ValueError("multiple values changed in one line")

        # assuming no spaces means its getting assigned a variable such as self.x = x
        if len(changed_values) == 0 and len(assignment.split()) == 1 and "(" not in assignment:
            # print("CHANGED, assignment", changed_values, assignment)
            var_name = assignment
            value = [value for key,value in prev_line_locals[-1] if key == var_name][0]
            # print("=========================")
            # print("CHANGED", changed_values)

        # ie: if not x:
        if not changed_values:
            return
        var_name = tuple(changed_values.keys())[0]
        value = tuple(changed_values.values())[0]
        if not isinstance(value, GeneratorType):
        # if "generator object" not in value:
            PRINTED_LINE += [cf.bold(cf.cyan(" #")), f"{var_name} = {value}"]
        # print(*PRINTED_LINE, cf.bold(cf.cyan(" #")), f"{var_name} = {value}")

    # if not have_printed:
    #     print(*PRINTED_LINE)

# change name(s) since I store var_name, value tuples, not key_val tup's
def prev_line_k_v_pairs(changed_values_keys):
    # need the previous values in order to remove them from "prev_line_locals"
    # ie: if x got changed to 10, this stores: (x, prev_value)
    # todo: change to generator
    return [
            (key, v)
            for (key, v) in prev_line_locals[-1]
            if key in changed_values_keys
    ]
