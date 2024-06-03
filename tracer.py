import sys
import dis
from pprint import pprint
from copy import deepcopy
from typing import Any
from types import GeneratorType
import inspect
import functools
import os
import traceback
from re import search
from colorama import Fore, Back, Style, init
import colorful as cf
from helpers import investigate_frames, print_all

class FunctionVars:
    """
    now "parent" class will store an array of FunctionTracer's rather than an array of dicts and sets
    but what happens when a new nested function is found, we would want the parent function to do that
    -- this is confusing

    maybe this only stores the variables and handles finding new values through implementing __hash__
    """
    def __init__(self, file_name, object_prefix, function_signature, execution_id):
        # need info from the previous function
        self.prev_line_locals_set = set()
        self.prev_line_locals_dict = dict()
        # -- Note: even if we used a database to write intermediate results to reduce memory complexity, we would still need
        # to store the sets/dicts of locals in memory since we need the actual object references and types, etc
        # the real memory hog will be these variables, thus: a database wont help with the bottleneck and we dont need it
        # so the question is: how much will a database help ?
        self.type = "function_start"
        # used for when self.type = "function_call" || "loop"

        # note: main tracer will need to find execution_id from other spots often: --> self.function_stack[-1].lines[-1].execution_id
        # cuz the main loop will see a new function and will have to iterate check self.function_stack[-1].lines[-1].execution_id

        self.lines = []
        # self.inner_code = []
        # when a new function call is encountered, the main tracer will do tracer_self.functions[-1]
        # self.function_stack = []

        # should this store nested info ??
        # then for each new line, the main loop will see y=10, and add a normal line
        # or will see y = other_fn() and then where will it assign inner_code ??

        self.object_prefix = object_prefix
        self.file_name = file_name
        self.function_signature = function_signature
        self.execution_id = execution_id
        # -- now we write to the JSON file here I think, then we 

        # self.caller_execution_id = sjdcnkasjdncdjka

    def add_exception(self, function_name, arg):
        # KEEP
        # todo: replace function_name with self.function_signature
        tb = ''.join(traceback.format_exception(*arg)).strip()
        print('%s raised an exception:%s%s' % (function_name, os.linesep, tb))
        pass

    def print_on_return(self, fxn_name, arg):
        # KEEP
        # move this to function
        # global SELF_IN_LOCALS
        self.self_in_locals = False
        print(f"{cf.cyan(f'{fxn_name} returned')} {arg}")


    def store_nested_objects(self, curr_line_locals_dict, locals_with_objects):
        # KEEP
        for name,value in curr_line_locals_dict.items():
            # in self.prev_line_locals_stack[-1]
            if self.is_custom_object(name, value):
                tracked_name = f"{self.object_prefix}{name}"
                # need to deepcopy o.w this value (stored in prev_line_locals_stack_dict -- will update this variable immediatley
                # ie: fields = {"sub_object": <__main__.SomeOtherObject object at 0x7fb745d8e710>, "z": 10}
                fields = vars(value)
                fields_copy = deepcopy(fields)
                # print("tracked_name, fields", tracked_name, fields)
                locals_with_objects[tracked_name] = fields_copy
                del locals_with_objects[name]
                self.store_nested_objects(fields, locals_with_objects[tracked_name])

    def is_custom_object(self, name, value):
        # MOVE
        # https://docs.python.org/3/library/inspect.html#fetching-attributes-statically
        # -- hasatr can cause code to execute !!!
        # todo: CHANGE
        return name != "self" and hasattr(value, "__dict__")
        # https://stackoverflow.com/a/52624678
        #^ wont work with __slots__
        # will only detect user defined types

    def add_object_fields_to_locals(self, curr_line_locals_dict):
        # KEEP
        """
            - create deepcopy of function locals
            - for each object in local, extract its fields/values and store that instead
            - create a set from this dict so we can see which values are new in calling function
        """

        # create a copy so we can delete the root objects and only store their field from vars()
        locals_with_objects = deepcopy(curr_line_locals_dict)
        # print("locals_with_objects", locals_with_objects, "locals_dict", curr_line_locals_dict)
        self.store_nested_objects(curr_line_locals_dict, locals_with_objects)

        curr_line_locals_set = self.convert_to_set(locals_with_objects.items())
        # return curr_line_locals_set, curr_line_locals_dict, curr_line_objects
        return curr_line_locals_set, locals_with_objects


    def update_stored_vars(self, curr_line_locals_dict):
        """ need to make lists hashable somehow for storing lists in the set.
            maybe I store lists differently
            and give the option to search lists for if a certain value appears
            could eventually make it so u pass a parameter to @trace which
            will look thru lists and return the values changed in a list as well
            as the indices where they are found.
        """
        # global SELF_IN_LOCALS
        # print("prev_line_locals", prev_line_locals_stack[-1])


        # curr_line_locals_set, curr_line_locals_dict, curr_line_objects = add_object_fields_to_locals(curr_line_locals_dict)
        curr_line_locals_set, curr_line_locals_dict = self.add_object_fields_to_locals(curr_line_locals_dict)
        new_variables = curr_line_locals_set - self.prev_line_locals_stack[-1]

        # Note: need curr_line_locals_dict since it is a dict and curr_line_locals_set is a set
        changed_values = {
            key: curr_line_locals_dict[key] # now the key stores the new value
            for key,_
            in new_variables
        }
        # print("changed", changed_values, "=====", curr_line_locals_dict, "=====", curr_line_objects, "new_variables", new_variables)

        # Note on classes:
        #     def Vector(x, y)
        #     ...
        #     y = Vector(0, 1)
        # -- first the variables x, y, self are created in the LOCAL SCOPE BEFORE the new function call appends a set() to the self.prev_line_locals_stack stack
        if not self.self_in_locals and "self" in changed_values:
            self.self_in_locals = True
            # print("============== self in locals, returning...")
            return
        self.gather_additional_data(changed_values)
        self.replace_old_values(changed_values)


    def construct_formatted_line(self, changed_values):
        # add interpreted comment to the current line
        # ie show: * 123 | x = y  # x = 10
        # move if statement to function named: "construct_formatted_line()
        if self.assigned_constant():
            self.formatted_line = ""
            # -- maybe create a LineInfo object that has changed values and each function has an array of these
            return
        # if not self.assigned_constant():
            # interpret_expression(changed_values, curr_line_objects)
            self.interpret_expression(changed_values)


    def construct_additional_line(self, changed_values):
        for (var_name, old_value) in self.prev_line_locals_stack_dict[-1].items():
            if var_name not in changed_values:
                continue
            new_value = changed_values[var_name]
            if var_name.startswith(self.object_prefix):
                # remove prefix: _TRACKED
                var_name = var_name[9:]
            self.additional_line += [cf.red(f"  {var_name}={old_value}"), "──>", cf.green(f"new value: {new_value}")]

    def gather_additional_data(self, changed_values):
        """
            we need to gather additional data if either:
                1. non-simple assignment  ie: x = "a string".split() * 2 + ["a"]
                2. variable has new value ie: x = 11; x = 22
        """
        # global self.additional_line
        if self.need_to_print_function:
            # here, we return BEFORE entering a new function
            print("need to print function, returning...")
            return

        self.construct_formatted_line(changed_values)
        self.construct_additional_line(changed_values)



    # def extract_variable_assignments(changed_values, curr_line_objects, var_names, values):
    def extract_variable_assignments(self, changed_values):
        # KEEP
        """ Can do:
            - x = y
            - a, b = "a", x
            - vect = Vector(0, 1)
            - vect.x = x
            - self.x = x    # will add more stuff for self later
        Add:
            - a, b = "a", vect.x
            - vect.x, vect.y = x, y
        """
        # global self.printed_line
        value: Any = ""
        var_name = ""

        assignment, expression = [code.strip() for code in self.prev_line_code.split('=')]
        # print("====== assignment", assignment, "expression", expression, "changed_values", changed_values)

        if (
            len(changed_values) == 0
            and len(expression.split()) == 1 and "(" not in expression # RHS has no spaces, "(" -- straight assignment ie: x = y
        ):
            # Note: this conditional handles __init__()
            # Think this is supposed to do substitution
            # this happens for self.y = y
            # THIS IS BECAUSE WE DONT CHECK FOR CHANGES TO SELF CURRENTLY THEREFORE CHANGED_VALUES = {}
            var_name = expression
            value = self.prev_line_locals_stack_dict[-1][var_name]
            # self.PRINTED_LINE += [cf.bold(cf.cyan(" #")), f"{var_name} = {value}"]
            print("extract_variable_assignments no changed values")
            return [var_name], [value]

        elif "," in assignment and len(assignment.split(",")) == len(expression.split(",")):
            # multiple assignment line
            assignments = [a.strip() for a in assignment.split(",")]
            expressions = [e.strip() for e in expression.split(",")]
            var_names, values = [], []
            for curr_assignment, curr_expression in zip(assignments, expressions):
                # -- need to find actual var_name from curr_assignment//curr_expression and then send the correct thing from changed_values
    # changed_values: {'_TRACKED_vect': {'x': 99, 'y': 1}, 'b': 10}, assignments: ['vect.x', 'b'], expressions: ['99', 'x']
                # assignment: vect.x, expression: 99 , var_name: vect.x, value: {'_TRACKED_vect': {'x': 99, 'y': 1}, 'b': 10}

                var_name, value = self.handle_object_expression(curr_assignment, curr_expression, changed_values)
                var_names.append(var_name)
                values.append(value)
            return var_names, values
            # extract_variable_assignments(changed_values, curr_line_objects, 
            # fuck with self.PRINTED_LINE here instead of making this too general
        elif len(changed_values) == 1:
            # print("changed_values", changed_values, "name,value", var_name, value)
            var_name, value = self.handle_object_expression(assignment, expression, changed_values)
            return [var_name], [value]
        else:
            # raise ValueError(f"Unexpected conditional case, changed_values: {changed_values}, curr_line_objects: {curr_line_objects}")
            raise ValueError(f"Unexpected conditional case, changed_values: {changed_values}")


    def generate_object_name(self, field_chain, changed_values):
        # KEEP WITH handle_object_expression
        name = ""
        chained_object = changed_values
        # need to iterate over changed_values
        for curr_name in field_chain:
            transformed_name = f"{self.object_prefix}{curr_name}"
            if transformed_name in chained_object:
                name = f"{name}.{transformed_name}" if name else transformed_name
                chained_object = chained_object[transformed_name]
            else:
                name = f"{name}.{curr_name}" if name else name
        # print("generated object name", name)
        return name


    # def handle_object_expression(assignment, expression, var_name, value):
    def handle_object_expression(self, assignment, expression, changed_values):
        # CAN MOVE
        # need to add a field for the actual value to make it clear for when value is the string "vect.x"
        """
            assignment ex.) "vect.x"  || "x"
            var_name   ex.) "vect"    || "x"
            value      ex.) {"x": 12} || "x"

            -- returns var_name ex.) "vect.x" || "x"
            -- returns value    ex.) 12       || "x"
            if its not an object assignment then we return the input
            if its an object, then we get its value from value by using the field name
        """
        # working output for LHS without MAssiggnment
        # assignment vect.x , expression x , var_name _TRACKED_vect , value {'x': 10, 'y': 1}

        # print(f"handle_object_expression assignment: {assignment}, expression: {expression}, changed_values: {changed_values}")

        if "." not in assignment and "." not in expression:
            if assignment in changed_values:
                return assignment, changed_values[assignment]
            return assignment, expression
            # return assignment, expression

        if "self" in assignment or "self" in expression:
            if assignment in changed_values:
                return assignment, changed_values[assignment]
            return assignment, expression

        assignment_field_chain = assignment.split(".")
        expression_field_chain = expression.split(".")
        object_field_assigned = len(assignment_field_chain) > 1
        object_field_in_expression = len(expression_field_chain) > 1
        # value

        var_name = assignment
        if object_field_assigned:
            # this is an assignment so we get the value from changed_values
            object_name = self.generate_object_name(assignment_field_chain, changed_values)
            value = None
            for field in object_name.split("."):
                value = value[field] if value else changed_values[field]
        if object_field_in_expression:
            # var_name = expression
            # this is an expression so we get the value from this object.field's previos value
            object_name = self.generate_object_name(expression_field_chain, self.prev_line_locals_stack_dict[-1])
            value = None
            for field in object_name.split("."):
                value = value[field] if value else self.prev_line_locals_stack_dict[-1][field]

            # do I need to change the var_name ?????

        # TODO: iterate over subobjects and remove _TRACKED_ from the name
    # vect={'y': 22, '_TRACKED_x': {'o': 0}} ──> new value: {'y': 22, '_TRACKED_x': {'o': 99}}

        return var_name, value
        # return assignment, expression


    def interpret_expression(self, changed_values):
        # KEEP
        # global self.printed_line

        # x = "="
        # x.add(" = ")
        # fn(" = ")
        has_bracket = "(" in self.prev_line_code
        is_assignment = (
            "=" in self.prev_line_code and "(" in self.prev_line_code and self.prev_line_code.index("=") < self.prev_line_code.index("(")
        ) or "=" in self.prev_line_code
        # this is wrong, what if the equals sign is in a string
        # what if this just returns things instead of printing them, then I can do multiple assignments recursively...
        # assuming no spaces means its getting assigned a variable such as self.x = x

        if len(changed_values) > 0 or is_assignment:
            code = [code.strip() for code in self.prev_line_code.split('=')]
            assignment, expression = code
            # var_names, values = [], []
            # extract_variable_assignments(changed_values, curr_line_objects, var_names, values)
            var_names, values = self.extract_variable_assignments(changed_values)
            # print("OUTPUT var_names: ", var_names, "values:", values)
            # for each variable change, store: assigned_var_name, 
            self.printed_line += [cf.bold(cf.cyan(" #"))]
            num_vars = len(var_names)
            # construct formatted_line
            for i in range(num_vars):
                var_name, value = var_names[i], values[i]
                self.printed_line += [f" {var_name} = {value},"] if 0 <= i < num_vars - 1 else [f" {var_name} = {value}"]


    # change name(s) since I store var_name, value tuples, not key_val tup's
    def prev_line_k_v_pairs(self, changed_values_keys):
        # need the previous values in order to remove them from "prev_line_locals_stack"
        # ie: if x got changed to 10, this stores: (x, prev_value)
        # todo: change to generator
        return [
                (key, v)
                for (key, v) in self.prev_line_locals_stack[-1]
                if key in changed_values_keys
        ]


    def replace_old_values(self, changed_values):
        # KEEP
        # need to update since this is a set of pairs so we cant just update the value for this variable
        # remove old values according to changed_values
        # they are different here, the dict has the new values already
        for key_val_pair in self.prev_line_k_v_pairs(changed_values):
            self.prev_line_locals_stack[-1].remove(key_val_pair)
            del self.prev_line_locals_stack_dict[-1][key_val_pair[0]]

        # replace old values according to changed_values
        set_stuff = self.convert_to_set(changed_values.items())
        self.prev_line_locals_stack[-1].update(set_stuff)
        self.prev_line_locals_stack_dict[-1].update(changed_values)


    def assigned_constant(self):
        # MOVE
        expression = self.prev_line_code.split('=')[-1].strip()
        # todo make this find dicts, differentiate between {1:1} and {1:1, **other_dict}
        # maybe do opposite and search for non-constants
        # TODO: add case for +=, *=, etc -- these should be considered non-obvious
        if (
            expression.isdigit()
            or search(r'^".*"$', expression) # search for string assignment
            or search(r"^'.*'$", expression) # search for string assignment
            or expression.startswith('return') # TODO: delete this so we can do interpretations on return (-- then maybe just delete the "a_fn() returned XXX line)
        ):
                return True
        return False

    def make_hashable(self, value):
        # print("value", value, "type", type(value))
        if isinstance(value, GeneratorType):
            return value
        elif isinstance(value, dict):
            # todo: recurse over nested dicts
            return tuple(self.make_hashable(idk) for idk in value.items())
        # elif isinstance(value, tuple):
        elif isinstance(value, tuple):
            return tuple(self.make_hashable(idk) for idk in value)
        elif isinstance(value, list):
            # return self.make_hashable(tuple(value))
            return tuple(self.make_hashable(idk) for idk in value)
        elif hasattr(value, "__hash__"):
            return value
        else:
            return value


    def convert_to_set(self, locals):
        hashable_locals = set()
        for var_name, value in locals:
            value = self.make_hashable(value)
            # print(f"var_name: {var_name}, value: {value}, type: {type(value)}")
            hashable_locals.add((var_name, value))
        return hashable_locals

    def update_line_code(self, next_line_executed):
        # prev_line_code[0] = next_line_executed
        self.prev_line_code = next_line_executed
        # print("new prev line code", prev_line_code[0])

    def update_line_num(self, line_num):
        self.prev_line_num = line_num


