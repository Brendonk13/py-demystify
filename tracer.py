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



class LineInfo:
    def __init__(self, code, execution_id, type, line_number, print_mode):
        # other: line_num
        self.original_line = code.lstrip(" ")
        # todo: add type information for all changes
        self.formatted_line = ""
        # todo: add type information for all changes
        self.additional_line = ""
        self.uncolored_additional_line = ""
        self.execution_id = execution_id
        self.type = type
        # only relevant if type == "loop"
        self.loop_idx = 0
        self.line_number = line_number
        # means that we produce a json file
        self.print_mode = print_mode
        self.function_json = []

        # not sure if I need this as a field
        self.changed_values = {}

    def __repr__(self):
        return f"LineInfo(type={self.type}, line={self.original_line}, execution_id={self.execution_id}, additional_line: {self.uncolored_additional_line})"

    def __str__(self):
        return self.__repr__()

    def create_formatted_line(self, var_names, values):
        line = cf.cyan("  #") if self.print_mode == "console" else "  #"
        num_vars = len(var_names)
        # construct formatted_line
        line_has_variables = False
        for i in range(num_vars):
            var_name, value = var_names[i], values[i]
            if var_name != "":
                line_has_variables = True
            new_part = f" {var_name} = {value}"

            # add a comma for all but last element
            if  i < num_vars - 1:
                new_part += ","
            line += new_part

        # don't print anything if there are no variables, happens on last loop condition evaluation: for i in range(0)
        if line_has_variables:
            self.formatted_line = "".join(line)


    def print_line(self):
        if self.print_mode == "json":
            return
        # todo: add uncolored_formatted_line, uncolored_original_line
        original_line =  f"{cf.cyan(f'*  {self.line_number} │  ')}{self.original_line.lstrip(' ')}"
        formatted_line = f"{original_line} {self.formatted_line}"
        print(formatted_line)
        if self.additional_line:
            print(self.additional_line)


    def add_return(self, fxn_name, returned_value):
        self.type = "return"
        self.returned_value = returned_value
        self.returned_function = fxn_name

    def print_return(self):
        if self.type != "return":
            raise ValueError(f"Cannot print return for line: {self}")
        print(f"{cf.cyan(f'{self.returned_function} returned')} {self.returned_value}")



