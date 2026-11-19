"""Part A2 — Regular-expression compiler: regex -> NFA (Thompson's construction).

Grammar you must support (see spec.py for the surface syntax):

    union   := concat ('|' concat)*
    concat  := star+
    star    := atom '*'*
    atom    := LITERAL | CLASS | '(' union ')'
    CLASS   := '<letter>' | '<digit>'
    LITERAL := alnum | escaped operator char | space | '_' | '.' etc.

Design guidance:
  - Parse to an AST (or postfix) with correct precedence (* > concat > |).
  - Compile each AST node to an NFA fragment following Sipser's inductive
    construction (§1.3): one start state, one accept state per fragment.
  - Remember: postfix '*' in THIS spec means "one or more" (a+), so
    `a*` compiles as concat(a, closure(a)). Empty matches must be impossible.
"""

from __future__ import annotations

from dataclasses import dataclass

from .automata import NFA
from .automata import EPS

class RegexSyntaxError(ValueError):
    """Raised for malformed regular expressions."""


@dataclass
class _Node:
    """Suggested AST node. You may use your own representation."""

    kind: str  # 'literal' | 'class' | 'union' | 'concat' | 'plus'
    value: str = ""
    children: list["_Node"] | None = None

#Todo A2
def parse(regex: str) -> _Node:
    """Convert a regular expression into an AST."""

    if not isinstance(regex, str) or not regex:
        raise RegexSyntaxError("Empty regex")

    pos = 0

    def expression():
        nonlocal pos

        left = sequence()

        while pos < len(regex) and regex[pos] == "|":
            pos += 1
            right = sequence()
            left = _Node("union", children=[left, right])

        return left

    def sequence():
        nonlocal pos

        nodes = []

        while pos < len(regex) and regex[pos] not in ")|":
            nodes.append(repetition())

        if not nodes:
            raise RegexSyntaxError("Missing expression")

        node = nodes[0]

        for next_node in nodes[1:]:
            node = _Node("concat", children=[node, next_node])

        return node

    def repetition():
        nonlocal pos

        node = atom()

        if pos < len(regex) and regex[pos] == "*":
            pos += 1
            node = _Node("plus", children=[node])

        return node

    def atom():
        nonlocal pos

        if pos >= len(regex):
            raise RegexSyntaxError("Unexpected end of regex")

        char = regex[pos]

        if char == "(":
            pos += 1
            node = expression()

            if pos >= len(regex) or regex[pos] != ")":
                raise RegexSyntaxError("Unbalanced parentheses")

            pos += 1
            return node

        if char == "\\":
            pos += 1

            if pos >= len(regex):
                raise RegexSyntaxError("Invalid escape")

            char = regex[pos]
            pos += 1
            return _Node("literal", value=char)

        if char == "<":
            if regex.startswith("<letter>", pos):
                pos += len("<letter>")
                return _Node("class", value="letter")

            if regex.startswith("<digit>", pos):
                pos += len("<digit>")
                return _Node("class", value="digit")

            # A standalone < can also be a literal operator.
            if ">" in regex[pos + 1:]:
                raise RegexSyntaxError("Unknown shorthand")

        if char in "|)*":
            raise RegexSyntaxError("Unexpected operator")

        pos += 1
        return _Node("literal", value=char)

    result = expression()

    if pos != len(regex):
        raise RegexSyntaxError("Invalid regex")

    return result

#Todo A2
def compile_regex(regex: str) -> NFA:
    """Compile a regex into an NFA using Thompson's construction."""

    tree = parse(regex)
    nfa = NFA()
    next_state = 0

    def new_state():
        nonlocal next_state

        state = next_state
        next_state += 1

        nfa.states.add(state)
        nfa.transitions[state] = {}

        return state

    def add_edge(start, symbol, end):
        if symbol not in nfa.transitions[start]:
            nfa.transitions[start][symbol] = set()

        nfa.transitions[start][symbol].add(end)

        if symbol != EPS:
            nfa.alphabet.add(symbol)

    def build(node):
        if node.kind == "literal":
            start = new_state()
            end = new_state()

            add_edge(start, node.value, end)
            return start, end

        if node.kind == "class":
            start = new_state()
            end = new_state()

            if node.value == "digit":
                chars = "0123456789"
            else:
                chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

            for char in chars:
                add_edge(start, char, end)

            return start, end

        if node.kind == "concat":
            left_start, left_end = build(node.children[0])
            right_start, right_end = build(node.children[1])

            add_edge(left_end, EPS, right_start)

            return left_start, right_end

        if node.kind == "union":
            start = new_state()
            end = new_state()

            left_start, left_end = build(node.children[0])
            right_start, right_end = build(node.children[1])

            add_edge(start, EPS, left_start)
            add_edge(start, EPS, right_start)

            add_edge(left_end, EPS, end)
            add_edge(right_end, EPS, end)

            return start, end

        if node.kind == "plus":
            start = new_state()
            end = new_state()

            inner_start, inner_end = build(node.children[0])

            add_edge(start, EPS, inner_start)
            add_edge(inner_end, EPS, inner_start)
            add_edge(inner_end, EPS, end)

            return start, end

        raise RegexSyntaxError("Unknown AST node")

    start, end = build(tree)

    nfa.start = start
    nfa.accepts = {end}

    return nfa
