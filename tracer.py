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

# next: save this in git, see how it looks with printed on the same line and just fix formatting in general

# NEXT: WORK ON THE ASSIGNED_CONSTANT PART TO USE THE FUNCTION INTERPRET_EXPRESSION
# try to do a substitution for an if statement ?
# or commit the work and start working on the one that generates a file
# NEXT: when showing objects with changed fields, only record the field that changed, not both X and Y when only X is changed


# Note: this thing kinda sucks at interpreting non-obvious things
# *  119 │   y = [2]  #  y = [2]
# *  121 │   y += ["a"]  #  y + = ["a"]
  # y=[2] ──> new value: [2, 'a']

# NEXT:
# - try to delete 'vect': <__main__.Vector object at 0x7f40fd7df050>, and only store their fields
# need to fix this for SELF


# NEXT:
# - MAKE STUPID MULTI-LINE STATEMENTS WORK

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

Done:
    - make loops work
    test: [] += [a]
    - return x, y, z()
    - object properties changing
        - object.some_value = 10
    - del some_dict[key]
    some_dict[key] = 2

    *  63 │   y = {**{"some": "dict"}, **y}  # y = {'some': 'dict', 'one': 1, 'two': 22}
        y=(('one', 1), ('two', 22)) ──> new value: {'some': 'dict', 'one': 1, 'two': 22}


Todo:
    - dont show value changes for loop variables -- just show inline ie for x in range(3): # x = 1
    - keep indentation
    - make strings have quotes around them ie: instead of b=b --> ... HAVE: b='b' --> ...
    - ASYNC
    - Note: I think if statements wont work great since we wont show the code paths that dont execute and there is a chance we have to interpret those values ourselves
        -- this should be a flag "eval_all_branch_paths"
    - add more substitution logic for function calls and such
    ie: Vector(x,y) shows Vector(0, 1)
    -- same for loops -- maybe not possible though

    - delete inline comments
        - dont have to worry about multi-line strings since those dont have comments
        - how do I tell if a comment is inside a string or not
    - how to tell when a multi-line anything is complete
    - https://github.com/alexmojaki/executing?tab=readme-ov-file#libraries-that-use-this ?
    -- this can get the ast from a frame object


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

# Define a function to explore Python frame objects
def investigate_frames(current_frame):
    # Print the current frame's outer frames and their details
    # current_frame = inspect.currentframe()
    frames = inspect.getouterframes(current_frame)
    print('Frame exploration:')
    for idx, frame_info in enumerate(frames):
        frame, filename, line_number, function_name, lines, index = frame_info
        print(f'Frame {idx}: {function_name} at {filename}:{line_number}')
        print(f'Code Context: {lines[index].strip()}')
        print(f'Locals: {frame.f_locals}')
        print('---')

def print_all(obj):
    fields = {}
    for attr_name in dir(obj):
        if not attr_name.startswith('__'):
            if attr_name in ("f_globals", "f_locals", "f_builtins"):
                continue
            # NOTE: use: https://docs.python.org/3/library/inspect.html#inspect.getattr_static
            # getattr_static
            attr_value = getattr(obj, attr_name)
            if not callable(attr_value):  # Exclude methods
                fields[attr_name] = attr_value
    pprint(fields)
    return fields

