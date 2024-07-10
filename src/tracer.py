import sys
# import dis
# import ast
from pprint import pprint, pformat
# from copy import deepcopy
from typing import Any, List, Type, Callable, Optional
# from typing import Any, Deque, ItemsView, List, Type, Callable, Optional
from types import FrameType, TracebackType
# from types import GeneratorType, FrameType,  TracebackType
# from collections import deque
# from itertools import islice
# import inspect
import functools
# import os
# import traceback
# from re import search
# from collections.abc import I
# from colorama import Fore, Back, Style, init
import colorful as cf
# from pygments import highlight
# from pygments.lexers import get_lexer_by_name
# from pygments.formatters import Terminal256Formatter
# from pygments import lex
# from pygments.token import Token as ParseToken

from .tracer_storage import Function
from .helpers import get_fxn_name, get_fxn_signature, TracingError



class Trace:
    """
    Each new function will create a new function object and this will allow me to write an entire function at a time into the csv
    - CSV is bad for this since I can't read one line at a time
    - maybe use sqlite and create csv from sqlite file at the end by using subprocess()
    I kinda want to just do duckdb but it sucks theres not a django orm for that
    - also just sucks that people have to download another package, but its just a dev dependency


    what if I wrote the csv file one function at a time as they complete
    then the first function will be at the end of the file and I can just read it in reverse
    - and the first function should be able to link to what line the function's it calls are in the csv
    ex.)
    def idk():
        x = other_fn()
    -- when we create a new function object cuz other_fn() is called
    -- we pass in a special parameter representing idk() so that idk can find the code for other_fn()
    """
    def __init__(self):
        cf.use_style("solarized")
        self.first_function = True
        self.execution_id = 0
        self.prev_trace = sys.gettrace()
        self.fxn_stack: List[Function]  = []

        self.json = []
        # todo: get value from env var
        self.print_mode = "debug"
        # todo: get value from env var
        self.object_prefix = "_TRACKED_"
        # todo: get value from env var
        self.num_loops_stored = 2 # store first 3, last 3 loop iters by default


    def __call__(self, function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            with self:
                return function(*args, **kwargs)

        return wrapper

    def __enter__(self):
        self.prev_trace = sys.gettrace()
        self.fxn_stack.append(None)
        sys.settrace(self.once_per_func_tracer)
        return self # todo: does this get traced ??


    def done_tracing(self):
        return not self.first_function and len(self.fxn_stack) == 1 and self.fxn_stack[0] is None

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], exc_traceback: Optional[TracebackType]) -> bool:
        # Note: return True to suppress exceptions
        # NOTE: this is called when a error occurs internally
        sys.settrace(self.prev_trace) # has to be the first line or we get weird errors
        # pprint(self.json)
        if not self.json and self.done_tracing():
            raise TracingError("No self.json, cannot write to file")
        if self.print_mode == "console":
            # todo: add code to print the json all nice -- console mode
            # iterate over self.json and show things function by function instead of in execution order
            return False
        if self.json and self.print_mode in ("debug", "json"):
            with open("code_info.json", "w") as f:
                json = pformat(self.json)
                f.write(json)
        return False

    def once_per_func_tracer(self, frame: FrameType, event: str, arg: Any) -> Optional[Callable]:
        # how this works: -- this function is called each new function and it prints "calling {signature}" then returns the trace_lines tracer for the next part
        name = get_fxn_name(frame)
        if event == 'call':
            # print(f"first_function: {self.first_function}, fxn_stack: {self.fxn_stack}")
            if self.done_tracing():
                return
            # fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
            if "dictcomp" in name:
                print("DICTCOMP")
                return
            if "listcomp" in name:
                print("LISTCOMP")
                return
            if "genexpr" in name:
                # https://docs.python.org/3/library/inspect.html#current-state-of-generators-coroutines-and-asynchronous-generators
                # Note: one day can support inspecting this ^
                print("GENEXPR")
                return
            if self.first_function:
                self.add_new_function_call(frame)
                self.first_function = False
            else:
                self.fxn_stack[-1].fxn_transition = True

            if self.trace_this_func(name):
                return self.trace_lines
            # print(inspect.getcomments(frame.f_code))
            # comments will need to be read from the file along with the lines they appear in

        print("=============== no tracer returned kinda")
        return self.once_per_func_tracer

    def trace_this_func(self, fxn_name: str) -> bool:
        # if fxn_name in list(should_trace): return True
        return True



    def on_return(self, frame: FrameType, returned_value: Any):
        # get json data for this function before we delete its data
        self.fxn_stack[-1].print_on_return(frame.f_code.co_name, get_fxn_signature(frame), returned_value)
        json = self.fxn_stack[-1].to_json()
        # TODO: store this json in the calling class

        # TODO: set flag so that we dont print the original function as if its getting called again
        # -- this is whats causing my error, I add the function to the stack twice
        # ie: currently, v = Vector() will do "calling __init__..."
        # then when __init__ returns, it will print "calling test_custom_objects" before doing the next line in the original function

        # print("before pop", self.fxn_stack)
        # pop the function's variables
        self.fxn_stack.pop()
        if not self.done_tracing():
            # add the called function's json to the caller
            self.fxn_stack[-1].add_json(json)
            # is this correct below here ? we're setting just_printed_return for a diff functin that returned (the popped one)
            self.fxn_stack[-1].just_printed_return = True
            self.fxn_stack[-1].just_returned = True
        else:
            # not sure if this is the correct json
            self.json = json
            if 1:
                pprint(json, sort_dicts=False, width=100)
        # print("AFTER pop", self.fxn_stack)


    def trace_lines(self, frame: FrameType, event: str, arg: Any):
        """ called before "next_line_executed" is ran, so we see the changes in frame.f_locals late

        WHEN TO UPDATE THE FUNCTION'S EXECUTION_ID
        solution: we pass execution_id to Function at the beginning of this function
            then at the end of this function, we get the new one from the function stack
            and the other function only updates this value if a printed line exists
            ie:
                - set execution_id --> self.fxn_stack[-1].latest_execution_id = self.execution_id
                - end of function --> self.execution_id = self.fxn_stack[-1].latest_execution_id

            this allows new functions to always have the right id
            and also allows the function object to determine if the value should be incremented based on the code found

            maybe pass a reference ? feels wrong but is simple to make sure everything is up to date
        """

        self.fxn_stack[-1].latest_execution_id = self.execution_id

        curr_line_locals_dict = frame.f_locals #.copy()
        if event == 'exception':
            # TODO
            # fxn_name = get_fxn_name(frame)
            # fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
            # signature = get_fxn_signature(frame)
            # print('The function call: %s produced an exception:\n' % signature)

            # tb = ''.join(traceback.format_exception(*arg)).strip()
            self.fxn_stack[-1].add_exception(arg)
            # print('%s raised an exception:%s%s' % (fxn_name, os.linesep, tb))

            #set a flag to print nothing else
            # raise TracingError("EXCEPTION")
            # return

        if not self.fxn_stack[-1].prev_line_locals_dict:
            # appended for each new function call so we have variables local to the current function
            # this happens when new functions are called and all the function args are added to locals at once right below
            # print("=====================INIT")
            self.fxn_stack[-1].initialize_locals(curr_line_locals_dict)

        added_line = self.fxn_stack[-1].add_line()
        self.execution_id = self.fxn_stack[-1].latest_execution_id

        # print(self.fxn_stack[-1].lines)
        self.fxn_stack[-1].update_stored_vars(curr_line_locals_dict)
        # update_stored_vars determines if this line should be added and if so, then execution_id is incrememented
        # this allows update_stored_vars to determine if self.execution_id should be incremented

        if added_line:
            self.fxn_stack[-1].mark_loop_events()
        self.fxn_stack[-1].print_line()

        # # if self.fxn_stack[-1].prev_line_code.strip() == "x = 20":
        # if self.fxn_stack[-1].prev_line_code:
        #     # pprint(ast.dump(ast.parse(inspect.getsource(frame))))
        #     source_code = inspect.getsource(frame)
        #     pprint(find_multi_line_everything(source_code))
        #     # start_line, end_line = get_for_loop_line_numbers(source_code)
        #     # print(f"start: {start_line}, end: {end_line}")
        #     # pprint(lines)
        #     # return
        #     # ast_stuff = ast.parse(self.fxn_stack[-1].prev_line_code.strip())
        #     # pprint(ast.dump(ast_stuff))
        #     print()

        if self.new_fxn_called():
            self.add_new_function_call(frame)
            self.fxn_stack[-1].initialize_locals(curr_line_locals_dict)
            # self.add_new_fxn_args_to_locals(frame, curr_line_locals_dict)

        if self.fxn_stack[-1].just_returned:
            self.fxn_stack[-1].just_returned = False
        if self.fxn_stack[-1].fxn_transition:
            self.fxn_stack[-1].fxn_transition = False
            # print("new function", self.fxn_stack)

        if event == 'return':
            self.on_return(frame, arg)
            # print("after return", self.fxn_stack)
            if len(self.fxn_stack) == 1 and self.fxn_stack[0] == None:
                return
        # have this as an else for weird case:
            # y = loop_fn();
            # def loop_fn: for i in range(2): x = i
            # NOTICE there is no return statement
            # this will do add_next_line on the fxn with y = loop_fn()
            # but the line added will be: for i in range(2)
            # the final evaluation of the loop condition
        else:
            # do this at the end since update_locals uses prev_line_code
            self.fxn_stack[-1].add_next_line(frame)


    def new_fxn_called(self):
        return self.fxn_stack[-1].fxn_transition \
               and not self.fxn_stack[-1].just_returned


    def add_new_function_call(self, frame: FrameType):
        self.fxn_stack.append(Function(frame, self.execution_id, self.object_prefix, self.num_loops_stored, len(self.fxn_stack)))
        # this causes immediate prints instead of deferring prints to this class
        self.fxn_stack[-1].print_mode = self.print_mode
        self.fxn_stack[-1].print_on_func_call(get_fxn_signature(frame), frame.f_lineno)
        self.execution_id += 1
