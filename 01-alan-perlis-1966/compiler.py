"""
Mini expression compiler — inspired by Alan Perlis's IT (Internal Translator), 1955-56.

IT was the first practical compiler: it turned algebraic expressions into machine code
automatically. Before IT, programmers wrote every instruction by hand.

This compiler does the same four-stage job IT did:
  1. Tokenize  — break source text into tokens
  2. Parse     — build an Abstract Syntax Tree (AST)
  3. Compile   — emit stack-based bytecode
  4. Execute   — run the bytecode on a tiny virtual stack machine

Supported syntax
----------------
  Numbers          3, 3.14, -2
  Variables        x, total, foo
  Arithmetic       +  -  *  /  ** (power)
  Unary minus      -x
  Grouping         (a + b) * c
  Assignment       x = expr          (stores in variable table)
  Comparisons      ==  !=  <  <=  >  >=   (return 1.0 or 0.0)

Usage
-----
  python compiler.py                 # interactive REPL
  python compiler.py "2 + 3 * 4"    # single expression
"""

import sys
import re
import operator

# ---------------------------------------------------------------------------
# 1. TOKENIZER
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(
    r"""
    \s*                                         # skip whitespace
    (?:
        (?P<NUMBER>  \d+(?:\.\d+)?)             # integer or float
      | (?P<NAME>    [A-Za-z_]\w*)              # identifier
      | (?P<OP2>     ==|!=|<=|>=|\*\*)          # two-char operators
      | (?P<OP1>     [+\-*/()<>=])              # single-char operator
    )
    """,
    re.VERBOSE,
)


def tokenize(text):
    tokens = []
    for m in TOKEN_RE.finditer(text):
        val = m.group(m.lastgroup)
        if m.lastgroup == "NUMBER":
            tokens.append(("NUMBER", float(val)))
        elif m.lastgroup == "NAME":
            tokens.append(("NAME", val))
        else:
            tokens.append(("OP", val))
    return tokens


# ---------------------------------------------------------------------------
# 2. PARSER  (recursive-descent, operator-precedence grammar)
#
# Grammar:
#   program    = assignment | expr
#   assignment = NAME '=' expr
#   expr       = comparison
#   comparison = addition ( ('=='|'!='|'<'|'<='|'>'|'>=') addition )*
#   addition   = term ( ('+'|'-') term )*
#   term       = power ( ('*'|'/') power )*
#   power      = unary ( '**' unary )*      right-associative
#   unary      = '-' unary | primary
#   primary    = NUMBER | NAME | '(' expr ')'
# ---------------------------------------------------------------------------


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # --- helpers ---

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected=None):
        tok = self.tokens[self.pos]
        if expected and tok[1] != expected:
            raise SyntaxError(f"expected '{expected}', got '{tok[1]}'")
        self.pos += 1
        return tok

    def match(self, *values):
        tok = self.peek()
        return tok is not None and tok[1] in values

    # --- grammar rules ---

    def parse(self):
        if not self.tokens:
            raise SyntaxError("empty input")
        # detect assignment: NAME '=' expr (but not '==')
        if (
            len(self.tokens) >= 2
            and self.tokens[0][0] == "NAME"
            and self.tokens[1] == ("OP", "=")
        ):
            return self.assignment()
        node = self.expr()
        if self.pos != len(self.tokens):
            raise SyntaxError(f"unexpected token: {self.peek()}")
        return node

    def assignment(self):
        name = self.consume()[1]
        self.consume("=")
        value = self.expr()
        return ("ASSIGN", name, value)

    def expr(self):
        return self.comparison()

    def comparison(self):
        node = self.addition()
        while self.match("==", "!=", "<", "<=", ">", ">="):
            op = self.consume()[1]
            right = self.addition()
            node = ("BINOP", op, node, right)
        return node

    def addition(self):
        node = self.term()
        while self.match("+", "-"):
            op = self.consume()[1]
            right = self.term()
            node = ("BINOP", op, node, right)
        return node

    def term(self):
        node = self.power()
        while self.match("*", "/"):
            op = self.consume()[1]
            right = self.power()
            node = ("BINOP", op, node, right)
        return node

    def power(self):
        node = self.unary()
        if self.match("**"):
            self.consume("**")
            exp = self.power()  # right-associative recursion
            node = ("BINOP", "**", node, exp)
        return node

    def unary(self):
        if self.match("-"):
            self.consume("-")
            return ("UNARY", "-", self.unary())
        return self.primary()

    def primary(self):
        tok = self.peek()
        if tok is None:
            raise SyntaxError("unexpected end of expression")
        if tok[0] == "NUMBER":
            self.consume()
            return ("NUMBER", tok[1])
        if tok[0] == "NAME":
            self.consume()
            return ("NAME", tok[1])
        if tok[1] == "(":
            self.consume("(")
            node = self.expr()
            self.consume(")")
            return node
        raise SyntaxError(f"unexpected token: {tok}")


