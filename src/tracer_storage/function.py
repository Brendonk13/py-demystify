import traceback
import inspect
import os
import re
from typing import List, Any, Dict, ItemsView
from types import GeneratorType, FrameType
from collections import deque
from itertools import islice

import colorful as cf

from . import Line
from . import Loop
from ..helpers import TracingError, get_file_name, get_fxn_signature, print_all_iterations

class Function:
    """
    now "parent" class will store an array of FunctionTracer's rather than an array of dicts and sets
    but what happens when a new nested function is found, we would want the parent function to do that
    -- this is confusing

    maybe this only stores the variables and handles finding new values through implementing __hash__
    """
    # def __init__(self, file_name, object_prefix, fxn_signature, execution_id, fxn_name):
    def __init__(self, frame: FrameType, execution_id: int, object_prefix="_TRACKED_", num_loops_stored=3, print_offset: int = 0):
        # need info from the previous function
        self.prev_line_locals_set = set()
        self.prev_line_locals_dict = dict()
        file_name = get_file_name(frame)
        # fxn_name = get_fxn_name(frame)
        fxn_signature = get_fxn_signature(frame)

        self.print_offset = print_offset

        # -- Note: even if we used a database to write intermediate results to reduce memory complexity, we would still need
        # to store the sets/dicts of locals in memory since we need the actual object references and types, etc
        # the real memory hog will be these variables, thus: a database wont help with the bottleneck and we dont need it
        # so the question is: how much will a database help ?
        self.type = "fxn_start"
        # used for when self.type = "fxn_call" || "loop"

        # note: main tracer will need to find execution_id from other spots often: --> self.fxn_stack[-1].lines[-1].execution_id
        # cuz the main loop will see a new function and will have to iterate check self.fxn_stack[-1].lines[-1].execution_id

        self.num_loops_stored = num_loops_stored

        self.print_mode = "json"
        self.lines: List[Line] = []
        # self.loop_lines: List[Line] = []

        self.in_loop_declaration = False
        self.loop_stack: List[Loop]  = []

        # self.deleted_lines = set()

        self.object_prefix = object_prefix
        self.file_name = file_name
        self.fxn_signature = fxn_signature
        self.execution_id = execution_id
        self.latest_execution_id = execution_id

        # need to ensure that if a new function is called, that the next line has the correct execution_id
        # need one source of truth for this in the root tracer class
        # -- now we write to the JSON file here I think, then we 
        self.fxn_transition = False
        self.just_printed_return = False
        self.just_returned = False
        self.prev_line_code = ""
        self.self_in_locals = False

        # self.caller_execution_id = sjdcnkasjdncdjka

    def __repr__(self):
        return f"Function(signature={self.fxn_signature})"

    def print_line(self):
        lines = self.get_current_lines()
        if lines:
            # if self.loop_stack:
            #     print("num loops:", len(self.loop_stack), "num iters:", len(self.loop_stack[-1].iterations), self.loop_stack[-1].iterations)
            lines[-1].print_line()

    def print_on_func_call(self, fxn_signature, line_number):
        lines = self.get_current_lines()
        # if not self.loop_stack:
        lines.append(Line(fxn_signature, self.latest_execution_id, "fxn_call", line_number, self.print_mode, self.print_offset))
        # else:
            # self.loop_lines.append(Line(fxn_signature, self.latest_execution_id, "fxn_call", line_number, self.print_mode))
        # self.loop_lines[-1].line_idx = len(self.lines) - 1

        self.latest_execution_id += 1
        if self.print_mode == "debug":
            print(cf.yellow(f'{(self.print_offset - 1) * 2 * ' '}... calling {fxn_signature}'))


    # todo: get the type of the arg
    def add_exception(self, arg):
        # todo: test
        lines = self.get_current_lines()
        tb = ''.join(traceback.format_exception(*arg)).strip()
        lines.append(Line(tb, self.latest_execution_id, "exception", self.prev_line_number, self.print_mode, self.print_offset))
        if self.print_mode == "debug":
            print('%s raised an exception:%s%s' % (self.fxn_signature, os.linesep, tb))


    def print_on_return(self, fxn_name: str, fxn_signature: str, returned_value: Any):
        # reset this value once we leave a function (we set this to true if self in locals)
        self.self_in_locals = False
        lines = self.get_current_lines()
        # if not self.loop_stack:
            # self.lines[-1].add_return(fxn_name, fxn_signature, returned_value)
            # self.lines[-1].print_return()
        # else:
        lines[-1].add_return(fxn_name, fxn_signature, returned_value)
        lines[-1].print_return()


    def initialize_locals(self, curr_line_locals: Dict[str, Any]):
        # called when a new function is found
        # todo: test this now that it also calls add_object_fields_to_locals
        curr_line_locals_set, curr_line_locals_dict = self.add_object_fields_to_locals(curr_line_locals)

        # curr_line_locals_set = self.convert_to_set(curr_line_locals.items())
        self.prev_line_locals_set.update(curr_line_locals_set)
        self.prev_line_locals_dict.update(curr_line_locals_dict)

    def get_assignment_and_expression(self):
        if "=" not in self.prev_line_code:
            return "", ""
        equals_idx = self.prev_line_code.index("=")
        assignment, expression = self.prev_line_code[:equals_idx].strip(), self.prev_line_code[equals_idx+1:].strip()
        return assignment, expression


    def store_nested_objects(self, curr_line_locals_dict: Dict[str, Any], locals_with_objects: Dict[str, Any]):
        """
        for each object, add all fields to locals_with_objects
        """
        # what If I have seperate storage for custom objects so that I don't need to deepcopy stuff
        for name,value in curr_line_locals_dict.items():
            if not self.is_custom_object(value):
                locals_with_objects[name] = value
                continue
            tracked_name = f"{self.object_prefix}{name}"
            # need to deepcopy o.w this value (stored in prev_line_locals_stack_dict -- will update this variable immediatley
            # ie: fields = {"sub_object": <__main__.SomeOtherObject object at 0x7fb745d8e710>, "z": 10}
            fields = vars(value)
            fields_copy = fields.copy()
            # fields_copy = deepcopy(fields)
            locals_with_objects[tracked_name] = fields_copy
            # del locals_with_objects[name]
            self.store_nested_objects(fields, locals_with_objects[tracked_name])



    def is_custom_object(self, value: Any):
        # https://docs.python.org/3/library/inspect.html#fetching-attributes-statically
        # -- hasatr can cause code to execute !!!
        # todo: CHANGE
        return hasattr(value, "__dict__")
        # https://stackoverflow.com/a/52624678
        #^ wont work with __slots__
        # will only detect user defined types

    def add_object_fields_to_locals(self, curr_line_locals_dict: Dict[str, Any]):
        """
            - create deepcopy of function locals
            - for each object in local, extract its fields/values and store that instead
            - create a set from this dict so we can see which values are new in calling function
        """

        # create a copy so we can delete the root objects and only store their field from vars()
        # print("LOCALS", curr_line_locals_dict)
        # for k, v in curr_line_locals_dict.items():
        #     if isinstance(v, 
        # locals_with_objects = deepcopy(curr_line_locals_dict)
        locals_with_objects = {}
        # print("locals_with_objects", locals_with_objects, "locals_dict", curr_line_locals_dict)
        self.store_nested_objects(curr_line_locals_dict, locals_with_objects)

        curr_line_locals_set = self.convert_to_set(locals_with_objects.items())
        # return curr_line_locals_set, curr_line_locals_dict, curr_line_objects
        return curr_line_locals_set, locals_with_objects


    def update_stored_vars(self, curr_line_locals_dict: Dict[str, Any]):
        """ need to make lists hashable somehow for storing lists in the set.
            maybe I store lists differently
            and give the option to search lists for if a certain value appears
            could eventually make it so u pass a parameter to @trace which
            will look thru lists and return the values changed in a list as well
            as the indices where they are found.
        """
        # NOTE: I didnt need this before I did all the loop stuff
        if self.prev_line_code == "":
            print("BYE")
            return
        curr_line_locals_set, curr_line_locals_dict = self.add_object_fields_to_locals(curr_line_locals_dict)
        new_variables = curr_line_locals_set - self.prev_line_locals_set

        # Note: need curr_line_locals_dict since it is a dict and curr_line_locals_set is a set
        changed_values = {
            key: curr_line_locals_dict[key] # now the key stores the new value
            for key,_
            in new_variables
        }
        if self.fxn_transition and not changed_values:
            return
        if self.is_assignment():
            self.in_loop_declaration = False
        # if self.is_loo

        # print("changed", changed_values, "=====", curr_line_locals_dict, "new_variables", new_variables)

        # Note on classes:
        #     def Vector(x, y)
        #     ...
        #     y = Vector(0, 1)
        # -- first the variables x, y, self are created in the LOCAL SCOPE BEFORE the new function call appends a set() to the self.prev_line_locals_stack stack
        if not self.self_in_locals and "_TRACKED_self" in changed_values and "__init__" not in self.fxn_signature:
            # Why needed, for prev_line_code: 'vect = Vector(0, 1)'
            # class Vector: def __init__(self, x, y, z=None): 
            # we have changed_values: {'z': None, 'y': 1, 'x': 0, '_TRACKED_self': {}}
            # if we wait one iteration, __init__ gets called and we add all function args like we do every new fxn call
            self.self_in_locals = True
            print(f"============== self in locals, returning..., prev_line: {self.prev_line_code}, changed_values: {changed_values}")
            return
        # todo: this call should not be done here
        self.gather_additional_data(changed_values)
        # self.replace_old_values(changed_values)
        self.prev_line_locals_set = curr_line_locals_set
        self.prev_line_locals_dict = curr_line_locals_dict


    def construct_formatted_line(self, changed_values: Dict[str, Any]):
        # add interpreted comment to the current line
        # ie show: * 123 | x = y  # x = 10
        # move if statement to function named: "construct_formatted_line()
        if self.assigned_constant():
            # self.lines[-1].formatted_line = ""
            # -- maybe create a Line object that has changed values and each function has an array of these
            return

        self.interpret_expression(changed_values)


    def construct_additional_line(self, changed_values: Dict[str, Any]):
        line = self.get_most_recent_line()
        added_additional_line = False
        for (var_name, old_value) in self.prev_line_locals_dict.items():
            if var_name not in changed_values:
                continue
            new_value = changed_values[var_name]
            if var_name.startswith(self.object_prefix):
                # remove prefix: _TRACKED
                var_name = var_name[9:]
            print_offset = self.print_offset * 2 * ' '
            colored_new_part = print_offset + cf.red(f"{var_name}={old_value}") + " --> " + cf.green(f"{new_value}")
            uncolored_new_part = print_offset + f"{var_name}={old_value}" + " --> " + f"{new_value}"
            if added_additional_line:
                line.additional_line += ","
                line.uncolored_additional_line += ","
            line.additional_line += colored_new_part
            line.uncolored_additional_line += uncolored_new_part
            added_additional_line = True

    def gather_additional_data(self, changed_values: Dict[str, Any]):
        """
            we need to gather additional data if either:
                1. non-simple assignment  ie: x = "a string".split() * 2 + ["a"]
                2. variable has new value ie: x = 11; x = 22
        """
        # if self.fxn_transition and not changed_values:
        #     # print(f"fxn_transition, changed_values: {changed_values}")
        #     # here, we return BEFORE entering a new function
        #     # print("need to print function, returning...")
        #     return

        self.construct_formatted_line(changed_values)
        if not self.is_loop():
            # changed_values is popping !!!
            # print("before additional line", changed_values)
            self.construct_additional_line(changed_values)


    def extract_variable_assignments(self, changed_values: Dict[str, Any]):
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

        # if (
        #     len(changed_values) == 0
        #     and len(expression.split()) == 1 and "(" not in expression # RHS has no spaces, "(" -- straight assignment ie: x = y
        # ):
        #     # Note: this conditional handles __init__()
        #     # Think this is supposed to do substitution
        #     # this happens for self.y = y
        #     # THIS IS BECAUSE WE DONT CHECK FOR CHANGES TO SELF CURRENTLY THEREFORE CHANGED_VALUES = {}
        #     print("changed_values, ", changed_values, f"assignmnet: {assignment}, expression: {expression}")
        #     print(self.prev_line_code)
        #     var_name = expression
        #     value = self.prev_line_locals_dict[var_name]
        #     print("extract_variable_assignments no changed values")
        #     return [var_name], [value]

        if "," in assignment and assignment != expression and len(assignment.split(",")) == len(expression.split(",")):
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
        elif len(changed_values) == 0:
            return [""], [""]
        else:
            # raise TracingError(f"Unexpected conditional case, changed_values: {changed_values}, curr_line_objects: {curr_line_objects}")
            raise TracingError(f"Unexpected conditional case, changed_values: {changed_values}")


    def generate_object_name(self, field_chain: List[str], changed_values: Dict[str, Any]):
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


    def handle_object_expression(self, assignment: str, expression: str, changed_values: Dict[str, Any]):
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
                # return deepcopy(changed_values).popitem()
                return changed_values.copy().popitem()
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


    def is_assignment(self):
        # x = "="
        # x.add(" = ")
        # fn(" = ")
        return (
            # Note: this doesnt work for func().value = 10 -- it says if there are "(", "=", and "=" is before "(" then its an assignment
            # -- actually it usually works, cuz if changed_values: then it will run, but it wont if you do func().value = 10 and value is already 10
            "=" in self.prev_line_code and "(" in self.prev_line_code and self.prev_line_code.index("=") < self.prev_line_code.index("(")
        ) or "=" in self.prev_line_code
        # this is wrong, what if the equals sign is in a string
        # what if this just returns things instead of printing them, then I can do multiple assignments recursively...
        # assuming no spaces means its getting assigned a variable such as self.x = x

    def interpret_expression(self, changed_values: Dict[str, Any]):
        # has_bracket = "(" in self.prev_line_code
        line = self.get_most_recent_line()

        if self.is_loop():
            # print("changed_values", changed_values)
            # var_name, value = changed_values.popitem()
            # TODO: test with a variable with multiple assignment in a loop
            line.create_formatted_line(list(changed_values.keys()), list(changed_values.values()), self.object_prefix)
            # HOW TO ENFORCE NOT HAVING ADDITIONAL_LINE FOR LOOPS
            # print("LOOPPPPP, changed_values", changed_values, "is_assignment", is_assignment, "prev_line_code", self.prev_line_code)
        elif len(changed_values) > 0 or self.is_assignment():
            # self.in_loop_declaration = False
            # assignment, expression = self.get_assignment_and_expression()
            var_names, values = self.extract_variable_assignments(changed_values)
            if var_names[0] == "" and values[0] == "":
                return
            line.create_formatted_line(var_names, values, self.object_prefix)



    # change name(s) since I store var_name, value tuples, not key_val tup's
    def prev_line_k_v_pairs(self, changed_values_keys: List[str]):
        # need the previous values in order to remove them from "prev_line_locals_stack"
        # ie: if x got changed to 10, this stores: (x, prev_value)
        # todo: change to generator
        return [
                (key, v)
                for (key, v) in self.prev_line_locals_set
                if key in changed_values_keys
        ]


    # def replace_old_values(self, changed_values: Dict[str, Any]):
    #     # need to update since this is a set of pairs so we cant just update the value for this variable
    #     # remove old values according to changed_values
    #     # they are different here, the dict has the new values already
    #     for key_val_pair in self.prev_line_k_v_pairs(changed_values):
    #         self.prev_line_locals_set.remove(key_val_pair)
    #         del self.prev_line_locals_dict[key_val_pair[0]]

    #     # replace old values according to changed_values
    #     changed_values_set = self.convert_to_set(changed_values.items())
    #     self.prev_line_locals_set.update(changed_values_set)
    #     self.prev_line_locals_dict.update(changed_values)


    def assigned_constant(self):
        expression = self.prev_line_code.split('=')[-1].strip()
        # todo make this find dicts, differentiate between {1:1} and {1:1, **other_dict}
        # maybe do opposite and search for non-constants
        # TODO: add case for +=, *=, etc -- these should be considered non-obvious
        if (
            expression.isdigit()
            or re.search(r'^".*"$', expression) # search for string assignment
            or re.search(r"^'.*'$", expression) # search for string assignment
            or expression.startswith('return') # TODO: delete this so we can do interpretations on return (-- then maybe just delete the "a_fn() returned XXX line)
        ):
                return True
        return False

    def make_hashable(self, value: Any):
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


    # def convert_to_set(self, locals: List[Tuple[str, Any]]):
    def convert_to_set(self, locals: ItemsView[str, Any]):
        hashable_locals = set()
        for var_name, value in locals:
            value = self.make_hashable(value)
            hashable_locals.add((var_name, value))
        return hashable_locals

    def add_next_line(self, frame: FrameType):
        # print ("ASJNXAJKSNJKLASNXJKLASNXLKJASNJKNSAKLJNXASK")
        skip_lane = "with" in self.prev_line_code
        next_line_executed = inspect.getframeinfo(frame).code_context[0].rstrip() if not skip_lane else ""
        # print(f"added next line, prev_line_code: {self.prev_line_code}, next_line_executed: {next_line_executed}")
        # print("prev_line", self.prev_line_code, "next line", next_line_executed)
        self.prev_line_code = next_line_executed
        self.prev_line_number = frame.f_lineno

    def get_current_lines(self):
        # if line_type in ("loop_start", "start_iteration") or self.loop_stack:
        # if self.loop_stack:
        #     print("curr: ", self.loop_stack[-1].iterations, f"loop stack: {self.loop_stack}")
        return self.lines if not self.loop_stack else self.loop_stack[-1].iterations[-1]

    def get_most_recent_line(self):
        lines = self.get_current_lines()
        # if not lines and self.loop_stack:
        #     # then we just wrote data from self.lines into self.loop_lines
        #     # here, will need to add data to self.loop_lines again before returning that
        #     return self.lines[-1]
        return lines[-1]


    def add_line(self):
        if self.just_printed_return:
            self.just_printed_return = False
            return False

        if self.prev_line_code == "":
            return False

        new_line = Line(self.prev_line_code, self.latest_execution_id, "code", self.prev_line_number, self.print_mode, self.print_offset)
        lines = self.lines

        if self.just_left_loop(new_line):
            # if just left loop, have already added line after loop to self.lines
            # todo: add the delete code here
            # print("just left loop")
            # -- need to compare with new_line, NOT lines[-2]
            # print(f"lines[-2]: {self.loop_stack[-1].iterations[-1][-2]}")
            # print(f"loop start line number: {self.loop_stack[-1].line.line_number}")
            if self.latest_execution_id < 26:
                print()
                print(f"BEFORE left loop")
                print(print_all_iterations(self.lines, self.loop_stack))
            loop = self.loop_stack[-1]
            self.write_last_iterations(loop)
            self.loop_stack[-1].iterations = deque() # free up memory, keep types happy
            self.loop_stack.pop()
            if self.latest_execution_id < 26:
                print()
                print(f"AFTER left loop")
                print(print_all_iterations(self.lines, self.loop_stack))
                print()


        # issue, need to add iteration, thennnn add line as the first line to it
        if self.started_another_loop_iteration():
            new_line.type = "start_iteration"
            # dont call get_most_recent_line here since we want to write to self.loop_lines regardless of whether its empty

        elif self.is_first_loop_line():
            new_line.type = "loop_start"
            self.loop_stack.append(Loop(line=new_line, start_line_number=self.prev_line_number))
            new_line.loop = self.loop_stack[-1]
            # maybe add print in the one that writes the iterations idk
            # print("============== NEW LOOP, LINE: {
            # new_line.loop.iterations.append([])


        # found_loop = False
        if new_line.type in ("loop_start", "start_iteration"):
            self.loop_stack[-1].iterations.append([])
            # print(f"New {new_line.type} for: {self.prev_line_code}, stack: {len(self.loop_stack[-1].iterations)}")
            # found_loop =True
            # attach the loop so that when we pop off the stack, we still have access to it

        if self.loop_stack:
            # print(f"in loop, stack: {self.loop_stack[-1]}")
            lines = self.loop_stack[-1].iterations[-1]

        lines.append(new_line)
        # print("LINES added to: ", lines)
        self.latest_execution_id += 1
        return True

        # self.mark_loop_events()


    def mark_loop_events(self):
        lines = self.get_current_lines()

        # if self.loop_stack:
        #     print(f"BEFORE mark loop, len(iters): {len(self.loop_stack[-1].iterations)}")
        if self.very_first_line_after_loop():
            # NOT WORKING!!!!!!!!!!!!!!!
            self.loop_stack[-1].first_loop_line = self.prev_line_number
            # print("VEWRYT FIRST", self.loop_stack[-1])

        if lines[-1].type == "start_iteration":
            # when a loop ends, we will USUALLY (breaks skip loop condition???) call this function to check the loop condition
            # then self.just_left_loop() will be called
            # -- maybe this section handles writing the first 3, and just_left_loop handles writing the last 3 iterations

            # print(f"mark loop new iteration, prev_line: {self.prev_line_code}, prev-line_num: {self.prev_line_number}, all start nums: {list(loop.start_line_number for loop in self.loop_stack)}")
            # print("mark loops new iter")
            loop = self.find_current_loop()
            self.write_first_iterations(loop)
            # if self.loop_stack:
            #     print(f"AFTER mark loop, len(iters): {len(self.loop_stack[-1].iterations)}")
            self.delete_iteration(loop)
            # print("AFTER mark loops new iter", lines)


    def get_parent_lines(self) -> List[Line]:
        """ if loop, return outter loop's most recent iteration """
        # need to also return the number of elements in all previous loops so I return the true index of a start
        if len(self.loop_stack) >= 2:
            # print(f"returning parent iteration {self.loop_stack[-2].iterations}")
            return self.loop_stack[-2].iterations[-1]
        return self.lines

    def write_last_iterations(self, loop):

        # print("WRITING LAST ITERATIONS")
        # print("loop_lines", self.loop_lines)
        # print()
        # print(f"loop.iterations: {loop.iterations}, loop: {loop} ")
        # print()

        lines = self.get_parent_lines()
        # print(f"write LAST for loop: {loop}")
        # print(f"all iterations: {self.loop_stack[-1].iterations}")
        num_iterations = len(self.loop_stack[-1].iterations)
        # print(list(islice(self.loop_stack[-1].iterations, num_iterations - self.num_loops_stored, num_iterations)))
        # write the last self.num_loops_stored
        # the last iteration has bogus, dont write
        # HOWEVER, we need to check just_left_loop() before appending self.lines, o.w we append first line AFTER the loop is exited here
        for iteration in islice(self.loop_stack[-1].iterations, num_iterations - self.num_loops_stored - 1, num_iterations - 1):
            # lines.append(iteration)
            # the first line in an iteration stores the metadata about it for easy converting to json
            iteration[0].line_idx = len(lines) # not minus one since we want the idx of this guy, after the end of the other list
            iteration[0].num_in_iteration = len(iteration)
            loop.iteration_starts.append(iteration[0])
            # the last 2 iterations dont have any data
            lines += iteration
            iteration[0].end_iteration_idx = len(lines) - 1
            print(f"writing LAST iteration: {iteration}")
            loop.debugging_iterations.append({
                "start_exec_id": iteration[0].execution_id,
                "end_exec_id": iteration[-1].execution_id,
                "length": len(iteration),
                "deleted": False,
                "next_exec_id": self.latest_execution_id,
            })

        # print(f"after writing, lines: {lines}")

    def very_first_line_after_loop(self):
        # Note: this only works once
        lines = self.get_current_lines()
        if len(lines) < 2:
            return False
            # raise TracingError(
            # f"need 2 lines to check very_first_line_after_loop(), lines: {lines}, loop_stack: {self.loop_stack}, lines: {self.lines}")
        # if self.loop_stack:
        #     print(f"checking v first, prev_line: {self.prev_line_code}, lines: {lines}, {self.loop_stack[-1].line}")
        return self.loop_stack and self.loop_stack[-1].line is lines[-2]

    def is_first_loop_line(self):
        first_token = self.prev_line_code.lstrip().split()[0]
        # if 2<= self.latest_execution_id <= 3:
        #     print(f"first token: {first_token}, first is in for, while: {first_token in ('for', 'while')}")
        return (
            first_token in ("for", "while")
            # check that this isnt just another iteration vs actual first iteration
            and self.prev_line_number not in (loop.start_line_number for loop in self.loop_stack)
        )

    def started_another_loop_iteration(self):
        first_token = self.prev_line_code.lstrip().split()[0]
        return (
            first_token in ("for", "while")
            # check that this loop start is in our current loops
            and self.prev_line_number in (loop.start_line_number for loop in self.loop_stack)
        )

    def find_current_loop(self):
        # for idx, loop in enumerate(self.loop_stack):
        for loop in self.loop_stack:
            if self.prev_line_number == loop.start_line_number:
                return loop

    def delete_iteration(self, loop):
        # if len(loop.iterations) >= self.num_loops_stored * 2 + 1:
        # plus one since we have an extra iteration: the unfinished one we just started before this fxn in add_iteration
        # we only want to delete completed iterations
        # plus one to account for there always being an iteration that just started which we dont count
        # -- we only want to delete an iteration if there are > self.num_loops_stored COMPLETED ITERATIONS
        if len(loop.iterations) > self.num_loops_stored + 1:
            deleted = loop.iterations.popleft()
            if self.latest_execution_id < 26:
                print(f"deleting iteration: {deleted}")

            loop.debugging_iterations.append({
                "start_exec_id": deleted[0].execution_id,
                "end_exec_id": deleted[-1].execution_id,
                "length": len(deleted),
                "deleted": True,
                "next_exec_id": self.latest_execution_id,
            })

    def write_first_iterations(self, loop: Loop):
        # when we have completed an iteration of the outmost loop, can write the first couple iterations (in self.loop_lines) to lines
        # could make this <= but then more logic

        # print(f"iterations: {loop.iterations}")
        # need to make sure the iteration is complete idk
        if len(loop.iterations) != self.num_loops_stored + 1 or loop.have_written_first_iterations:
            return
        # print(f"write firs for loop: {loop}")

        lines = self.get_parent_lines()
        # num_iterations = len(self.loop_stack[-1].iterations)
        # for _ in islice(self.loop_stack[-1].iterations, num_iterations - self.num_loops_stored - 1, num_iterations - 1):
        # for idx in range(len(loop.iterations[-1][:self.num_loops_stored])):
        for _ in range(self.num_loops_stored):
            iteration = loop.iterations.popleft()
            # the first line in an iteration stores the metadata about it for easy converting to json
            iteration[0].num_in_iteration = len(iteration)
            iteration[0].line_idx = len(lines) # not minus one since we want the idx of this guy, after the end of the other list
            loop.iteration_starts.append(iteration[0])
            print(f"writing FIRST iteration: {iteration}")
            lines += iteration
            iteration[0].end_iteration_idx = len(lines) - 1
            loop.debugging_iterations.append({
                "start_exec_id": iteration[0].execution_id,
                "end_exec_id": iteration[-1].execution_id,
                "length": len(iteration),
                "deleted": False,
                "next_exec_id": self.latest_execution_id,
            })


        loop.have_written_first_iterations = True
        # print(f"after writing, lines: {lines}")
        # loop.iterations.append([])


    def just_left_loop(self, new_line):
        # TODO: NOTE DONE
        # need to check that previous line[-2] is the start of a loop and that line[-1].line_number != IDK[-].first_loop_line
        # need to know if the previous line was a loop start
        # if self.loop_lines and self.loop_stack:
        #     print(f"just_left_loop, is first line after loop: {self.loop_lines[-1]}, loop stack: {self.loop_stack}")

        # if self.loop_stack:
        #     if self.latest_execution_id < 20:
        #         print("just left, iterations:", self.loop_stack[-1].iterations)

        # assuming there are >= 2 iterations -- implies one full iteration then one loop check, however, since we write the first one, this means at this code will only work with at least 3 iterations
        # Facts: len(iterations[-1]) == 1 (the new loop condition)
        if self.loop_stack and self.loop_stack[-1].iterations and self.loop_stack[-1].iterations[-1][-1].original_line == "break":
            # print("BREAK")
            return True
        if not self.loop_stack or len(self.loop_stack[-1].iterations) < 2:
            # print("RETURN")
            return False

        # lines = self.loop_stack[-1].iterations[-2]
        # curr_loop_start_line = self.loop_stack[-1].line.line_number

        def prev_line_was_loop_condition():
            lines = self.loop_stack[-1].iterations[-1]
            ans = lines[-1].line_number == self.loop_stack[-1].line.line_number
            # print(f"{self.prev_line_code}, prev_line_was_loop_condition: {ans}, prev line number: {lines[-1].line_number}, loop start number: {self.loop_stack[-1].line.line_number}")
            return ans

        def new_line_is_not_the_first_line_in_this_loop():
            # print(f"new_line_is_not_the_first_line_in_this_loop, new_line.line_number: {new_line.line_number}, first line in loop: {self.loop_stack[-1].first_loop_line}")
            return new_line.line_number != self.loop_stack[-1].first_loop_line

        return (
            # TODO: make sure break isnt just one line in a multiline string or something
            # self.prev_line_code.strip() == "break"
            # lines[-2].original_line.strip() == "break"
                prev_line_was_loop_condition()
                and new_line_is_not_the_first_line_in_this_loop()
                # lines[-2].line_number == curr_loop_start_line # we always check the loop condition before leaving loop, so if we left, the prev line must be loop condition
                # and self.loop_stack[-1].first_loop_line != -1 # check this value has been set
                # and self.loop_stack[-1].first_loop_line != self.prev_line_number # if the first line after a loop is not the expected value, the loop exited
                # NOTE: need to check that continues work properly
        )


    def is_loop(self):
        # return self.loop_stack
        # todo: combine this with other loop functions, it only is meant to test if we are in the start/middle of a loop declaration
        # purpose is to support multi-line loop declarations but maybe this should be done diff
        if self.in_loop_declaration:
            # print("================ IN LOOP DECLARATION", self.lines[-1])
            return True
        # todo: set in_loop_declaration to false
        # if self.in_loop_declaration or in_loop:
        if self.is_first_loop_line():
            # print(f"SET LOOP DECLARATION, code: {self.prev_line_code}, self: {self}")
            self.in_loop_declaration = True
            return True


    def add_json(self, json):
        # this will be called before the function is returned
        lines = self.get_current_lines()
        lines[-1].fxn_json = json

    def to_json(self):
        # print()
        # print_aligned_lines(self.lines)
        # print()
        self.json = self.construct_json_object(0, len(self.lines))
        # print()
        return self.json


    def construct_json_object(self, start_idx, end_idx, prev_loop_start=None, num_iters=0):
        # return [{"one": 1}]

        json = []
        idx = start_idx
        while idx < min(len(self.lines), end_idx):
            line = self.lines[idx]

            # print(f"idx: {idx}, start_idx: {start_idx}, end_idx: {end_idx}, line: {line}")
            # todo: only add json if the field exists in order to reduce size of json
            json.append({
                "execution_id": line.execution_id,
                "original_line": line.original_line,
                # "file_name": self.file_name,
                # "line_number": line.line_number,
                # "formatted_line": line.formatted_line,
                # "additional_line": line.uncolored_additional_line,
                "type": line.type,
                "fxn_json": line.fxn_json,
            })
            # if line.type == "code":
            #     json[idx].update({
            #         "formatted_line": line.formatted_line,
            #         "additional_line": line.additional_line,
            #     })
            # if line.type in ("loop_start", "start_iteration"):
            if line.type == "loop_start":
                if line.loop is None:
                    raise TracingError(f"loop start/iteration has no loop attached, line: {line}")
                if line == prev_loop_start:
                    idx += 1
                    continue

                # print()
                json[-1]["loop"] = []
                # print(f"found loop line: {line}, iterations: {line.loop.debugging_iterations}")

                # if num_iters > 3:
                # # if num_iters > -1:
                #     return json

                end_iter = end_idx
                start_iter = idx

                # print()
                # print("iteration starts, num iterations: ", len(line.loop.iteration_starts))
                for l in line.loop.iteration_starts:
                    end_iter = start_iter + l.num_in_iteration
                    # print(f"loop starts: start: {start_iter}, end: {end_iter}, num_in_iteration: {l.num_in_iteration}")
                    # print(f"start line: {self.lines[start_iter]}, end line: {self.lines[end_iter]}")
                    start_iter = end_iter
                # print()

                end_iter = end_idx
                start_iter = idx

                for start_line in line.loop.iteration_starts:
                    # print(f"json'ing from start line: {start_line}")

                    end_iter = start_iter + start_line.num_in_iteration
                    # print(f"start_iter: {start_iter}, end: {end_iter}")
                    # print()
                    iteration_lines = self.construct_json_object(start_iter, end_iter, line, num_iters + 1)
                    json[-1]["loop"].append(iteration_lines)
                    start_iter = end_iter
                idx = end_iter - 1
            if line.type == "return":
                json[-1]["returned_function"] = line.returned_function
                json[-1]["returned_value"] = line.returned_value
            idx += 1
        return json

