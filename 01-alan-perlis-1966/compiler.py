"""
Mini expression compiler — inspired by Alan Perlis's IT (Internal Translator) compiler, 1955-56.

IT was the first successful compiler: it translated algebraic expressions written by humans
into IBM 650 machine code. Perlis's insight was that you could describe a language formally
and mechanically translate it — no hand-assembly required.

This implementation mirrors IT's core pipeline:
    source text → tokens → AST → bytecode → execution

Supported syntax:
    Literals:     42, 3.14
    Variables:    x, result
    Arithmetic:   +  -  *  /  (with correct precedence)
    Unary minus:  -x, -(a + b)
    Grouping:     (expr)
    Assignment:   x = expr
    Multi-stmt:   separated by newlines or semicolons

Example:
    $ python compiler.py
    > x = 3
    > y = x * (2 + 4)
    > y
    18.0
"""

from __future__ import annotations
import re
import sys
from dataclasses import dataclass, field
from typing import Union


# ---------------------------------------------------------------------------
# 1. LEXER  (source text → token stream)
# ---------------------------------------------------------------------------

TT_NUM   = "NUM"
TT_NAME  = "NAME"
TT_PLUS  = "PLUS"
TT_MINUS = "MINUS"
TT_STAR  = "STAR"
TT_SLASH = "SLASH"
TT_EQ    = "EQ"
TT_LPAREN = "LPAREN"
TT_RPAREN = "RPAREN"
TT_EOF   = "EOF"

_TOKEN_RE = re.compile(
    r"\s*(?:"
    r"(?P<NUM>[0-9]+(?:\.[0-9]*)?)    |"
    r"(?P<NAME>[A-Za-z_][A-Za-z0-9_]*)|"
    r"(?P<PLUS>\+)                    |"
    r"(?P<MINUS>-)                    |"
    r"(?P<STAR>\*)                    |"
    r"(?P<SLASH>/)                    |"
    r"(?P<EQ>=)                       |"
    r"(?P<LPAREN>\()                  |"
    r"(?P<RPAREN>\))                   "
    r")\s*",
    re.VERBOSE,
)


@dataclass
class Token:
    type: str
    value: str


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise SyntaxError(f"Unexpected character: {text[pos]!r}")
        pos = m.end()
        kind = m.lastgroup
        tokens.append(Token(kind, m.group(kind)))  # type: ignore[arg-type]
    tokens.append(Token(TT_EOF, ""))
    return tokens


# ---------------------------------------------------------------------------
# 2. PARSER  (token stream → AST)
# ---------------------------------------------------------------------------

@dataclass
class NumNode:
    value: float

@dataclass
class VarNode:
    name: str

@dataclass
class BinOpNode:
    op: str
    left: "ASTNode"
    right: "ASTNode"

@dataclass
class UnaryNode:
    op: str
    operand: "ASTNode"

@dataclass
class AssignNode:
    name: str
    value: "ASTNode"

ASTNode = Union[NumNode, VarNode, BinOpNode, UnaryNode, AssignNode]