# ---------------------------------------------------------------------------
# 3. CODE GENERATOR  →  stack-based bytecode
#
# Instructions
# ------------
#   PUSH  val     push a literal float
#   LOAD  name    push value of variable
#   STORE name    pop top, store in variable
#   ADD           pop two, push sum
#   SUB           pop two, push difference
#   MUL           pop two, push product
#   DIV           pop two, push quotient
#   POW           pop two, push power
#   NEG           pop one, push negation
#   CMP  op       pop two, push 1.0 or 0.0
# ---------------------------------------------------------------------------


def compile_ast(node):
    instructions = []

    def emit(node):
        kind = node[0]
        if kind == "NUMBER":
            instructions.append(("PUSH", node[1]))

        elif kind == "NAME":
            instructions.append(("LOAD", node[1]))

        elif kind == "UNARY":
            emit(node[2])
            instructions.append(("NEG",))

        elif kind == "BINOP":
            op = node[1]
            if op in ("==", "!=", "<", "<=", ">", ">="):
                emit(node[2])
                emit(node[3])
                instructions.append(("CMP", op))
            else:
                emit(node[2])
                emit(node[3])
                opcode = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "**": "POW"}[op]
                instructions.append((opcode,))

        elif kind == "ASSIGN":
            emit(node[2])
            instructions.append(("STORE", node[1]))

        else:
            raise ValueError(f"unknown AST node: {kind}")

    emit(node)
    return instructions


# ---------------------------------------------------------------------------
# 4. VIRTUAL MACHINE
# ---------------------------------------------------------------------------

CMP_OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def execute(instructions, env=None):
    if env is None:
        env = {}
    stack = []

    for instr in instructions:
        op = instr[0]

        if op == "PUSH":
            stack.append(instr[1])
        elif op == "LOAD":
            name = instr[1]
            if name not in env:
                raise NameError(f"undefined variable '{name}'")
            stack.append(env[name])
        elif op == "STORE":
            env[instr[1]] = stack[-1]  # leave value on stack so we can print it
        elif op == "NEG":
            stack.append(-stack.pop())
        elif op == "ADD":
            b, a = stack.pop(), stack.pop()
            stack.append(a + b)
        elif op == "SUB":
            b, a = stack.pop(), stack.pop()
            stack.append(a - b)
        elif op == "MUL":
            b, a = stack.pop(), stack.pop()
            stack.append(a * b)
        elif op == "DIV":
            b, a = stack.pop(), stack.pop()
            if b == 0:
                raise ZeroDivisionError("division by zero")
            stack.append(a / b)
        elif op == "POW":
            b, a = stack.pop(), stack.pop()
            stack.append(a ** b)
        elif op == "CMP":
            b, a = stack.pop(), stack.pop()
            stack.append(1.0 if CMP_OPS[instr[1]](a, b) else 0.0)
        else:
            raise ValueError(f"unknown opcode: {op}")

    return stack[-1] if stack else None, env


