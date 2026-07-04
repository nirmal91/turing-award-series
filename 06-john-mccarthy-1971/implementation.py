"""
A working Lisp, built the way John McCarthy defined it in 1960.

McCarthy's "Recursive Functions of Symbolic Expressions and Their Computation by
Machine" (Communications of the ACM, 1960) did something no language had done: it
defined the language in itself. He wrote eval, a function that takes a program
written as a list and computes its value. Because code and data are both just
S-expressions (nested lists of symbols), eval is only about a page long, and yet
it is a complete interpreter.

This file is that idea, made runnable. It has a reader (text -> S-expressions),
an evaluator (eval / apply), lexical environments with real closures, recursion,
and a handful of built-in operators. It mirrors the 1960 paper rather than
simulating it: the seven primitives (quote, atom, eq, car, cdr, cons, cond),
lambda, and label (recursion) are all here and everything else is built on top.

BEFORE Lisp: to compute factorial you wrote a fixed sequence of machine
instructions over fixed memory cells. A program could not build another program,
recursion was exotic, and there was no way to hand code around as data.

AFTER Lisp, the same idea is data you can read, run, and pass around:
    (label fact (lambda (n)
        (cond ((eq n 0) 1)
              (t (* n (fact (- n 1)))))))

Pipeline:
    source text
        -> tokenize   (split into ( ) and atoms)
        -> parse      (build nested Python lists = S-expressions)
        -> eval       (walk the S-expression against an environment)
        -> apply      (bind arguments, evaluate the body)
        -> value

Run:
    python3 implementation.py            # interactive REPL
    python3 implementation.py --test     # self-test suite (16 cases)
    python3 implementation.py --verbose  # REPL that prints every eval step
"""

import sys


# ── Reader: text -> S-expressions ────────────────────────────────────────────────
#
# An S-expression is either an atom or a list of S-expressions. In this
# implementation an atom is a Python int, float, or str, and a list is a Python
# list. The reader turns "(cons 1 (quote (2 3)))" into ['cons', 1, ['quote', [2, 3]]].

class Symbol(str):
    """A Lisp symbol. A subclass of str so it prints plainly, but distinct from
    Lisp strings would be (we have no string literals, so every str is a symbol)."""


def tokenize(text):
    """Split source text into a flat list of tokens: '(', ')', and atoms."""
    # Pad the parentheses with spaces so a plain split separates them from atoms.
    spaced = text.replace("(", " ( ").replace(")", " ) ")
    return spaced.split()


def parse(tokens):
    """Turn a token list into one S-expression. Returns (expr, remaining_tokens)."""
    if len(tokens) == 0:
        raise SyntaxError("unexpected end of input")

    token = tokens[0]
    rest = tokens[1:]

    if token == "(":
        # Read expressions until the matching close paren.
        items = []
        while rest[0] != ")":
            item, rest = parse(rest)
            items.append(item)
            if len(rest) == 0:
                raise SyntaxError("missing )")
        return items, rest[1:]          # drop the closing ")"

    if token == ")":
        raise SyntaxError("unexpected )")

    return atom(token), rest


def atom(token):
    """Classify a single token as an int, a float, or a symbol."""
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return Symbol(token)


def read(text):
    """Parse the first complete S-expression out of text."""
    expr, _ = parse(tokenize(text))
    return expr


# ── Environment: names -> values, with lexical scoping ───────────────────────────
#
# An environment is a dict of bindings plus a pointer to the enclosing one. Looking
# up a name walks outward until it finds a binding. This chain is what makes
# closures work: a lambda remembers the environment it was created in.

class Env:
    def __init__(self, bindings=None, parent=None):
        self.bindings = bindings if bindings is not None else {}
        self.parent = parent

    def lookup(self, name):
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise NameError("unbound symbol: " + name)

    def define(self, name, value):
        self.bindings[name] = value


class Procedure:
    """A lambda: its parameter names, its body, and the environment it closed over."""
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env


# ── The evaluator: eval and apply ────────────────────────────────────────────────
#
# This is McCarthy's eval. Given an expression and an environment, it returns a
# value. quote, cond, if, lambda, define, and label are special forms (they decide
# for themselves whether to evaluate their arguments). Everything else is a
# function application: evaluate the operator and the arguments, then apply.

