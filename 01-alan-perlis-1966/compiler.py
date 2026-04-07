"""
Mini expression compiler inspired by Alan Perlis's IT (Internal Translator) compiler (1955-56).

IT was the first successful compiler: it took algebraic expressions and compiled them
to IBM 650 machine code. This implementation mirrors that pipeline:

  source text → tokenizer → parser (AST) → bytecode compiler → stack VM execution

Supported syntax:
  - Integer and float literals
  - Variables (single or multi-char identifiers)
  - Binary operators: + - * / ^ (right-associative exponentiation)
  - Unary negation: -expr
  - Parentheses
  - Assignment: name = expr
  - Multiple statements separated by semicolons or newlines

Example:
  x = 3
  y = x * 2 + 1
  print(y)  # → 7
"""

from __future__ import annotations
import math
import operator
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Iterator


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

class TT(Enum):
    NUM   = auto()
    IDENT = auto()
    PLUS  = auto()
    MINUS = auto()
    STAR  = auto()
    SLASH = auto()
    CARET = auto()
    LPAREN = auto()
    RPAREN = auto()
    EQ    = auto()
    SEMI  = auto()
    EOF   = auto()


@dataclass
class Token:
    type: TT
    value: object = None

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r})"


# ---------------------------------------------------------------------------
# Lexer / Tokenizer
# ---------------------------------------------------------------------------

class LexError(Exception): pass

def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    while i < len(text):
        ch = text[i]

        if ch in ' \t\r\n':
            i += 1
            continue

        if ch == '#':                          # line comment
            while i < len(text) and text[i] != '\n':
                i += 1
            continue

        if ch.isdigit() or (ch == '.' and i + 1 < len(text) and text[i+1].isdigit()):
            j = i
            while j < len(text) and (text[j].isdigit() or text[j] == '.'):
                j += 1
            raw = text[i:j]
            tokens.append(Token(TT.NUM, float(raw) if '.' in raw else int(raw)))
            i = j
            continue

        if ch.isalpha() or ch == '_':
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                j += 1
            tokens.append(Token(TT.IDENT, text[i:j]))
            i = j
            continue

        single = {'+': TT.PLUS, '-': TT.MINUS, '*': TT.STAR, '/': TT.SLASH,
                  '^': TT.CARET, '(': TT.LPAREN, ')': TT.RPAREN,
                  '=': TT.EQ, ';': TT.SEMI}
        if ch in single:
            tokens.append(Token(single[ch]))
            i += 1
            continue

        raise LexError(f"Unexpected character {ch!r} at position {i}")

    tokens.append(Token(TT.EOF))
    return tokens


# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------

@dataclass
class NumNode:
    value: float | int

@dataclass
class VarNode:
    name: str

@dataclass
class BinOpNode:
    op: str
    left: object
    right: object

@dataclass
class UnaryNode:
    op: str
    operand: object

@dataclass
class AssignNode:
    name: str
    expr: object


# ---------------------------------------------------------------------------
# Parser  (recursive-descent, Pratt-style precedence)
# ---------------------------------------------------------------------------

