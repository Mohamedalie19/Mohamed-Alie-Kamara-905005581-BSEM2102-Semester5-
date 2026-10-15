"""DCOMP320 Data Structures and Algorithm - Stacks Implementation.

Reads mathematical expressions from input.txt, evaluates each one using
a stack-based algorithm, and writes the results to output.txt in the
same layout as the input (separator lines are kept, results replace
the expressions).

Run with:  python main.py
(Optional: python main.py <input_file> <output_file> to use other files.)
"""

import math
import os
import sys

# input.txt and output.txt are looked for in the same folder as this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "input.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "output.txt")


# ---------------------------------------------------------------
# Stack
# ---------------------------------------------------------------

class StackUnderflowError(Exception):
    """Raised when pop() or peek() is used on an empty stack."""


class Stack:
    """A stack (LIFO) built on top of a Python list.

    The END of the list is the TOP of the stack, so push/pop/peek
    only touch the end of the list. That keeps each one O(1).
    """

    def __init__(self):
        self._items = []

    def push(self, item):
        """Put item on top of the stack."""
        self._items.append(item)

    def pop(self):
        """Remove and return the top item."""
        if self.is_empty():
            raise StackUnderflowError("pop from an empty stack")
        return self._items.pop()

    def peek(self):
        """Return the top item WITHOUT removing it."""
        if self.is_empty():
            raise StackUnderflowError("peek at an empty stack")
        return self._items[-1]

    def is_empty(self):
        """Return True if the stack has no items."""
        return len(self._items) == 0

    def size(self):
        """Return how many items are on the stack."""
        return len(self._items)


# ---------------------------------------------------------------
# Expression evaluation (two-stack method)
# ---------------------------------------------------------------

class ExpressionError(Exception):
    """Raised when an expression cannot be evaluated."""


# Higher number = applied first. "(" is only a marker, so it is 0.
PRECEDENCE = {"(": 0, "+": 1, "-": 1, "*": 2, "/": 2, "neg": 3}

# Only plain 0-9 count as digits (str.isdigit() also accepts symbols like "\u00b2")
DIGITS = "0123456789"


def tokenize(expression):
    """Turn text into a list of tokens (numbers as floats, symbols as str)."""
    tokens = []
    i = 0
    while i < len(expression):
        ch = expression[i]
        if ch.isspace():                      # skip spaces
            i += 1
        elif ch in DIGITS or ch == ".":       # read the WHOLE number
            start = i
            while i < len(expression) and (expression[i] in DIGITS or expression[i] == "."):
                i += 1
            text = expression[start:i]
            if text.count(".") > 1 or text == ".":
                raise ExpressionError("Invalid number '" + text + "'")
            tokens.append(float(text))
        elif ch in "+-*/()":
            tokens.append(ch)
            i += 1
        else:
            raise ExpressionError("Invalid character '" + ch + "'")
    return tokens


def apply_one_operator(numbers, operators):
    """Pop one operator and apply it to the top number(s)."""
    op = operators.pop()
    if op == "neg":                           # unary minus: one operand
        numbers.push(-numbers.pop())
        return
    right = numbers.pop()                     # first popped = RIGHT operand
    left = numbers.pop()
    if op == "+":
        numbers.push(left + right)
    elif op == "-":
        numbers.push(left - right)
    elif op == "*":
        numbers.push(left * right)
    elif op == "/":
        if right == 0:
            raise ExpressionError("Division by zero")
        numbers.push(left / right)