VERBOSE = False


def seval(x, env, depth=0):
    if VERBOSE:
        print("  " * depth + "eval: " + to_str(x))
    result = _seval(x, env, depth)
    if VERBOSE:
        print("  " * depth + "  => " + to_str(result))
    return result


def _seval(x, env, depth):
    # A symbol names a value. Look it up.
    if isinstance(x, Symbol):
        return env.lookup(x)

    # Numbers evaluate to themselves.
    if not isinstance(x, list):
        return x

    if len(x) == 0:
        return []                       # the empty list, Lisp's nil

    op = x[0]

    if op == "quote":                   # (quote X) -> X, unevaluated
        return x[1]

    if op == "cond":                    # (cond (test expr) (test expr) ...)
        for clause in x[1:]:
            test = seval(clause[0], env, depth + 1)
            if not is_false(test):
                return seval(clause[1], env, depth + 1)
        return []

    if op == "if":                      # (if test then else) — sugar over cond
        test = seval(x[1], env, depth + 1)
        if not is_false(test):
            return seval(x[2], env, depth + 1)
        if len(x) > 3:
            return seval(x[3], env, depth + 1)
        return []

    if op == "lambda":                  # (lambda (params) body) -> a closure
        return Procedure(x[1], x[2], env)

    if op == "define":                  # (define name expr) — bind in this env
        value = seval(x[2], env, depth + 1)
        env.define(x[1], value)
        return x[1]

    if op == "label":                   # (label name (lambda ...)) — self-reference
        # McCarthy's way to write a recursive function before define existed.
        # Bind the name to the closure inside its own environment so the body can
        # call itself.
        local = Env(parent=env)
        proc = seval(x[2], local, depth + 1)
        local.define(x[1], proc)
        return proc

    # Otherwise: application. Evaluate the operator, evaluate every argument,
    # then apply.
    proc = seval(op, env, depth + 1)
    args = []
    for arg in x[1:]:
        args.append(seval(arg, env, depth + 1))
    return apply_(proc, args, depth)


def apply_(proc, args, depth=0):
    # A built-in is a plain Python function.
    if callable(proc) and not isinstance(proc, Procedure):
        return proc(*args)

    # A Lisp lambda: bind parameters to arguments in a fresh child environment,
    # then evaluate the body there.
    if isinstance(proc, Procedure):
        if len(args) != len(proc.params):
            raise TypeError("expected %d args, got %d" % (len(proc.params), len(args)))
        local = Env(parent=proc.env)
        for i in range(len(proc.params)):
            local.define(proc.params[i], args[i])
        return seval(proc.body, local, depth + 1)

    raise TypeError("not a function: " + to_str(proc))


# ── Truth, printing, and the built-in operators ─────────────────────────────────

def is_false(x):
    """Lisp is false only for the symbol f and the empty list; everything else true."""
    if x == Symbol("f"):
        return True
    if isinstance(x, list) and len(x) == 0:
        return True
    return False


def lisp_bool(python_bool):
    return Symbol("t") if python_bool else Symbol("f")


def to_str(x):
    """Render a value as Lisp source: atoms plain, lists parenthesized."""
    if isinstance(x, Procedure):
        return "(lambda " + to_str(x.params) + " ...)"
    if callable(x):
        return "<builtin>"
    if isinstance(x, list):
        return "(" + " ".join(to_str(item) for item in x) + ")"
    return str(x)


def global_env():
    """The starting environment: the seven primitives plus arithmetic."""
    env = Env()

    # The classic list primitives.
    env.define(Symbol("car"), lambda a: a[0])
    env.define(Symbol("cdr"), lambda a: a[1:])
    env.define(Symbol("cons"), lambda a, b: [a] + b)
    env.define(Symbol("atom"), lambda a: lisp_bool(not isinstance(a, list)))
    env.define(Symbol("eq"), lambda a, b: lisp_bool(a == b))
    env.define(Symbol("null"), lambda a: lisp_bool(isinstance(a, list) and len(a) == 0))

    # Arithmetic and comparison, so the examples can do real work.
    env.define(Symbol("+"), lambda a, b: a + b)
    env.define(Symbol("-"), lambda a, b: a - b)
    env.define(Symbol("*"), lambda a, b: a * b)
    env.define(Symbol("="), lambda a, b: lisp_bool(a == b))
    env.define(Symbol("<"), lambda a, b: lisp_bool(a < b))

    # Two named constants.
    env.define(Symbol("t"), Symbol("t"))
    env.define(Symbol("nil"), [])
    return env


