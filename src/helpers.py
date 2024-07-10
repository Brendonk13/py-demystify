from pygments import highlight
from pygments.lexers import get_lexer_by_name
import inspect
from pprint import pprint

class TracingError(Exception):
    pass


def get_file_name(frame):
    return frame.f_code.co_filename

def get_fxn_name(frame):
    return frame.f_code.co_name

def get_fxn_signature(frame):
    fxn_name = get_fxn_name(frame)
    fxn_args = inspect.formatargvalues(*inspect.getargvalues(frame))
    return fxn_name + fxn_args

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

def spans_multiple_lines(node):
    return hasattr(node, 'lineno') and hasattr(node, 'end_lineno') and node.lineno != node.end_lineno

# Example usage:
def find_multi_line_everything(source_code):
    tree = ast.parse(source_code)
    for node in ast.walk(tree):
        # if isinstance(node, (ast.For, ast.While)):
        # if isinstance(node, ast.Assign):
            # for target in node.targets:
        # ast.For/While give you lineno, end_lineno for the whole damn loop
        # ast.Dict will tell me multiple line dicts
        # TODO: try with more stuff and change to isinstance(node, (ast.Call, ast.Assign, ... etc)):
        if not isinstance(node, (ast.For, ast.While, ast.FunctionDef, ast.Dict, ast.BoolOp)):
        # if not isinstance(node, (ast.For, ast.While, ast.FunctionDef)):
            if spans_multiple_lines(node):
                print(f"The loop statement '{ast.dump(node)}' spans multiple lines: {node.lineno} -> {node.end_lineno}")
                print()
                # print(get_for_loop_line_numbers(source_code))
                # print(source_code)
                # print("The target '{}' spans multiple lines".format(ast.dump(target)))


def print_all_iterations(lines, loop_stack):
    code = [] + lines
    for loop in loop_stack:
        # code.append
        code += ["Loop(====, ====, ====)"]
        for iteration in loop.iterations:
            code += iteration + ['Iter(====, ====, ====)']
        print_aligned_lines(code)
        code = []
    print("done printing")
    # print_aligned_lines(code)


def print_aligned_lines(lines):
    # output = []
    max_lens = [len(part) for line in lines for part in str(line).split(",")]
    for line in lines:
        if line is None:
            print(line)
            continue
        line = str(line)
        parts = line.split(",")
        s = f"{parts[0].ljust(max_lens[0])}, {parts[1].ljust(max_lens[1])}, {parts[2].ljust(max_lens[2])}"
        print(s)
        # output.append(line.split(",")


def object_copy(instance, init_args=None):
    # https://stackoverflow.com/a/48528831

    if init_args:
        new_obj = instance.__class__(**init_args)
    else:
        new_obj = instance.__class__()
    if hasattr(instance, '__dict__'):
        for k in instance.__dict__ :
            try:
                attr_copy = copy.deepcopy(getattr(instance, k))
            except Exception as e:
                attr_copy = object_copy(getattr(instance, k))
            setattr(new_obj, k, attr_copy)

        new_attrs = list(new_obj.__dict__.keys())
        for k in new_attrs:
            if not hasattr(instance, k):
                delattr(new_obj, k)
        return new_obj
    else:
        return instance


def get_for_loop_line_numbers(source):
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            start_line = node.lineno
            # Finding the end line number
            end_line = find_end_lineno(node)
            return start_line, end_line

def find_end_lineno(node):
    # Traverse the AST recursively to find the last child node's line number
    last_child = node
    while hasattr(last_child, 'body') and last_child.body:
        last_child = last_child.body[-1]
    return last_child.lineno


def strip_inline_comments(replace_query):
    # https://stackoverflow.com/a/65104145
    lexer = get_lexer_by_name("python")
    generator = lex(replace_query, lexer)
    line = []
    lines = []
    for token in generator:
        token_type = token[0]
        token_text = token[1]
        if token_type in ParseToken.Comment:
            continue
        line.append(token_text)
        if token_text == '\n':
            lines.append(''.join(line))
            line = []
    if line:
        line.append('\n')
        lines.append(''.join(line))
    strip_query = "\n".join(lines)
    return strip_query
