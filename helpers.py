import inspect
from pprint import pprint


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