# def print_all(frame):
#     def find_all_attrs(curr_obj):
#         all_attrs = {}
#         for attr in dir(curr_obj):
#             if attr.startswith("__"):
#                 continue
#             # all_attrs[attr] = getattr(curr_obj, attr)
#             all_attrs[attr] = find_all_attrs(getattr(curr_obj, attr))
#         return all_attrs
#     attrs = find_all_attrs(frame)
#     pprint(attrs)







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
        # global JUST_PRINTED_RETURN
        if self.just_printed_return:
            self.just_printed_return = False
            return

        # no print on first call (where value isss empty string
        if self.prev_line_code != "":
            # should do more stuff instead of always printing lstrip'd lines
            # need to show conditionals/their indentations better.
            self.printed_line += [cf.cyan(f'*  {self.prev_line_num} │  '), f'{self.prev_line_code.lstrip(" ")}']

    def on_return(self, frame, arg):
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
        # global PRINTED_LINE
        # global ADDITIONAL_LINE
        # global JUST_PRINTED_RETURN
        # global NEED_TO_PRINT_FUNCTION
        # global prev_line_locals_stack
        # TODO: 
        # global prev_line_locals_stack_dict

        # clear last results
        self.printed_line.clear()
        self.additional_line.clear()

        curr_line_locals_dict = frame.f_locals #.copy()
        # curr_line_locals_set = convert_to_set(curr_line_locals_dict.items())
        # print("CURR LOCALS", curr_line_locals_dict)
        if event == 'exception':
            name = frame.f_code.co_name
            fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
            signature = name + fxn_args
            print('The function call: %s produced an exception:\n' % signature)
            tb = ''.join(traceback.format_exception(*arg)).strip()
            print('%s raised an exception:%s%s' % (name, os.linesep, tb))
            #set a flag to print nothing else
            # raise ValueError("EXCEPTION")
            # return

        # if not len(prev_line_locals_stack[-1]):
        if not self.prev_line_locals_stack[-1]:
            # appended for each new function call so we have variables local to the current function
            # this happens when new functions are called and all the function args are added to locals at once right below
            # self.prev_line_locals_stack[-1].update(curr_line_locals_set)
            curr_line_locals_set = self.convert_to_set(curr_line_locals_dict.items())
            # print("========== prev_line_locals[-1] is empty, new:", curr_line_locals_set)
            self.prev_line_locals_stack[-1].update(curr_line_locals_set)
        # if not prev_line_locals_stack_dict[-1]:
            self.prev_line_locals_stack_dict[-1].update(deepcopy(curr_line_locals_dict))

        # prints the current line about to execute
        self.extract_original_code()

        # investigate_frames(frame)

    #     print()
        # print_all(inspect.getframeinfo(frame))
        # print_all(frame.f_code)

        # for attr_name in dir(frame.f_code):
        #     if attr_name in ("_co_code_adaptive", "co_code", "co_linetable", "co_lnotab"):
        #         print(attr_name, dis.dis(getattr(frame.f_code, attr_name)))
        # print()

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



    def print_on_return(self, fxn_name, arg):
        # global SELF_IN_LOCALS
        self.self_in_locals = False
        print(f"{cf.cyan(f'{fxn_name} returned')} {arg}")


    def store_nested_objects(self, curr_line_locals_dict, locals_with_objects):
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


    def add_object_fields_to_locals(self, curr_line_locals_dict):
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

        # add interpreted comment to the current line
        # ie show: * 123 | x = y  # x = 10
        if not self.assigned_constant():
            # interpret_expression(changed_values, curr_line_objects)
            self.interpret_expression(changed_values)

        for (var_name, old_value) in self.prev_line_locals_stack_dict[-1].items():
            if var_name not in changed_values:
                continue
            new_value = changed_values[var_name]
            if var_name.startswith(self.object_prefix):
                # remove prefix: _TRACKED
                var_name = var_name[9:]
            self.additional_line += [cf.red(f"  {var_name}={old_value}"), "──>", cf.green(f"new value: {new_value}")]


    # def extract_variable_assignments(changed_values, curr_line_objects, var_names, values):
    def extract_variable_assignments(self, changed_values):
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


    def update_line_code(self, next_line_executed):
        # prev_line_code[0] = next_line_executed
        self.prev_line_code = next_line_executed
        # print("new prev line code", prev_line_code[0])

    def update_line_num(self, line_num):
        self.prev_line_num = line_num

    def is_custom_object(self, name, value):
        # https://docs.python.org/3/library/inspect.html#fetching-attributes-statically
        # -- hasatr can cause code to execute !!!
        # todo: CHANGE
        return name != "self" and hasattr(value, "__dict__")
        # https://stackoverflow.com/a/52624678
        #^ wont work with __slots__
        # will only detect user defined types

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


    def print_on_func_call(self, fxn_name, fxn_args):
        # add to variable stack
        # pop from function stack when I leave)
        self.prev_line_locals_stack.append(set())
        self.prev_line_locals_stack_dict.append(dict())
        signature = fxn_name + fxn_args
        print(cf.yellow(f'... calling {signature}'))


# def init_tracer_globals():
#     cf.use_style("solarized")
#     global prev_line_code
#     global prev_line_locals_stack_dict
#     global prev_line_locals_stack
#     global prev_line_num

#     global OBJECT_PREFIX
#     global SELF_IN_LOCALS
#     global PRINTED_LINE
#     global ADDITIONAL_LINE
#     global JUST_PRINTED_RETURN
#     global FIRST_FUNCTION
#     global NEED_TO_PRINT_FUNCTION
#     # use list to store string since lists are mutable.
#     prev_line_code = ["0"]

#     FIRST_FUNCTION = True
#     NEED_TO_PRINT_FUNCTION = False
#     JUST_PRINTED_RETURN = False
#     PRINTED_LINE = []
#     ADDITIONAL_LINE = []
#     SELF_IN_LOCALS = False

#     OBJECT_PREFIX = "_TRACKED_"
#     # is a set of var_name, val tuples.
#     # ie: == { ('var_name1', "value1"), ('var_name2', 123), ... }
#     # prev_line_locals_stack = set()
#     prev_line_locals_stack = [set()]
#     prev_line_locals_stack_dict = [{}]
#     prev_line_num = [0]


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
            # init_tracer_globals()

            # https://docs.python.org/3/library/sys.html#sys.settrace
            # sys.settrace(once_per_func_tracer)
            return function(*args, **kwds) #executes decorated function
        finally:
            sys.settrace(old)
            # read the csv created and print everything
            # real library will hit the api and verify account info by using an api key
            # if cant reach internet, should still work with minimal version
    return setup_tracing