class ParseError(Exception): pass

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, *types: TT) -> Token:
        tok = self.tokens[self.pos]
        if types and tok.type not in types:
            raise ParseError(f"Expected {types}, got {tok}")
        self.pos += 1
        return tok

    def match(self, *types: TT) -> bool:
        return self.tokens[self.pos].type in types

    # --- grammar ---

    def parse_program(self) -> list:
        stmts = []
        while not self.match(TT.EOF):
            stmts.append(self.parse_stmt())
            while self.match(TT.SEMI):
                self.consume()
        return stmts

    def parse_stmt(self):
        # assignment: IDENT = expr
        if self.peek().type == TT.IDENT and self.pos + 1 < len(self.tokens) \
                and self.tokens[self.pos + 1].type == TT.EQ:
            name = self.consume(TT.IDENT).value
            self.consume(TT.EQ)
            expr = self.parse_expr()
            return AssignNode(name, expr)
        return self.parse_expr()

    def parse_expr(self, min_prec: int = 0):
        return self.parse_binary(min_prec)

    # Pratt precedence table: (precedence, right-associative?)
    _PREC = {
        TT.PLUS:  (1, False),
        TT.MINUS: (1, False),
        TT.STAR:  (2, False),
        TT.SLASH: (2, False),
        TT.CARET: (3, True),
    }

    def parse_binary(self, min_prec: int = 0):
        left = self.parse_unary()
        while True:
            tok = self.peek()
            if tok.type not in self._PREC:
                break
            prec, right_assoc = self._PREC[tok.type]
            if prec < min_prec:
                break
            self.consume()
            next_prec = prec if right_assoc else prec + 1
            right = self.parse_binary(next_prec)
            left = BinOpNode(tok.type, left, right)
        return left

    def parse_unary(self):
        if self.match(TT.MINUS):
            self.consume()
            return UnaryNode('-', self.parse_unary())
        return self.parse_primary()

    def parse_primary(self):
        tok = self.peek()
        if tok.type == TT.NUM:
            self.consume()
            return NumNode(tok.value)
        if tok.type == TT.IDENT:
            self.consume()
            return VarNode(tok.value)
        if tok.type == TT.LPAREN:
            self.consume()
            node = self.parse_expr()
            self.consume(TT.RPAREN)
            return node
        raise ParseError(f"Unexpected token {tok}")


# ---------------------------------------------------------------------------
# Bytecode instructions (stack-based virtual machine)
# ---------------------------------------------------------------------------

class Op(Enum):
    PUSH  = auto()   # push literal onto stack
    LOAD  = auto()   # push variable value
    STORE = auto()   # pop → store in variable
    ADD   = auto()
    SUB   = auto()
    MUL   = auto()
    DIV   = auto()
    POW   = auto()
    NEG   = auto()   # unary negate


@dataclass
class Instr:
    op: Op
    arg: object = None

    def __repr__(self):
        return f"{self.op.name:<6} {self.arg!r}" if self.arg is not None else self.op.name


# ---------------------------------------------------------------------------
# Compiler  (AST → bytecode)
# ---------------------------------------------------------------------------

_OP_MAP = {
    TT.PLUS:  Op.ADD,
    TT.MINUS: Op.SUB,
    TT.STAR:  Op.MUL,
    TT.SLASH: Op.DIV,
    TT.CARET: Op.POW,
}

class Compiler:
    def __init__(self):
        self.code: list[Instr] = []

    def compile_node(self, node):
        if isinstance(node, NumNode):
            self.code.append(Instr(Op.PUSH, node.value))

        elif isinstance(node, VarNode):
            self.code.append(Instr(Op.LOAD, node.name))

        elif isinstance(node, BinOpNode):
            self.compile_node(node.left)
            self.compile_node(node.right)
            self.code.append(Instr(_OP_MAP[node.op]))

        elif isinstance(node, UnaryNode):
            self.compile_node(node.operand)
            self.code.append(Instr(Op.NEG))

        elif isinstance(node, AssignNode):
            self.compile_node(node.expr)
            self.code.append(Instr(Op.STORE, node.name))

        else:
            raise ValueError(f"Unknown AST node: {node}")

    def compile(self, stmts: list) -> list[Instr]:
        for stmt in stmts:
            self.compile_node(stmt)
        return self.code


# ---------------------------------------------------------------------------
# Virtual machine  (executes bytecode)
# ---------------------------------------------------------------------------

class VMError(Exception): pass

class VM:
    def __init__(self):
        self.stack: list = []
        self.env: dict[str, float] = {}

    def run(self, code: list[Instr]) -> object:
        last = None
        for instr in code:
            op = instr.op

            if op == Op.PUSH:
                self.stack.append(instr.arg)

            elif op == Op.LOAD:
                if instr.arg not in self.env:
                    raise VMError(f"Undefined variable '{instr.arg}'")
                self.stack.append(self.env[instr.arg])

            elif op == Op.STORE:
                val = self.stack.pop()
                self.env[instr.arg] = val
                last = val

            elif op == Op.NEG:
                self.stack.append(-self.stack.pop())

            else:
                b, a = self.stack.pop(), self.stack.pop()
                if op == Op.ADD: self.stack.append(a + b)
                elif op == Op.SUB: self.stack.append(a - b)
                elif op == Op.MUL: self.stack.append(a * b)
                elif op == Op.DIV:
                    if b == 0: raise VMError("Division by zero")
                    self.stack.append(a / b)
                elif op == Op.POW: self.stack.append(a ** b)

        return self.stack[-1] if self.stack else last


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compile_and_run(source: str, env: dict | None = None) -> tuple[object, dict, list[Instr]]:
    """
    Compile and execute *source*.

    Returns (result, final_environment, bytecode).
    Optionally seed variables via *env*.
    """
    tokens = tokenize(source)
    parser = Parser(tokens)
    stmts  = parser.parse_program()

    compiler = Compiler()
    code = compiler.compile(stmts)

    vm = VM()
    if env:
        vm.env.update(env)
    result = vm.run(code)
    return result, vm.env, code


