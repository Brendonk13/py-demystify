from typing import Deque, List
from collections import deque

from .line import Line
from ..helpers import print_aligned_lines

class Loop:
    def __init__(self, line, start_line_number):
        # this an index into Function.lines so we can find the line where a loop started
        # self.line = line
        self.line = line
        # on the first iteration of a loop, we mark the line that comes after the loop
        # then we know a loop is complete if the execution flow skips this line (due to failed loop condition)
        self.first_loop_line = -1
        # use this to help check if a loop is complete
        # self.end_idx: Optional[int] = None
        # self.end_idx = -1
        # self.start_line: Optional[Line] = None
        self.have_written_first_iterations = False
        # self.iterations = deque([{"line": line, "start_lines_idx": start_lines_idx}])
        self.iterations: Deque[List[Line]] = deque()
        # self.iterations.append([])
        self.iteration_starts : List[Line] = []
        # self.written_iterations = []
        # need to be able to delete from the front easily
        # but need to make sure we dont delete the first iterations
        # also need to
        # self.debugging_iterations = []
        # self.written_iterations = []
        # need to be able to delete from the front easily
        # but need to make sure we dont delete the first iterations
        # also need to
        self.debugging_iterations = []

        # issue is something is converting from a dict to LIST

        # self.deleted_indices = set()

        # maybe dont need this
        self.start_line_number = start_line_number

    def __repr__(self):
        # return f"Loop(start_line: {self.line.line_number}, first_line={self.first_loop_line} wrote_first_iters={self.have_written_first_iterations})"
        return f"Loop(line: {self.line.original_line.strip()}, start_line: {self.line.line_number}, first_line={self.first_loop_line}, wrote_first_iters={self.have_written_first_iterations})"
    def __str__(self):
        return self.__repr__()

    def print_iterations(self):
        lines = []
        for iteration in self.iterations:
            lines += iteration
        print_aligned_lines(lines)