# ---------------------------------------------------------------------------
# 5. PRETTY-PRINTERS  (for -v / verbose mode)
# ---------------------------------------------------------------------------


def format_ast(node, indent=0):
    pad = "  " * indent
    kind = node[0]
    if kind == "NUMBER":
        return f"{pad}NUMBER({node[1]})"
    if kind == "NAME":
        return f"{pad}NAME({node[1]})"
    if kind == "UNARY":
        return f"{pad}UNARY({node[1]})\n{format_ast(node[2], indent+1)}"
    if kind == "BINOP":
        return (
            f"{pad}BINOP({node[1]})\n"
            f"{format_ast(node[2], indent+1)}\n"
            f"{format_ast(node[3], indent+1)}"
        )
    if kind == "ASSIGN":
        return f"{pad}ASSIGN({node[1]})\n{format_ast(node[2], indent+1)}"
    return f"{pad}{node}"


def format_bytecode(instructions):
    lines = []
    for i, instr in enumerate(instructions):
        lines.append(f"  {i:3d}  {instr[0]:<6} {' '.join(str(x) for x in instr[1:])}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6. PIPELINE  — tokenize → parse → compile → execute
# ---------------------------------------------------------------------------


def run(source, env=None, verbose=False):
    tokens = tokenize(source)
    ast = Parser(tokens).parse()
    bytecode = compile_ast(ast)

    if verbose:
        print("  Tokens   :", tokens)
        print("  AST:\n" + format_ast(ast))
        print("  Bytecode:\n" + format_bytecode(bytecode))

    result, env = execute(bytecode, env)
    return result, env


# ---------------------------------------------------------------------------
# 7. TEST SUITE
# ---------------------------------------------------------------------------


def run_tests():
    cases = [
        # (source, expected_result, optional env dict)
        ("2 + 3",           5.0,   {}),
        ("10 - 4",          6.0,   {}),
        ("3 * 4",          12.0,   {}),
        ("10 / 4",          2.5,   {}),
        ("2 ** 10",      1024.0,   {}),
        ("2 + 3 * 4",      14.0,   {}),   # precedence
        ("(2 + 3) * 4",    20.0,   {}),   # grouping
        ("-5 + 3",         -2.0,   {}),   # unary minus
        ("2 ** 3 ** 2",   512.0,   {}),   # right-assoc: 2**(3**2) = 2**9
        ("x + 1",          6.0,   {"x": 5.0}),   # variable
        ("y = 42",        42.0,   {}),             # assignment
        ("3 < 5",          1.0,   {}),             # comparison true
        ("5 < 3",          0.0,   {}),             # comparison false
        ("2 + 2 == 4",     1.0,   {}),
    ]

    passed = 0
    failed = 0
    for source, expected, init_env in cases:
        try:
            result, _ = run(source, env=dict(init_env))
            ok = abs(result - expected) < 1e-9
        except Exception as e:
            ok = False
            result = f"ERROR: {e}"
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}]  {source!r:<25}  expected={expected}  got={result}")

    print(f"\n  {passed}/{passed+failed} tests passed")
    return failed == 0


# ---------------------------------------------------------------------------
# 8. ENTRY POINT
# ---------------------------------------------------------------------------


def repl():
    print("Mini IT-style compiler  (type 'quit' to exit, 'test' to run tests)")
    print("  Supports: numbers, variables, +  -  *  /  **  ( )  ==  !=  <  <=  >  >=  =")
    env = {}
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("quit", "exit"):
            break
        if line == "test":
            run_tests()
            continue
        verbose = line.startswith("!")
        if verbose:
            line = line[1:].strip()
        try:
            result, env = run(line, env=env, verbose=verbose)
            if result is not None:
                print(result if result != int(result) else int(result))
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--test" in args or "-t" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    if args:
        source = " ".join(a for a in args if not a.startswith("-"))
        verbose = "-v" in args
        try:
            result, _ = run(source, verbose=verbose)
            print(result if result != int(result) else int(result))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        repl()