class Function:
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

        self.print_mode = "json"
        self.lines = []

        self.in_loop_declaration = False
        # loops = [LineInfo[], LineInfo[], LineInfo[], ..., LineInfo[], LineInfo[], LineInfo[]]
        self.loops = []

        self.object_prefix = object_prefix
        self.file_name = file_name
        self.function_signature = function_signature
        self.execution_id = execution_id
        self.latest_execution_id = execution_id
        # need to ensure that if a new function is called, that the next line has the correct execution_id
        # need one source of truth for this in the root tracer class
        # -- now we write to the JSON file here I think, then we 
        self.function_transition = False
        self.just_printed_return = False
        self.just_returned = False
        self.prev_line_code = ""
        self.self_in_locals = False

        # self.caller_execution_id = sjdcnkasjdncdjka

    def __repr__(self):
        return f"Function(signature={self.function_signature})"

    def print_line(self):
        if self.lines:
            self.lines[-1].print_line()


    def add_exception(self, function_name, arg):
        # todo: replace function_name with self.function_signature
        tb = ''.join(traceback.format_exception(*arg)).strip()
        print('%s raised an exception:%s%s' % (function_name, os.linesep, tb))
        pass

    def print_on_return(self, fxn_name, arg):
        # reset this value once we leave a function (we set this to true if self in locals)
        self.self_in_locals = False
        self.lines[-1].add_return(fxn_name, arg)
        self.lines[-1].print_return()


    def initialize_locals(self, curr_line_locals):
        # called when a new function is found
        # todo: test this now that it also calls add_object_fields_to_locals
        curr_line_locals_set, curr_line_locals_dict = self.add_object_fields_to_locals(curr_line_locals)

        # curr_line_locals_set = self.convert_to_set(curr_line_locals.items())
        self.prev_line_locals_set.update(curr_line_locals_set)
        self.prev_line_locals_dict.update(curr_line_locals_dict)

    def get_assignment_and_expression(self):
        equals_idx = self.prev_line_code.index("=")
        assignment, expression = self.prev_line_code[:equals_idx].strip(), self.prev_line_code[equals_idx+1:].strip()
        return assignment, expression


    def store_nested_objects(self, curr_line_locals_dict, locals_with_objects):
        for name,value in curr_line_locals_dict.items():
            if not self.is_custom_object(name, value):
                continue
            tracked_name = f"{self.object_prefix}{name}"
            # need to deepcopy o.w this value (stored in prev_line_locals_stack_dict -- will update this variable immediatley
            # ie: fields = {"sub_object": <__main__.SomeOtherObject object at 0x7fb745d8e710>, "z": 10}
            fields = vars(value)
            fields_copy = deepcopy(fields)
            locals_with_objects[tracked_name] = fields_copy
            del locals_with_objects[name]
            self.store_nested_objects(fields, locals_with_objects[tracked_name])

    def is_custom_object(self, name, value):
        # https://docs.python.org/3/library/inspect.html#fetching-attributes-statically
        # -- hasatr can cause code to execute !!!
        # todo: CHANGE
        return hasattr(value, "__dict__")
        # https://stackoverflow.com/a/52624678
        #^ wont work with __slots__
        # will only detect user defined types

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
        curr_line_locals_set, curr_line_locals_dict = self.add_object_fields_to_locals(curr_line_locals_dict)
        new_variables = curr_line_locals_set - self.prev_line_locals_set

        # Note: need curr_line_locals_dict since it is a dict and curr_line_locals_set is a set
        changed_values = {
            key: curr_line_locals_dict[key] # now the key stores the new value
            for key,_
            in new_variables
        }
        # print("changed", changed_values, "=====", curr_line_locals_dict, "new_variables", new_variables)
        if self.function_transition and not changed_values:
            return

        # Note on classes:
        #     def Vector(x, y)
        #     ...
        #     y = Vector(0, 1)
        # -- first the variables x, y, self are created in the LOCAL SCOPE BEFORE the new function call appends a set() to the self.prev_line_locals_stack stack
        # todo: do I still need this ?
        if not self.self_in_locals and "self" in changed_values:
            self.self_in_locals = True
            print("============== self in locals, returning...")
            return
        # todo: this call should not be done here
        self.gather_additional_data(changed_values)
        self.replace_old_values(changed_values)


    def construct_formatted_line(self, changed_values):
        # add interpreted comment to the current line
        # ie show: * 123 | x = y  # x = 10
        # move if statement to function named: "construct_formatted_line()
        if self.assigned_constant():
            # self.lines[-1].formatted_line = ""
            # -- maybe create a LineInfo object that has changed values and each function has an array of these
            return

        self.interpret_expression(changed_values)


    def construct_additional_line(self, changed_values):
        added_additional_line = False
        for (var_name, old_value) in self.prev_line_locals_dict.items():
            if var_name not in changed_values:
                continue
            new_value = changed_values[var_name]
            if var_name.startswith(self.object_prefix):
                # remove prefix: _TRACKED
                var_name = var_name[9:]
            colored_new_part = cf.red(f"  {var_name}={old_value}") + " ──> " + cf.green(f"new value: {new_value}")
            uncolored_new_part = f"  {var_name}={old_value}" + " ──> " + f"new value: {new_value}"
            if added_additional_line:
                self.lines[-1].additional_line += ","
                self.lines[-1].uncolored_additional_line += ","
            self.lines[-1].additional_line += colored_new_part
            self.lines[-1].uncolored_additional_line += uncolored_new_part
            added_additional_line = True

    def gather_additional_data(self, changed_values):
        """
            we need to gather additional data if either:
                1. non-simple assignment  ie: x = "a string".split() * 2 + ["a"]
                2. variable has new value ie: x = 11; x = 22
        """
        # if self.function_transition and not changed_values:
        #     # print(f"function_transition, changed_values: {changed_values}")
        #     # here, we return BEFORE entering a new function
        #     # print("need to print function, returning...")
        #     return

        # print("before additional line", changed_values)
        self.construct_formatted_line(changed_values)
        if not self.is_loop():
            # changed_values is popping !!!
            self.construct_additional_line(changed_values)


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
        value: Any = ""
        var_name = ""

        assignment, expression = self.get_assignment_and_expression()
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
            value = self.prev_line_locals_dict[var_name]
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
        return name


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
        # print(f"handle_object_expression assignment: {assignment}, expression: {expression}, changed_values: {changed_values}")

        if "." not in assignment and "." not in expression:
            if assignment in changed_values:
                return assignment, changed_values[assignment]
            if len(changed_values) == 1:
                return deepcopy(changed_values).popitem()
            return assignment, expression

        if "self" in assignment or "self" in expression:
            if assignment in changed_values:
                return assignment, changed_values[assignment]
            return assignment, expression

        assignment_field_chain = assignment.split(".")
        expression_field_chain = expression.split(".")
        object_field_assigned = len(assignment_field_chain) > 1
        object_field_in_expression = len(expression_field_chain) > 1

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
            object_name = self.generate_object_name(expression_field_chain, self.prev_line_locals_dict)
            value = None
            for field in object_name.split("."):
                value = value[field] if value else self.prev_line_locals_dict[field]

            # do I need to change the var_name ?????

        # TODO: iterate over subobjects and remove _TRACKED_ from the name
    # vect={'y': 22, '_TRACKED_x': {'o': 0}} ──> new value: {'y': 22, '_TRACKED_x': {'o': 99}}

        return var_name, value


    def interpret_expression(self, changed_values):
        # x = "="
        # x.add(" = ")
        # fn(" = ")
        has_bracket = "(" in self.prev_line_code
        is_assignment = (
            # Note: this doesnt work for func().value = 10 -- it says if there are "(", "=", and "=" is before "(" then its an assignment
            # -- actually it usually works, cuz if changed_values: then it will run, but it wont if you do func().value = 10 and value is already 10
            "=" in self.prev_line_code and "(" in self.prev_line_code and self.prev_line_code.index("=") < self.prev_line_code.index("(")
        ) or "=" in self.prev_line_code
        # this is wrong, what if the equals sign is in a string
        # what if this just returns things instead of printing them, then I can do multiple assignments recursively...
        # assuming no spaces means its getting assigned a variable such as self.x = x
        if is_assignment:
            self.in_loop_declaration = False

        if self.is_loop():
            # print("changed_values", changed_values)
            # var_name, value = changed_values.popitem()
            # TODO: test with a variable with multiple assignment in a loop
            self.lines[-1].create_formatted_line(list(changed_values.keys()), list(changed_values.values()))
            # HOW TO ENFORCE NOT HAVING ADDITIONAL_LINE FOR LOOPS
            # print("LOOPPPPP, changed_values", changed_values, "is_assignment", is_assignment, "prev_line_code", self.prev_line_code)
        elif len(changed_values) > 0 or is_assignment:
            self.in_loop_declaration = False
            # assignment, expression = self.get_assignment_and_expression()
            var_names, values = self.extract_variable_assignments(changed_values)
            self.lines[-1].create_formatted_line(var_names, values)



    # change name(s) since I store var_name, value tuples, not key_val tup's
    def prev_line_k_v_pairs(self, changed_values_keys):
        # need the previous values in order to remove them from "prev_line_locals_stack"
        # ie: if x got changed to 10, this stores: (x, prev_value)
        # todo: change to generator
        return [
                (key, v)
                for (key, v) in self.prev_line_locals_set
                if key in changed_values_keys
        ]


    def replace_old_values(self, changed_values):
        # need to update since this is a set of pairs so we cant just update the value for this variable
        # remove old values according to changed_values
        # they are different here, the dict has the new values already
        for key_val_pair in self.prev_line_k_v_pairs(changed_values):
            self.prev_line_locals_set.remove(key_val_pair)
            del self.prev_line_locals_dict[key_val_pair[0]]

        # replace old values according to changed_values
        changed_values_set = self.convert_to_set(changed_values.items())
        self.prev_line_locals_set.update(changed_values_set)
        self.prev_line_locals_dict.update(changed_values)


    def is_loop(self):

        # purpose is to support multi-line loop declarations but maybe this should be done diff
        if self.in_loop_declaration:
            return True
        # todo: set in_loop_declaration to false
        stripped_code = self.prev_line_code.lstrip()
        in_loop = " " in stripped_code and stripped_code.split()[0] in ("for", "while")
        if self.in_loop_declaration or in_loop:
            self.in_loop_declaration = True
            return True

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

    def make_hashable(self, value):
        # print("value", value, "type", type(value))
        if isinstance(value, GeneratorType):
            return value
        elif isinstance(value, dict):
            # todo: recurse over nested dicts
            return tuple(self.make_hashable(idk) for idk in value.items())
        elif isinstance(value, (tuple, list)):
            return tuple(self.make_hashable(idk) for idk in value)
        # todo: change to static hasattr?
        elif hasattr(value, "__hash__"):
            return value
        else:
            return value


    def convert_to_set(self, locals):
        hashable_locals = set()
        for var_name, value in locals:
            value = self.make_hashable(value)
            hashable_locals.add((var_name, value))
        return hashable_locals

    def add_next_line(self, frame):
        # print("added next line")
        skip_lane = "with" in self.prev_line_code
        next_line_executed = inspect.getframeinfo(frame).code_context[0].rstrip() if not skip_lane else ""
        self.prev_line_code = next_line_executed
        self.prev_line_number = frame.f_lineno


    def add_original_code(self):
        if self.just_printed_return:
            self.just_printed_return = False
            return

        if self.prev_line_code == "":
            return

        # should do more stuff instead of always printing lstrip'd lines
        # need to show conditionals/their indentations better.
        # TODO: check if this is a loop or something
        self.lines.append(LineInfo(self.prev_line_code, self.latest_execution_id, "code", self.prev_line_number, self.print_mode))
        self.latest_execution_id += 1


    def add_json(self, json):
        # this will be called before the function is returned
        self.lines[-1].function_json = json

    def to_json(self):
        self.construct_json_object(self.lines)
        return self.json

    def construct_json_object(self, lines):
        # an array of lines
        self.json = [{} for _ in range(len(lines))]
        for idx, line in enumerate(lines):
            # todo: only add json if the field exists in order to reduce size of json
            self.json[idx] = {
                "execution_id": line.execution_id,
                # "file_name": self.file_name,
                "line_number": line.line_number,
                "original_line": line.original_line,
                # "formatted_line": line.formatted_line,
                # "additional_line": line.uncolored_additional_line,
                # "type": line.type,
                "function_json": line.function_json,
            }
            # if line.type == "code":
            #     self.json[idx].update({
            #         "formatted_line": line.formatted_line,
            #         "additional_line": line.additional_line,
            #     })
            if line.type == "loop":
                self.json[idx]["loop_iterations"] = self.construct_json_object(self.loops[line.loop_idx])
            if line.type == "return":
                self.json[idx]["returned_function"] = line.returned_function
                self.json[idx]["returned_value"] = line.returned_value





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
        self.object_prefix = "_TRACKED_"
        self.execution_id = 0
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
        self.function_stack.append(None)
        sys.settrace(self.once_per_func_tracer)


    def done_tracing(self):
        return not self.first_function and len(self.function_stack) == 1 and self.function_stack[0] is None

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # NOTE: this is called when a error occurs internally
        sys.settrace(self.prev_trace) # has to be the first line or we get weird errors

    def once_per_func_tracer(self, frame, event, arg):
        # how this works: -- this function is called each new function and it prints "calling {signature}" then returns the trace_lines tracer for the next part
        name = frame.f_code.co_name
        if event == 'call':
            print(f"first_function: {self.first_function}, function_stack: {self.function_stack}")
            if self.done_tracing():
                return
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
                self.print_on_func_call(frame.f_code.co_filename, name, fxn_args)
                self.first_function = False
            else:
                self.function_stack[-1].function_transition = True

            if self.trace_this_func(name):
                return self.trace_lines
            # print(inspect.getcomments(frame.f_code))
            # comments will need to be read from the file along with the lines they appear in

        print("=============== no tracer returned kinda")
        return self.once_per_func_tracer

    def trace_this_func(self, fxn_name):
        # if fxn_name in list(should_trace): return True
        return True



    def on_return(self, frame, arg):
        # get json data for this function before we delete its data
        self.function_stack[-1].print_on_return(frame.f_code.co_name, arg)
        json = self.function_stack[-1].to_json()
        # TODO: store this json in the calling class

        # TODO: set flag so that we dont print the original function as if its getting called again
        # -- this is whats causing my error, I add the function to the stack twice
        # ie: currently, v = Vector() will do "calling __init__..."
        # then when __init__ returns, it will print "calling test_custom_objects" before doing the next line in the original function

        # pop the function's variables
        self.function_stack.pop()
        if not self.done_tracing():
            self.function_stack[-1].add_json(json)
            # is this correct below here ? we're setting just_printed_return for a diff functin that returned (the popped one)
            self.function_stack[-1].just_printed_return = True
            self.function_stack[-1].just_returned = True
        else:
            # not sure if this is the correct json
            if False:
                pprint(json, sort_dicts=False)
        # print("AFTER pop", self.function_stack)


    def trace_lines(self, frame, event, arg):
        """ called before "next_line_executed" is ran, so we see the changes in frame.f_locals late

        WHEN TO UPDATE THE FUNCTION'S EXECUTION_ID
        solution: we pass execution_id to Function at the beginning of this function
            then at the end of this function, we get the new one from the function stack
            and the other function only updates this value if a printed line exists
            ie:
                - set execution_id --> self.function_stack[-1].latest_execution_id = self.execution_id
                - end of function --> self.execution_id = self.function_stack[-1].latest_execution_id

            this allows new functions to always have the right id
            and also allows the function object to determine if the value should be incremented based on the code found

            maybe pass a reference ? feels wrong but is simple to make sure everything is up to date
        """
        # clear last results
        # maybe we pass this as a reference
        self.function_stack[-1].latest_execution_id = self.execution_id

        curr_line_locals_dict = frame.f_locals #.copy()
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

        if not self.function_stack[-1].prev_line_locals_dict:
            # appended for each new function call so we have variables local to the current function
            # this happens when new functions are called and all the function args are added to locals at once right below
            self.function_stack[-1].initialize_locals(curr_line_locals_dict)

        # prints the current line about to execute
        self.function_stack[-1].add_original_code()


        # if not self.function_stack[-1].function_transition:
        self.function_stack[-1].update_stored_vars(curr_line_locals_dict)
        self.execution_id =  self.function_stack[-1].latest_execution_id
        # else:
        #     print(self.function_stack[-1].lines[-1])

        self.function_stack[-1].print_line()

        if self.function_stack[-1].function_transition:
            # append set() to prev_line_locals_stack, then add the initial function args to this set
            if not self.function_stack[-1].just_returned:
                self.add_new_function_args_to_locals(frame, curr_line_locals_dict)
            self.function_stack[-1].function_transition = False
            # print("new function", self.function_stack)
        if self.function_stack[-1].just_returned:
            self.function_stack[-1].just_returned = False
        if event == 'return':
            self.on_return(frame, arg)
            # print("after return", self.function_stack)
            if len(self.function_stack) == 1 and self.function_stack[0] == None:
                return

        # do this at the end since update_locals uses prev_line_code
        self.function_stack[-1].add_next_line(frame)



    def add_new_function_args_to_locals(self, frame, curr_line_locals_dict):
        """
            Append set() to prev_line_locals_stack,
            then add the initial function args to this set
        """
        # this stays here since it inits stuff
        name = frame.f_code.co_name
        fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
        self.print_on_func_call(frame.f_code.co_filename, name, fxn_args)

        self.function_stack[-1].initialize_locals(curr_line_locals_dict)

        # print("new function, just made locals:", self.prev_line_locals_stack[-1])


    def add_new_function(self, file_name, signature):
        self.function_stack.append(Function(file_name, self.object_prefix, signature, self.execution_id + 1))
        # this causes immediate prints instead of deferring prints to this class
        self.function_stack[-1].print_mode = "console"


    def print_on_func_call(self, file_name, fxn_name, fxn_args):
        # add to variable stack
        # pop from function stack when I leave)
        signature = fxn_name + fxn_args
        self.add_new_function(file_name, signature)
        # TODO: move  this line elsewhere
        print(cf.yellow(f'... calling {signature}'))
