import sys
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
Todo:
    create global set of values
    figure out the diff shit and q's i wrote down

    I think I need to use the dis module to find intermediate fxn return values

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

    return once_per_func_tracer


def init_tracer_globals():
    cf.use_style("solarized")
    global prev_line_code
    # global prev_line_locals_dict
    global prev_line_locals
    global prev_line_num

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


def print_code():
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

    if not len(prev_line_locals[-1]):
        # appended for each new function call so we have variables local to the current function
        # prev_line_locals.update(set(curr_line_locals.items()))
        # prev_line_locals[-1].update(set(curr_line_locals.items()))
        prev_line_locals[-1].update(hashable_curr_line_locals)
        # prev_line_locals_dict.update(curr_line_locals)

    # print("trace lines locals", curr_line_locals)
    # print_code(frame.f_lineno)
    print_code() # prints the current line about to execute

    # changed_values = update_locals(curr_line_locals)
    # think I should keep the prints elsewhere to increase modularity
    update_stored_vars(curr_line_locals, hashable_curr_line_locals)

    next_line_executed = inspect.getframeinfo(frame).code_context[0].rstrip()
    # do this at the end since update_locals uses prev_line_code
    update_line_code(next_line_executed)
    update_line_num(frame.f_lineno)

    print(*PRINTED_LINE)
    if ADDITIONAL_LINE:
        print(*ADDITIONAL_LINE)

    fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
    # if fxn_args.startswith('()'): then no args
    if NEED_TO_PRINT_FUNCTION:
        name = frame.f_code.co_name
        print_on_func_call(name, fxn_args)
        NEED_TO_PRINT_FUNCTION = False

    if event == 'return':
        # first arg is fxn name
        print_on_return(frame.f_code.co_name, arg)

        # pop the function's variables
        prev_line_locals.pop()
        JUST_PRINTED_RETURN = True


def print_on_return(fxn_name, arg):
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
    deal_with_lists(curr_line_locals) # convert lists to tuples

    # print("locals", curr_line_locals.items())
    changed_values = {
                key: curr_line_locals[key]
                # for key,_ in set(curr_line_locals.items()) - prev_line_locals[-1]
                for key,_ in hashable_curr_line_locals - prev_line_locals[-1]
    }

    # print("CHANGED VARS", changed_values)
    print_vars(changed_values)

    # need to update since this is a set of pairs so we cant just update the value for this variable
    for key_val_pair in prev_line_k_v_pairs(changed_values):
        prev_line_locals[-1].remove(key_val_pair)

    # is this correct ?
    prev_line_locals[-1].update(make_locals_hashable(changed_values))

    return

def assigned_constant():
    assignment = prev_line_code[0].split('=')[-1].strip()

    # todo make this find dicts, differentiate between {1:1} and {1:1, **other_dict}
    if (assignment.isdigit()
        or search(r'^".*"$', assignment)
        or search(r"^'.*'$", assignment)
        or assignment.startswith('return')):
            return True
    return False


def print_vars(changed_values):
    global PRINTED_LINE
    global ADDITIONAL_LINE
    if NEED_TO_PRINT_FUNCTION:
        # print() # was
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
        if len(changed_values) > 1:
            raise ValueError("multiple values changed in one line")
        var_name = tuple(changed_values.keys())[0]
        value = tuple(changed_values.values())[0]
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
