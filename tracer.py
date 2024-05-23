import sys
import inspect
import functools
import os
import traceback
from re import search
from colorama import Fore, Back, Style, init
import colorful as cf


def on_func_call(fxn_name, fxn_args):
    _LOCALS.append(set())
    signature = fxn_name + fxn_args
    #CSV: line_num, caller_line_number, function_signature, caller_function_signature, original_line, formatted_line, additional_line
    _FILE.write(_LINE_NUM, )
    # print(cf.yellow(f'... calling {signature}'))


def trace_this_func(fxn_name):
    # if fxn_name in list(should_trace): return True
    # todo: make this more granular
    return True



def once_per_func_tracer(frame, event, arg):
    #CSV: line_num, caller_line_number, function_signature, caller_function_signature, original_line, formatted_line, additional_line
    _FILE.write("line_number,caller_line_number,function_signature,caller_function_signature,original_line,formatted_line,additional_line")
    # how this works: -- this function is called each new function and it prints "calling {signature}" then returns the trace_lines tracer for the next part
    # global FIRST_FUNCTION
    # global NEED_TO_PRINT_FUNCTION
    name = frame.f_code.co_name
    if event == 'call':
        fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
        on_func_call(name, fxn_args)
        # if FIRST_FUNCTION:
        #     print_on_func_call(name, fxn_args)
        #     FIRST_FUNCTION = False
        # else:
        #     NEED_TO_PRINT_FUNCTION = True

        if trace_this_func(name):
            return trace_lines
        # print(inspect.getcomments(frame.f_code))
        # comments will need to be read from the file along with the lines they appear in

    return once_per_func_tracer


def init_tracer_globals():
    # cf.use_style("solarized")
    # global prev_line_locals_dict
    global _LINE_NUM
    global _CALLER_LINE_NUM
    global _FXN_SIGNATURE
    global _CALLER_FXN_SIGNATURE
    global _ORIGINAL_CODE
    global _FORMATTED_LINE
    global _ADDITIONAL_LINE
    global _LOCALS
    # #CSV: line_num, called_from_line, function_signature, line_of_code, changed_values, return statement
    #CSV: line_num, caller_line_number, function_signature, caller_function_signature, original_line, formatted_line, additional_line

    # global _FORMATTED_LINE
    # global ADDITIONAL_LINE
    # global JUST_PRINTED_RETURN
    # global FIRST_FUNCTION
    # global NEED_TO_PRINT_FUNCTION
    # use list to store string since lists are mutable.
    _ORIGINAL_CODE = ["0"]

    # FIRST_FUNCTION = True
    # NEED_TO_PRINT_FUNCTION = False
    # JUST_PRINTED_RETURN = False
    _FORMATTED_LINE = []
    _ADDITIONAL_LINE = []

    # is a set of var_name, val tuples.
    # ie: == { ('var_name1', "value1"), ('var_name2', 123), ... }
    # _LOCALS = set()
    _LOCALS = []
    # prev_line_locals_dict = dict()
    _LINE_NUM = [0]



def trace(function):
    """
    trace the decorated function before changing back to default sys.gettrace value.
    """
    @functools.wraps(function)
    def setup_tracing(*args, **kwds):
        """
            use a try because of the finally functionality.
        """
        global _FILE
        try:
            #done before decorated function
            old = sys.gettrace()
            init_tracer_globals()
            _FILE = open("trace_data.csv", "w")

            sys.settrace(once_per_func_tracer)
            return function(*args, **kwds) #executes decorated function
        finally:
            _FILE.close()
            sys.settrace(old)
    return setup_tracing


def print_code():
    global _FORMATTED_LINE

    # no print on first call (where value isss empty string
    if _ORIGINAL_CODE[0] != "0":
        # should do more stuff instead of always printing lstrip'd lines
        # need to show conditionals/their indentations better.
        # print(cf.cyan(f'*  {_LINE_NUM[0]} │  '), f'{_ORIGINAL_CODE[0].lstrip(" ")}')
        # _FORMATTED_LINE += [cf.cyan(f'*  {_LINE_NUM[0]} │  '), f'{_ORIGINAL_CODE[0].lstrip(" ")}']
        _FORMATTED_LINE += [f'*  {_LINE_NUM[0]} │  ', f'{_ORIGINAL_CODE[0].lstrip(" ")}']