# ---------------------------------------------------------------------------
# Demo / tests
# ---------------------------------------------------------------------------

def _header(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)


def run_tests():
    cases = [
        # (description, source, expected_result_or_var, expected_value)
        ("Integer arithmetic",        "2 + 3 * 4",          None, 14),
        ("Parentheses override",      "(2 + 3) * 4",        None, 20),
        ("Right-assoc exponent",      "2 ^ 3 ^ 2",          None, 512),  # 2^(3^2) = 2^9
        ("Unary negation",            "-(3 + 4)",            None, -7),
        ("Float division",            "7 / 2",               None, 3.5),
        ("Variable assignment",       "x = 10; x * 2 + 1",  None, 21),
        ("Multi-var program",         "a = 3; b = 4; a^2 + b^2", None, 25),
        ("Chained assignment",        "x = 5; y = x + 1; y * y", None, 36),
        ("Quadratic formula fragment","b = -4; c = 4; b^2 - 4*c", None, 0),
    ]

    passed = failed = 0
    for desc, src, var, expected in cases:
        try:
            result, env, _ = compile_and_run(src)
            actual = env.get(var, result) if var else result
            # Normalize int-valued floats for comparison
            if isinstance(actual, float) and actual == int(actual) and isinstance(expected, int):
                actual = int(actual)
            ok = (actual == expected)
        except Exception as e:
            ok = False
            actual = f"ERROR: {e}"

        status = "PASS" if ok else "FAIL"
        print(f"  [{status}]  {desc}")
        if not ok:
            print(f"         source:   {src!r}")
            print(f"         expected: {expected!r}")
            print(f"         got:      {actual!r}")
            failed += 1
        else:
            passed += 1

    print(f"\n  {passed}/{passed+failed} tests passed")
    return failed == 0


def demo_pipeline():
    _header("PIPELINE TRACE — Perlis IT compiler in miniature")

    source = "result = (3 + 4) * 2 ^ 3 - 1"
    print(f"\n  Source:  {source}\n")

    tokens = tokenize(source)
    print("  Tokens:")
    for tok in tokens[:-1]:
        print(f"    {tok}")

    parser = Parser(tokens)
    stmts  = parser.parse_program()
    print(f"\n  AST:  {stmts[0]}")

    compiler = Compiler()
    code = compiler.compile(stmts)
    print("\n  Bytecode:")
    for i, instr in enumerate(code):
        print(f"    {i:02d}  {instr}")

    result, env, _ = compile_and_run(source)
    print(f"\n  Result:  result = {env['result']}")
    # (3+4)*2^3 - 1 = 7*8 - 1 = 55
    print(f"  Check:   (3+4) * 2^3 - 1 = {(3+4) * 2**3 - 1}")


if __name__ == "__main__":
    _header("TESTS")
    run_tests()
    demo_pipeline()

    _header("INTERACTIVE — try your own expressions")
    print("  Enter expressions (or 'quit' to exit).")
    print("  Variables persist across lines.")
    print("  Examples:  x = 42      x * 2 + 1      2^10\n")
    env: dict = {}
    while True:
        try:
            line = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() in ('quit', 'exit', 'q'):
            break
        if not line:
            continue
        try:
            result, env, code = compile_and_run(line, env)
            print(f"    → {result}")
        except (LexError, ParseError, VMError) as e:
            print(f"    Error: {e}")