class LineInfo:
    def __init__(self, code, execution_id):
        # other: line_num
        self.original_code = code
        self.formatted_line = ""
        self.additional_line = ""
        self.execution_id = execution_id

        # not sure if I need this as a field
        self.changed_values = {}


# - what do I do per function
# - what do I do per line

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
        self.prev_line = []
        self.first_function = True
        self.need_to_print_function = False
        self.just_printed_return = False
        self.printed_line = []
        self.additional_line = []
        self.self_in_locals = False

        self.prev_line_code = ""
        self.object_prefix = "_TRACKED_"
        # is a set of var_name, val tuples.
        # ie: == { ('var_name1', "value1"), ('var_name2', 123), ... }
        # prev_line_locals_stack = set()
        # need an extra data structure in these lists since __exit__ is part of the tracing
        self.prev_line_locals_stack = [set()]
        self.prev_line_locals_stack_dict = [{}]
        # self.prev_line_num = [0]
        self.prev_line_num = []
        self.prev_trace = sys.gettrace()

        self.function_stack = []


    def __call__(self, function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            with self:
                return function(*args, **kwargs)

        return wrapper

    def __enter__(self):
        self.prev_trace = sys.gettrace()
        # init_tracer_globals()
        sys.settrace(self.once_per_func_tracer)


    def __exit__(self, exc_type, exc_value, exc_traceback):
        sys.settrace(self.prev_trace) # has to be the first line or we get weird errors

    def once_per_func_tracer(self, frame, event, arg):
        # how this works: -- this function is called each new function and it prints "calling {signature}" then returns the trace_lines tracer for the next part
        # global FIRST_FUNCTION
        # global NEED_TO_PRINT_FUNCTION
        name = frame.f_code.co_name
        if event == 'call':
            fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
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
                self.print_on_func_call(name, fxn_args)
                self.first_function = False
            else:
                self.need_to_print_function = True

            if self.trace_this_func(name):
                return self.trace_lines
            # print(inspect.getcomments(frame.f_code))
            # comments will need to be read from the file along with the lines they appear in

        print("=============== no tracer returned kinda")
        return self.once_per_func_tracer

    def trace_this_func(self, fxn_name):
        # if fxn_name in list(should_trace): return True
        return True


    def extract_original_code(self):
        # CAN MOVE
        # global JUST_PRINTED_RETURN
        if self.just_printed_return:
            self.just_printed_return = False
            return

        # no print on first call (where value isss empty string
        # if self.function_stack[-1].prev_line_code:
        if self.prev_line_code != "":
            # should do more stuff instead of always printing lstrip'd lines
            # need to show conditionals/their indentations better.
            self.printed_line += [cf.cyan(f'*  {self.prev_line_num} │  '), f'{self.prev_line_code.lstrip(" ")}']

    def on_return(self, frame, arg):
        # stay here
        # global JUST_PRINTED_RETURN
        # first arg is fxn name
        self.print_on_return(frame.f_code.co_name, arg)

        # pop the function's variables
        self.prev_line_locals_stack.pop()
        self.prev_line_locals_stack_dict.pop()
        self.just_printed_return = True

    def trace_lines(self, frame, event, arg):
        """ called before "next_line_executed" is ran, so we see the changes in frame.f_locals late
        """
        # clear last results
        self.printed_line.clear()
        self.additional_line.clear()

        curr_line_locals_dict = frame.f_locals #.copy()
        # curr_line_locals_set = convert_to_set(curr_line_locals_dict.items())
        # print("CURR LOCALS", curr_line_locals_dict)
        if event == 'exception':
            # TODO
            name = frame.f_code.co_name
            fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
            signature = name + fxn_args
            print('The function call: %s produced an exception:\n' % signature)
            tb = ''.join(traceback.format_exception(*arg)).strip()
            print('%s raised an exception:%s%s' % (name, os.linesep, tb))
            #set a flag to print nothing else
            # raise ValueError("EXCEPTION")
            # return

        # if not self.function_stack[-1].prev_line_locals_stack:
        # if not len(prev_line_locals_stack[-1]):
        if not self.prev_line_locals_stack[-1]:
            # appended for each new function call so we have variables local to the current function
            # this happens when new functions are called and all the function args are added to locals at once right below
            # self.prev_line_locals_stack[-1].update(curr_line_locals_set)
            curr_line_locals_set = self.convert_to_set(curr_line_locals_dict.items())
            # print("========== prev_line_locals[-1] is empty, new:", curr_line_locals_set)
            self.prev_line_locals_stack[-1].update(curr_line_locals_set)
            self.prev_line_locals_stack_dict[-1].update(deepcopy(curr_line_locals_dict))

        # prints the current line about to execute
        self.extract_original_code()


        self.update_stored_vars(curr_line_locals_dict)

        print(*self.printed_line)
        if self.additional_line:
            print(*self.additional_line)

        if self.need_to_print_function:
            # append set() to prev_line_locals_stack, then add the initial function args to this set
            self.add_new_function_args_to_locals(frame, curr_line_locals_dict)
            self.need_to_print_function = False
        if event == 'return':
            self.on_return(frame, arg)

        skip_lane = "with" in self.prev_line_code
        next_line_executed = inspect.getframeinfo(frame).code_context[0].rstrip() if not skip_lane else ""
        # do this at the end since update_locals uses prev_line_code
        self.update_line_code(next_line_executed)
        self.update_line_num(frame.f_lineno)


    def add_new_function_args_to_locals(self, frame, curr_line_locals_dict):
        """
            Append set() to prev_line_locals_stack,
            then add the initial function args to this set
        """
        # this stays here since it inits stuff
        name = frame.f_code.co_name
        fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
        # NOTE: can get more detailed call info: https://docs.python.org/3/library/inspect.html#inspect.getcallargs
        # also here: https://docs.python.org/3/library/inspect.html#inspect.formatargvalues
        # or: https://docs.python.org/3/library/inspect.html#inspect.getfullargspec
        # inspect has a lot of functionality for all sorts of details for function calls
        self.print_on_func_call(name, fxn_args)
        curr_line_locals_set = self.convert_to_set(curr_line_locals_dict.items())
        self.prev_line_locals_stack[-1].update(curr_line_locals_set)
        self.prev_line_locals_stack_dict[-1].update(deepcopy(curr_line_locals_dict))
        # print("new function, just made locals:", self.prev_line_locals_stack[-1])


    def print_on_func_call(self, fxn_name, fxn_args):
        # add to variable stack
        # pop from function stack when I leave)
        self.prev_line_locals_stack.append(set())
        self.prev_line_locals_stack_dict.append(dict())
        signature = fxn_name + fxn_args
        print(cf.yellow(f'... calling {signature}'))