class Parser:
    """Recursive-descent parser implementing standard operator precedence.

    Grammar (simplified):
        stmt   → NAME '=' expr  |  expr
        expr   → term  (('+' | '-') term)*
        term   → unary (('*' | '/') unary)*
        unary  → '-' unary  |  primary
        primary→ NUM  |  NAME  |  '(' expr ')'
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, expected: str | None = None) -> Token:
        tok = self.tokens[self.pos]
        if expected and tok.type != expected:
            raise SyntaxError(f"Expected {expected}, got {tok.type!r} ({tok.value!r})")
        self.pos += 1
        return tok

    def parse_stmt(self) -> ASTNode:
        # Look ahead: NAME '=' is an assignment
        if (self.peek().type == TT_NAME
                and self.pos + 1 < len(self.tokens)
                and self.tokens[self.pos + 1].type == TT_EQ):
            name = self.consume(TT_NAME).value
            self.consume(TT_EQ)
            val = self.parse_expr()
            return AssignNode(name, val)
        return self.parse_expr()

    def parse_expr(self) -> ASTNode:
        node = self.parse_term()
        while self.peek().type in (TT_PLUS, TT_MINUS):
            op = self.consume().value
            node = BinOpNode(op, node, self.parse_term())
        return node

    def parse_term(self) -> ASTNode:
        node = self.parse_unary()
        while self.peek().type in (TT_STAR, TT_SLASH):
            op = self.consume().value
            node = BinOpNode(op, node, self.parse_unary())
        return node

    def parse_unary(self) -> ASTNode:
        if self.peek().type == TT_MINUS:
            self.consume()
            return UnaryNode("-", self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> ASTNode:
        tok = self.peek()
        if tok.type == TT_NUM:
            self.consume()
            return NumNode(float(tok.value))
        if tok.type == TT_NAME:
            self.consume()
            return VarNode(tok.value)
        if tok.type == TT_LPAREN:
            self.consume()
            node = self.parse_expr()
            self.consume(TT_RPAREN)
            return node
        raise SyntaxError(f"Unexpected token: {tok.type!r} ({tok.value!r})")


def parse(text: str) -> ASTNode:
    tokens = tokenize(text)
    parser = Parser(tokens)
    node = parser.parse_stmt()
    if parser.peek().type != TT_EOF:
        raise SyntaxError(f"Trailing input: {parser.peek().value!r}")
    return node


# ---------------------------------------------------------------------------
# 3. COMPILER  (AST → stack-based bytecode)
# ---------------------------------------------------------------------------
#
# Instruction set (mirrors what a simple stack machine needs):
#   PUSH_CONST  value   — push a number literal
#   PUSH_VAR    name    — push variable's current value
#   STORE       name    — pop top of stack → variable
#   ADD / SUB / MUL / DIV — pop two, push result
#   NEG                 — negate top of stack

@dataclass
class Instr:
    op: str
    arg: object = None

    def __repr__(self) -> str:
        return f"{self.op}" + (f" {self.arg!r}" if self.arg is not None else "")


def compile_node(node: ASTNode) -> list[Instr]:
    if isinstance(node, NumNode):
        return [Instr("PUSH_CONST", node.value)]

    if isinstance(node, VarNode):
        return [Instr("PUSH_VAR", node.name)]

    if isinstance(node, UnaryNode):
        code = compile_node(node.operand)
        code.append(Instr("NEG"))
        return code

    if isinstance(node, BinOpNode):
        left = compile_node(node.left)
        right = compile_node(node.right)
        op_map = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV"}
        return left + right + [Instr(op_map[node.op])]

    if isinstance(node, AssignNode):
        code = compile_node(node.value)
        code.append(Instr("STORE", node.name))
        return code

    raise TypeError(f"Unknown node type: {type(node)}")


def compile_source(text: str) -> list[Instr]:
    ast = parse(text)
    return compile_node(ast)


# ---------------------------------------------------------------------------
# 4. VIRTUAL MACHINE  (executes bytecode)
# ---------------------------------------------------------------------------

class VM:
    def __init__(self):
        self.vars: dict[str, float] = {}
        self.stack: list[float] = []

    def run(self, instructions: list[Instr]) -> float | None:
        self.stack = []
        for instr in instructions:
            if instr.op == "PUSH_CONST":
                self.stack.append(float(instr.arg))  # type: ignore[arg-type]
            elif instr.op == "PUSH_VAR":
                name = instr.arg
                if name not in self.vars:
                    raise NameError(f"Undefined variable: {name!r}")
                self.stack.append(self.vars[name])
            elif instr.op == "STORE":
                self.vars[instr.arg] = self.stack.pop()  # type: ignore[index]
                return None  # assignment produces no printable result
            elif instr.op == "NEG":
                self.stack.append(-self.stack.pop())
            elif instr.op == "ADD":
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a + b)
            elif instr.op == "SUB":
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a - b)
            elif instr.op == "MUL":
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a * b)
            elif instr.op == "DIV":
                b, a = self.stack.pop(), self.stack.pop()
                if b == 0:
                    raise ZeroDivisionError("Division by zero")
                self.stack.append(a / b)
            else:
                raise RuntimeError(f"Unknown opcode: {instr.op}")

        return self.stack[-1] if self.stack else None


# ---------------------------------------------------------------------------
# 5. REPL  (interactive loop)
# ---------------------------------------------------------------------------

def run_statements(source: str, vm: VM, *, verbose: bool = False) -> float | None:
    """Compile and run one or more semicolon/newline separated statements."""
    result = None
    for stmt in re.split(r"[;\n]+", source):
        stmt = stmt.strip()
        if not stmt:
            continue
        code = compile_source(stmt)
        if verbose:
            print("  bytecode:", "  ".join(str(i) for i in code))
        result = vm.run(code)
    return result


def repl(verbose: bool = False) -> None:
    print("IT-inspired expression compiler  (Perlis, 1955-56 style)")
    print("Type expressions or assignments. Ctrl-D / 'quit' to exit.\n")
    vm = VM()
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.lower() in ("quit", "exit"):
            break
        if not line:
            continue
        try:
            result = run_statements(line, vm, verbose=verbose)
            if result is not None:
                # Print as int when the value is a whole number
                print(int(result) if result == int(result) else result)
        except (SyntaxError, NameError, ZeroDivisionError, RuntimeError) as exc:
            print(f"Error: {exc}")


# ---------------------------------------------------------------------------
# 6. SELF-TEST
# ---------------------------------------------------------------------------

def run_tests() -> None:
    vm = VM()

    def check(src: str, expected: float) -> None:
        result = run_statements(src, vm)
        assert result == expected, f"FAIL: {src!r} → {result!r}, expected {expected!r}"
        print(f"  PASS  {src!r:35s} → {result}")

    print("Running tests...")

    check("2 + 3",          5.0)
    check("10 - 4",         6.0)
    check("3 * 4",         12.0)
    check("8 / 2",          4.0)
    check("2 + 3 * 4",     14.0)   # precedence: * before +
    check("(2 + 3) * 4",   20.0)   # grouping
    check("-5",             -5.0)
    check("-(3 + 2)",       -5.0)
    check("2 * -3",         -6.0)

    # Variable assignment and use
    run_statements("x = 7", vm)
    check("x",              7.0)
    check("x * 2",         14.0)

    # Multi-step: y = x * (2 + 4)  →  7 * 6 = 42
    run_statements("y = x * (2 + 4)", vm)
    check("y",             42.0)

    # Chained expression
    run_statements("a = 3; b = a + 1", vm)
    check("a * b",         12.0)   # 3 * 4

    print("All tests passed.\n")


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    else:
        verbose = "--verbose" in sys.argv or "-v" in sys.argv
        repl(verbose=verbose)