def run(text, env):
    """Read one expression from text and evaluate it in env."""
    return seval(read(text), env)


# ── REPL ─────────────────────────────────────────────────────────────────────────

BANNER = """A Lisp interpreter (John McCarthy, 1960).
Try:
  (cons (quote a) (quote (b c)))
  (define square (lambda (n) (* n n)))
  (square 9)
  (define fact (lambda (n) (cond ((eq n 0) 1) (t (* n (fact (- n 1)))))))
  (fact 5)
Type an S-expression, or Ctrl-D to quit."""


def repl():
    env = global_env()
    print(BANNER)
    while True:
        try:
            line = input("lisp> ")
        except EOFError:
            print()
            return
        if line.strip() == "":
            continue
        try:
            value = run(line, env)
            print(to_str(value))
        except (SyntaxError, NameError, TypeError, IndexError, ZeroDivisionError) as err:
            print("error: " + str(err))


# ── Self-test suite ──────────────────────────────────────────────────────────────

def run_tests():
    cases = [
        # (source, expected_as_lisp_string, description)
        ("(quote a)", "a", "quote returns its argument unevaluated"),
        ("(quote (a b c))", "(a b c)", "quote a list"),
        ("(car (quote (a b c)))", "a", "car takes the first element"),
        ("(cdr (quote (a b c)))", "(b c)", "cdr takes the rest"),
        ("(cons (quote a) (quote (b c)))", "(a b c)", "cons prepends"),
        ("(atom (quote a))", "t", "an atom is an atom"),
        ("(atom (quote (a b)))", "f", "a list is not an atom"),
        ("(eq (quote a) (quote a))", "t", "eq of equal atoms is t"),
        ("(eq (quote a) (quote b))", "f", "eq of different atoms is f"),
        ("(cond ((eq 1 2) (quote no)) (t (quote yes)))", "yes", "cond picks the true branch"),
        ("(if (eq 1 1) (quote same) (quote diff))", "same", "if on a true test"),
        ("(+ 2 (* 3 4))", "14", "nested arithmetic"),
        ("((lambda (x) (* x x)) 6)", "36", "apply a lambda literal"),
        # A closure: adder captures y, so (adder 10) returns a function that adds 10.
        ("(((lambda (y) (lambda (x) (+ x y))) 10) 5)", "15", "closures capture their environment"),
        # Recursion via label, McCarthy's original mechanism (no define needed).
        ("((label fact (lambda (n) (cond ((eq n 0) 1) (t (* n (fact (- n 1))))))) 5)",
         "120", "recursion with label: 5! = 120"),
        # A list-processing recursion: length of a list.
        ("((label len (lambda (xs) (cond ((null xs) 0) (t (+ 1 (len (cdr xs)))))))"
         " (quote (a b c d)))", "4", "recursive length of (a b c d)"),
    ]

    passed = 0
    for source, expected, description in cases:
        env = global_env()
        try:
            got = to_str(run(source, env))
        except Exception as err:            # noqa: BLE001 — tests report any failure
            got = "error: " + str(err)
        ok = got == expected
        if ok:
            passed += 1
        mark = "PASS" if ok else "FAIL"
        print("[%s] %-45s -> %s" % (mark, source if len(source) <= 45 else source[:42] + "...", got))
        if not ok:
            print("        expected %s (%s)" % (expected, description))

    # A stateful check: define persists across expressions in one environment.
    env = global_env()
    run("(define double (lambda (n) (+ n n)))", env)
    got = to_str(run("(double 21)", env))
    ok = got == "42"
    passed += 1 if ok else 0
    print("[%s] define persists across expressions      -> %s" % ("PASS" if ok else "FAIL", got))

    total = len(cases) + 1
    print()
    print("%d/%d passed" % (passed, total))
    return passed == total


# ── Entry point ──────────────────────────────────────────────────────────────────

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
        print("(verbose mode: every eval step is printed)\n")
    repl()


if __name__ == "__main__":
    main()