def evaluate_expression(expression):
    """Evaluate an arithmetic expression using a number stack and an operator stack."""
    tokens = tokenize(expression)
    numbers = Stack()
    operators = Stack()
    expecting_operand = True    # True at start, after "(" and after an operator

    try:
        for token in tokens:
            if isinstance(token, float):                  # a number
                if not expecting_operand:
                    raise ExpressionError("Malformed expression")
                numbers.push(token)
                expecting_operand = False

            elif token == "(":
                if not expecting_operand:
                    raise ExpressionError("Malformed expression")
                operators.push("(")

            elif token == ")":
                if expecting_operand:
                    raise ExpressionError("Malformed expression")
                while not operators.is_empty() and operators.peek() != "(":
                    apply_one_operator(numbers, operators)
                if operators.is_empty():
                    raise ExpressionError("Mismatched parentheses")
                operators.pop()                           # discard "("
                expecting_operand = False

            elif token == "-" and expecting_operand:      # unary minus
                operators.push("neg")

            else:                                         # binary + - * /
                if expecting_operand:
                    raise ExpressionError("Malformed expression")
                while (not operators.is_empty()
                       and PRECEDENCE[operators.peek()] >= PRECEDENCE[token]):
                    apply_one_operator(numbers, operators)
                operators.push(token)
                expecting_operand = True

        if expecting_operand:                             # e.g. "3 +" or empty
            raise ExpressionError("Malformed expression")
        while not operators.is_empty():
            if operators.peek() == "(":
                raise ExpressionError("Mismatched parentheses")
            apply_one_operator(numbers, operators)
        if numbers.size() != 1:
            raise ExpressionError("Malformed expression")
        result = numbers.pop()
        if not math.isfinite(result):                     # inf or nan
            raise ExpressionError("Number too large")
        return result

    except StackUnderflowError:
        raise ExpressionError("Malformed expression")


# ---------------------------------------------------------------
# File processing
# ---------------------------------------------------------------

def is_separator(line):
    """True if the line is a separator such as -----.

    Rule: at least 3 characters, all identical, and the character is not
    a letter, digit, '.', '(' or ')'. This keeps a lone '-' (a minus sign)
    from being mistaken for a separator.
    """
    if len(line) < 3:
        return False
    ch = line[0]
    if line != ch * len(line):
        return False
    return not (ch.isalnum() or ch in ".()")


def read_input_file(path):
    """Read the input file and return a list of (kind, text) entries.

    kind is "separator" or "expression". Blank lines are skipped.
    The original order is kept so the output can mirror the input.
    """
    entries = []
    with open(path, "r", encoding="utf-8-sig") as file:
        for raw_line in file:
            line = raw_line.strip()
            if line == "":
                continue
            if is_separator(line):
                entries.append(("separator", line))
            else:
                entries.append(("expression", line))
    return entries


def format_result(value):
    """Format a number: 13.0 -> '13', 3.5 -> '3.5'."""
    value = round(value, 10)          # removes floating-point noise
    if value.is_integer():
        return str(int(value))
    return str(value)


def evaluate_entries(entries):
    """Evaluate every expression entry and return the list of output lines."""
    lines = []
    for kind, text in entries:
        if kind == "separator":
            lines.append(text)                    # copy separator exactly
        else:
            try:
                lines.append(format_result(evaluate_expression(text)))
            except ExpressionError as error:
                lines.append("Error: " + str(error))
    return lines


def write_output_file(path, lines):
    """Write each line of output on its own line."""
    with open(path, "w", encoding="utf-8") as file:
        for line in lines:
            file.write(line + "\n")


def main(input_path=INPUT_FILE, output_path=OUTPUT_FILE):
    try:
        entries = read_input_file(input_path)
    except FileNotFoundError:
        print("Error: input file not found: " + input_path)
        return
    except (OSError, UnicodeDecodeError) as error:
        print("Error: could not read input file: " + str(error))
        return

    if not any(kind == "expression" for kind, _ in entries):
        print("Error: input file contains no expressions: " + input_path)
        return

    lines = evaluate_entries(entries)
    write_output_file(output_path, lines)

    # Show expression -> result on screen
    print("Results:")
    for (kind, text), line in zip(entries, lines):
        if kind == "expression":
            print("  " + text + "  =  " + line)
    print("Output written to " + output_path)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        main()