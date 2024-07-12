from typing import Any, List, Optional

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import Terminal256Formatter
import colorful as cf

from ..helpers import strip_inline_comments, TracingError

class Line:
    def __init__(self, code: str, execution_id: int, type: str, line_number: int, print_mode: str, print_offset: int = 0):
        # done here to remove circular import
        from . import Loop

        # other: line_num
        self.original_line = code.lstrip(" ")
        # todo: add type information for all changes
        self.formatted_line = ""
        # todo: add type information for all changes
        self.additional_line = ""
        self.uncolored_additional_line = ""
        self.execution_id = execution_id
        self.type = type
        # only relevant if type == "loop_start"
        self.loop_idx = 0
        self.strip_comments = True
        self.syntax_highlight = True
        self.line_number = line_number
        # means that we produce a json file
        self.print_mode = print_mode
        self.fxn_json = []

        self.print_offset = print_offset

        # for loops
        self.num_in_iteration = 0

        self.line_idx = -1
        self.end_iteration_idx = -1

        # have access to loop info for easy parsing to json
        self.loop: Optional[Loop] = None

        # not sure if I need this as a field
        self.changed_values = {}

    def __repr__(self):
        # return f'Line(type={self.type}, line="{self.original_line}", execution_id={self.execution_id}, additional_line: {self.uncolored_additional_line})'
        return f'Line(exec_id={self.execution_id}, code="{self.original_line}", type={self.type})'

    def __str__(self):
        return self.__repr__()

    def create_formatted_line(self, var_names: List[str], values: List[Any], object_prefix: str):
        line = cf.cyan("  #") if self.print_mode == "debug" else "  #"
        num_vars = len(var_names)
        # construct formatted_line
        line_has_variables = False
        for i in range(num_vars):
            var_name, value = var_names[i], values[i]
            if var_name != "":
                if var_name.startswith(object_prefix):
                    var_name = var_name[len(object_prefix):]
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

        original_line = self.original_line.lstrip(' ')
        if self.strip_comments:
            original_line = strip_inline_comments(original_line)

        if self.syntax_highlight:
            original_line = highlight(
                original_line,
                lexer=get_lexer_by_name("python"),
                formatter=Terminal256Formatter(style="solarized-dark")
            ).rstrip("\n")

        original_line =  f"{self.print_offset * 2 * ' '}{cf.cyan(f'*  {self.line_number} │  ')}{original_line}"
        # original_line =  f"{cf.cyan(f'*  {self.line_number} │  ')}{self.print_offset * 2 * ' '}{original_line}"
        formatted_line = f"{original_line} {self.formatted_line}"

        print(formatted_line)
        if self.additional_line:
            print(self.additional_line)


    def add_return(self, fxn_name: str, fxn_signature: str, returned_value: Any):
        self.type = "return"
        self.returned_value = returned_value
        self.returned_function = fxn_name
        self.fxn_signature = fxn_signature

    def print_return(self):
        if self.type != "return":
            raise TracingError(f"Cannot print return for line: {self}")
        if self.print_mode == "debug":
            # print(f"{cf.yellow(f'-> {self.returned_function} returned')} {cf.cyan(self.returned_value)}")
            print(f"{cf.yellow(f'{(self.print_offset - 1) * 2 * ' '}-> {self.fxn_signature} returned')} {cf.cyan(self.returned_value)}")