def update_line_code(next_line_executed):
    _ORIGINAL_CODE[0] = next_line_executed

def update_line_num(line_num):
    _LINE_NUM[0] = line_num


def make_locals_hashable(curr_line_locals):
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
    global _FORMATTED_LINE
    global _ADDITIONAL_LINE

    # clear last results
    _FORMATTED_LINE.clear()
    _ADDITIONAL_LINE.clear()

    curr_line_locals = frame.f_locals
    hashable_curr_line_locals = make_locals_hashable(curr_line_locals)
    # print("CURR LOCALS", curr_line_locals)
    if event == 'exception':
        name = frame.f_code.co_name
        fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
        signature = name + fxn_args
        print('The function call: %s produced an exception:\n' % signature)
        return

    if not len(_LOCALS[-1]):
        _LOCALS[-1].update(hashable_curr_line_locals)

    # print_code(frame.f_lineno)
    print_code() # prints the current line about to execute

    # think I should keep the prints elsewhere to increase modularity
    update_stored_vars(curr_line_locals, hashable_curr_line_locals)

    next_line_executed = inspect.getframeinfo(frame).code_context[0].rstrip()
    # do this at the end since update_locals uses _ORIGINAL_CODE
    update_line_code(next_line_executed)
    update_line_num(frame.f_lineno)

    # print(*_FORMATTED_LINE)
    # if _ADDITIONAL_LINE:
    #     print(*_ADDITIONAL_LINE)

    fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
    # if fxn_args.startswith('()'): then no args

    if event == 'return':
        # first arg is fxn name
        print_on_return(frame.f_code.co_name, arg)

        # pop the function's variables
        _LOCALS.pop()


def print_on_return(fxn_name, arg):
    pass
    # print('%s returned %r' % (fxn_name, arg))


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

    changed_values = {
                key: curr_line_locals[key]
                for key,_ in hashable_curr_line_locals - _LOCALS[-1]
    }

    print_vars(changed_values)

    # need to update since this is a set of pairs so we cant just update the value for this variable
    for key_val_pair in prev_line_k_v_pairs(changed_values):
        _LOCALS[-1].remove(key_val_pair)

    # is this correct ?
    _LOCALS[-1].update(make_locals_hashable(changed_values))
    return

def assigned_constant():
    assignment = _ORIGINAL_CODE[0].split('=')[-1].strip()

    # todo make this find dicts, differentiate between {1:1} and {1:1, **other_dict}
    if (assignment.isdigit()
        or search(r'^".*"$', assignment)
        or search(r"^'.*'$", assignment)
        or assignment.startswith('return')):
            return True
    return False


def print_vars(changed_values):
    global _FORMATTED_LINE
    global _ADDITIONAL_LINE

    for (var_name, old_value) in _LOCALS[-1]:
        if var_name in changed_values:
            _ADDITIONAL_LINE += [cf.red(f"  {var_name}={old_value}"), "──>", cf.green(f"new value: {changed_values[var_name]}")]

    if not assigned_constant():
        if len(changed_values) > 1:
            raise ValueError("multiple values changed in one line")
        var_name = tuple(changed_values.keys())[0]
        value = tuple(changed_values.values())[0]
        _FORMATTED_LINE += [cf.bold(cf.cyan(" #")), f"{var_name} = {value}"]


# change name(s) since I store var_name, value tuples, not key_val tup's
def prev_line_k_v_pairs(changed_values_keys):
    # need the previous values in order to remove them from "_LOCALS"
    # ie: if x got changed to 10, this stores: (x, prev_value)
    # todo: change to generator
    return [
            (key, v)
            for (key, v) in _LOCALS[-1]
            if key in changed_values_keys
    ]
