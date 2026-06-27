"""
A working Lisp interpreter, built around McCarthy's eval/apply.
Based on the work of John McCarthy (Turing Award, 1971).

Usage:
    python implementation.py            # interactive REPL
    python implementation.py --test     # test suite (20 cases)
    python implementation.py --verbose  # show reader, parse tree, and eval steps

Before Lisp (1958): to compute a factorial you wrote a loop in assembly or
    Fortran. Numbers lived in fixed-size memory you managed by hand, recursion
    was not supported, there was no way to treat a program as data, and the
    only values were numbers. Symbolic work, like manipulating an algebraic
    expression, meant encoding it yourself in arrays.

After Lisp: a program is a nested list. McCarthy gave seven primitive
    operators (quote, atom, eq, car, cdr, cons, cond), conditional expressions,
    recursion, lambda, and garbage collection, then wrote eval: a half-page
    function that interprets Lisp, written IN Lisp. Code became data, data
    became code, and the read-eval-print loop was born:

        (define (fact n) (if (= n 0) 1 (* n (fact (- n 1)))))
        (fact 5)   =>   120

This file implements that interpreter: a reader that turns text into lists,
eval/apply that runs them, and at the end McCarthy's own eval expressed in
this dialect and run inside it, an interpreter interpreting an interpreter.
"""

import sys


# ── The reader: text into nested lists (S-expressions) ──────────────────────────
#
# This is the "read" in read-eval-print. McCarthy's insight starts here: program
# source is parsed into the SAME list structure that the program manipulates.

def tokenize(source):
    """Break source text into a flat list of tokens.

    Parentheses become their own tokens. The single quote ' is shorthand for
    (quote ...), so 'x reads as (quote x); we expand it to a token here.
    """
    tokens = []
    spaced = source.replace("(", " ( ").replace(")", " ) ").replace("'", " ' ")
    for piece in spaced.split():
        tokens.append(piece)
    return tokens


def read(tokens):
    """Consume one expression from the front of the token list and return it."""
    if len(tokens) == 0:
        raise SyntaxError("unexpected end of input")

    token = tokens.pop(0)

    if token == "'":
        # 'expr  ->  (quote expr)
        return ["quote", read(tokens)]

    if token == "(":
        expression = []
        while tokens[0] != ")":
            expression.append(read(tokens))
            if len(tokens) == 0:
                raise SyntaxError("missing )")
        tokens.pop(0)            # discard the closing )
        return expression

    if token == ")":
        raise SyntaxError("unexpected )")

    return atom(token)


def atom(token):
    """Turn a single token into a number if it looks like one, else a symbol."""
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token            # a symbol is just its string name


def parse(source):
    """Read one complete expression from a string."""
    return read(tokenize(source))


# ── The environment: where symbols get their meaning ────────────────────────────
#
# An environment maps names to values. Each function call makes a fresh child
# environment whose parent is the environment the function was defined in. That
# parent chain is lexical scoping, which Lisp introduced to mainstream practice.

class Environment:
    def __init__(self, names=(), values=(), parent=None):
        self.vars = {}
        for i in range(len(names)):
            self.vars[names[i]] = values[i]
        self.parent = parent

    def lookup(self, name):
        """Find the value of a name, walking up to enclosing scopes if needed."""
        if name in self.vars:
            return self.vars[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise NameError("unbound symbol: " + str(name))

    def set(self, name, value):
        self.vars[name] = value


# ── A user-defined function (a closure) ─────────────────────────────────────────
#
# A closure is McCarthy's lambda made concrete: the parameter names, the body,
# and the environment of definition, carried together so the function can be
# called later and still see the variables it was born among.

class Closure:
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

    def __call__(self, *args):
        call_env = Environment(self.params, args, self.env)
        return seval(self.body, call_env)


# ── Truthiness ──────────────────────────────────────────────────────────────────
#
# Following McCarthy: the empty list () is nil, which is false. So is the boolean
# false. Everything else, including the number 0, counts as true.

def is_true(value):
    if value is False:
        return False
    if value == []:
        return False
    return True


# ── eval: the heart of Lisp ─────────────────────────────────────────────────────

def seval(expression, env, verbose=False, depth=0):
    """Evaluate one expression in an environment."""
    if verbose:
        print("    " * depth + "eval " + to_str(expression))

    # A symbol evaluates to whatever it is bound to.
    if isinstance(expression, str):
        return env.lookup(expression)

    # A number (or any non-list) evaluates to itself.
    if not isinstance(expression, list):
        return expression

    # The empty list is nil and evaluates to itself.
    if len(expression) == 0:
        return []

    head = expression[0]

    # ── Special forms: these do NOT evaluate all their arguments the normal way.

    if head == "quote":
        # (quote e) -> e, untouched. The bridge from code to data.
        return expression[1]

    if head == "if":
        # (if test then else)
        test = expression[1]
        then_branch = expression[2]
        if is_true(seval(test, env, verbose, depth + 1)):
            return seval(then_branch, env, verbose, depth + 1)
        if len(expression) > 3:
            return seval(expression[3], env, verbose, depth + 1)
        return []

    if head == "cond":
        # (cond (test1 result1) (test2 result2) ...). First true test wins.
        for clause in expression[1:]:
            test = clause[0]
            if is_true(seval(test, env, verbose, depth + 1)):
                return seval(clause[1], env, verbose, depth + 1)
        return []

    if head == "define":
        # (define name value)  or  (define (name params...) body) as sugar.
        target = expression[1]
        if isinstance(target, list):
            name = target[0]
            params = target[1:]
            body = expression[2]
            env.set(name, Closure(params, body, env))
            return name
        else:
            value = seval(expression[2], env, verbose, depth + 1)
            env.set(target, value)
            return target

    if head == "lambda":
        # (lambda (params) body) -> a closure.
        return Closure(expression[1], expression[2], env)

    if head == "let":
        # (let ((a v1) (b v2)) body): bind locals, then evaluate body.
        names = []
        values = []
        for binding in expression[1]:
            names.append(binding[0])
            values.append(seval(binding[1], env, verbose, depth + 1))
        local = Environment(names, values, env)
        return seval(expression[2], local, verbose, depth + 1)

    if head == "begin":
        # (begin e1 e2 ... en): evaluate each, return the last.
        result = []
        for sub in expression[1:]:
            result = seval(sub, env, verbose, depth + 1)
        return result

    if head == "and":
        result = True
        for sub in expression[1:]:
            result = seval(sub, env, verbose, depth + 1)
            if not is_true(result):
                return False
        return result

    if head == "or":
        for sub in expression[1:]:
            result = seval(sub, env, verbose, depth + 1)
            if is_true(result):
                return result
        return False

    # ── Otherwise: a function call. Evaluate operator and every argument, apply.
    proc = seval(head, env, verbose, depth + 1)
    args = []
    for sub in expression[1:]:
        args.append(seval(sub, env, verbose, depth + 1))
    return sapply(proc, args)


def sapply(proc, args):
    """Apply a procedure (a built-in callable or a Closure) to arguments."""
    return proc(*args)


# ── The standard environment: the primitives ────────────────────────────────────

def prim_cons(item, rest):
    """Put item on the front of the list rest."""
    return [item] + rest


def prim_atom(x):
    """True if x is not a (non-empty) list. The empty list is an atom (nil)."""
    if isinstance(x, list) and len(x) > 0:
        return False
    return True


def prim_eq(a, b):
    """True if a and b are the same atom (or both nil)."""
    return a == b


def prim_list(*items):
    result = []
    for item in items:
        result.append(item)
    return result


def prim_add(*nums):
    total = 0
    for n in nums:
        total += n
    return total


def prim_mul(*nums):
    product = 1
    for n in nums:
        product *= n
    return product


def prim_sub(first, *rest):
    if len(rest) == 0:
        return -first
    total = first
    for n in rest:
        total -= n
    return total


def prim_div(first, *rest):
    total = first
    for n in rest:
        total = total / n
    return total


def standard_env():
    env = Environment()
    env.set("car", lambda lst: lst[0])
    env.set("cdr", lambda lst: lst[1:])
    env.set("cons", prim_cons)
    env.set("atom", prim_atom)
    env.set("eq", prim_eq)
    env.set("null?", lambda x: x == [])
    env.set("list", prim_list)
    env.set("not", lambda x: not is_true(x))
    env.set("+", prim_add)
    env.set("-", prim_sub)
    env.set("*", prim_mul)
    env.set("/", prim_div)
    env.set("=", lambda a, b: a == b)
    env.set("<", lambda a, b: a < b)
    env.set(">", lambda a, b: a > b)
    env.set("<=", lambda a, b: a <= b)
    env.set(">=", lambda a, b: a >= b)
    # McCarthy's truth value t, and nil, available as bare symbols.
    env.set("t", True)
    env.set("nil", [])
    env.set("else", True)
    # eval itself, exposed to the language: run a list as a program in the global
    # environment. This is what makes "code is data" literal at the REPL.
    env.set("eval", lambda expr: seval(expr, env))
    return env


# ── Printing values back as Lisp text ───────────────────────────────────────────

def to_str(value):
    """Render a value the way Lisp would print it."""
    if value is True:
        return "t"
    if value is False:
        return "nil"
    if isinstance(value, list):
        parts = []
        for item in value:
            parts.append(to_str(item))
        return "(" + " ".join(parts) + ")"
    if isinstance(value, Closure):
        return "<closure>"
    if callable(value):
        return "<primitive>"
    return str(value)


# ── McCarthy's eval, written in this dialect and run inside this interpreter ─────
#
# This is the famous part of the 1960 paper. eval below is a Lisp program that
# interprets Lisp. When we run it on our Python interpreter, we have an
# interpreter running an interpreter. It covers the seven primitive operators,
# cond, and variable lookup through an association-list environment, which is
# the core McCarthy showed all of computation could be built from. Our host
# interpreter supplies lambda and define on top.

METACIRCULAR = """
(define (null? x) (eq x (quote ())))

(define (assoc key env)
  (cond ((null? env) (quote ()))
        ((eq (car (car env)) key) (car (cdr (car env))))
        (t (assoc key (cdr env)))))

(define (mc-eval e env)
  (cond
    ((atom e) (assoc e env))
    ((eq (car e) (quote quote)) (car (cdr e)))
    ((eq (car e) (quote atom))  (atom (mc-eval (car (cdr e)) env)))
    ((eq (car e) (quote eq))    (eq (mc-eval (car (cdr e)) env)
                                    (mc-eval (car (cdr (cdr e))) env)))
    ((eq (car e) (quote car))   (car (mc-eval (car (cdr e)) env)))
    ((eq (car e) (quote cdr))   (cdr (mc-eval (car (cdr e)) env)))
    ((eq (car e) (quote cons))  (cons (mc-eval (car (cdr e)) env)
                                      (mc-eval (car (cdr (cdr e))) env)))
    ((eq (car e) (quote cond))  (mc-evcon (cdr e) env))
    (t (quote unknown-form))))

(define (mc-evcon clauses env)
  (cond ((mc-eval (car (car clauses)) env)
         (mc-eval (car (cdr (car clauses))) env))
        (t (mc-evcon (cdr clauses) env))))
"""


def load_metacircular(env, verbose=False):
    """Define the metacircular eval inside the given environment."""
    tokens = tokenize(METACIRCULAR)
    while len(tokens) > 0:
        expression = read(tokens)
        seval(expression, env, verbose)


# ── The REPL: the read-eval-print loop, which Lisp invented ─────────────────────

def repl(verbose=False):
    print("Lisp interpreter (John McCarthy, Turing Award 1971)")
    print("Built on eval/apply and the seven primitives: "
          "quote atom eq car cdr cons cond.")
    print("Type an expression. Try:  (define (sq x) (* x x))   then   (sq 9)")
    print("Type  demo  to see a guided tour, or  exit  to quit.\n")

    env = standard_env()
    load_metacircular(env)

    while True:
        try:
            line = input("lisp> ")
        except EOFError:
            print()
            return

        text = line.strip()
        if text == "":
            continue
        if text == "exit" or text == "quit":
            return
        if text == "demo":
            demo(verbose)
            continue

        try:
            expression = parse(text)
            if verbose:
                print("  tokens:", tokenize(text))
                print("  parsed:", expression)
            value = seval(expression, env, verbose)
            print(to_str(value))
        except Exception as error:
            print("error:", error)


# ── Guided demo ──────────────────────────────────────────────────────────────────

def run(env, source, verbose=False):
    """Parse and evaluate one line, print it the way the REPL would."""
    expression = parse(source)
    value = seval(expression, env, verbose)
    print("  " + source)
    print("    => " + to_str(value))
    return value


def demo(verbose=False):
    print("Lisp, the second-oldest language still in use (John McCarthy, 1958)\n")

    env = standard_env()
    load_metacircular(env)

    print("BEFORE Lisp: numbers in fixed memory, loops, no recursion, no")
    print("way to treat a program as data. AFTER Lisp: lists are everything.\n")

    print("1. The seven primitives. Lists are built and taken apart with these.")
    run(env, "(cons 'a (cons 'b '()))", verbose)
    run(env, "(car '(a b c))", verbose)
    run(env, "(cdr '(a b c))", verbose)
    run(env, "(atom 'x)", verbose)
    run(env, "(eq 'a 'a)", verbose)
    print()

    print("2. Conditional expressions: cond, which McCarthy introduced.")
    run(env, "(cond ((eq 1 2) 'no) ((eq 2 2) 'yes) (t 'fallback))", verbose)
    print()

    print("3. Recursion, the thing Fortran could not do in 1958.")
    run(env, "(define (fact n) (if (= n 0) 1 (* n (fact (- n 1)))))", verbose)
    run(env, "(fact 5)", verbose)
    print()

    print("4. Functions are values. Define one that takes another.")
    run(env, "(define (twice f x) (f (f x)))", verbose)
    run(env, "(define (inc n) (+ n 1))", verbose)
    run(env, "(twice inc 10)", verbose)
    print()

    print("5. Code is data. Build a program with cons, then run it.")
    run(env, "(define prog (cons '* (cons 6 (cons 7 '()))))", verbose)
    run(env, "prog", verbose)
    print("    (now evaluate that built-up list as a program)")
    run(env, "(eval prog)", verbose)
    print()

    print("6. The punchline: McCarthy's eval, written in Lisp, run inside our")
    print("   Lisp. An interpreter interpreting an interpreter.")
    run(env, "(mc-eval '(cons (quote a) (cons (quote b) (quote ()))) '())", verbose)
    run(env, "(mc-eval '(car x) '((x (1 2 3))))", verbose)
    run(env, "(mc-eval '(cond ((eq (quote p) (quote q)) (quote first)) "
             "((eq (quote r) (quote r)) (quote second))) '())", verbose)
    print()
    print("Code and data are the same lists. eval is the one function that runs")
    print("the data as code. That equivalence is the foundation McCarthy laid.")


# ── Test suite ────────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print("  PASS  " + name)
            passed += 1
        else:
            print("  FAIL  " + name)
            failed += 1

    env = standard_env()
    load_metacircular(env)

    def ev(source):
        return seval(parse(source), env)

    # 1. The reader turns text into nested lists.
    check("tokenize + parse", parse("(+ 1 2)") == ["+", 1, 2])

    # 2. The reader recognizes integers and floats.
    check("parse numbers", parse("(1 2.5 x)") == [1, 2.5, "x"])

    # 3. Quote shorthand expands to (quote ...).
    check("quote shorthand", parse("'a") == ["quote", "a"])

    # 4. Arithmetic, variadic.
    check("addition", ev("(+ 1 2 3 4)") == 10)

    # 5. Nested arithmetic.
    check("nested arithmetic", ev("(* (+ 1 2) (- 10 6))") == 12)

    # 6. quote returns data unevaluated.
    check("quote returns data", ev("'(a b c)") == ["a", "b", "c"])

    # 7. The seven primitives: car, cdr, cons.
    check("car", ev("(car '(a b c))") == "a")
    check("cdr", ev("(cdr '(a b c))") == ["b", "c"])
    check("cons", ev("(cons 'a '(b c))") == ["a", "b", "c"])

    # 8. atom and eq predicates.
    check("atom of symbol", ev("(atom 'x)") is True)
    check("atom of list", ev("(atom '(a b))") is False)
    check("eq same", ev("(eq 'a 'a)") is True)
    check("eq different", ev("(eq 'a 'b)") is False)

    # 9. if, both branches.
    check("if true branch", ev("(if (eq 1 1) 'yes 'no)") == "yes")
    check("if false branch", ev("(if (eq 1 2) 'yes 'no)") == "no")

    # 10. cond picks the first true clause.
    check("cond", ev("(cond ((eq 1 2) 'a) ((eq 2 2) 'b) (t 'c))") == "b")

    # 11. define and look up a value.
    ev("(define x 42)")
    check("define value", ev("x") == 42)

    # 12. lambda applied directly.
    check("lambda application", ev("((lambda (x) (* x x)) 5)") == 25)

    # 13. define a function and call it.
    ev("(define (square n) (* n n))")
    check("define function", ev("(square 7)") == 49)

    # 14. Recursion: factorial.
    ev("(define (fact n) (if (= n 0) 1 (* n (fact (- n 1)))))")
    check("recursion: factorial", ev("(fact 5)") == 120)

    # 15. Recursion over a list: length.
    ev("(define (len xs) (if (null? xs) 0 (+ 1 (len (cdr xs)))))")
    check("recursion: list length", ev("(len '(a b c d))") == 4)

    # 16. Higher-order function.
    ev("(define (twice f x) (f (f x)))")
    ev("(define (inc n) (+ n 1))")
    check("higher-order function", ev("(twice inc 10)") == 12)

    # 17. Closures capture their defining environment.
    ev("(define (adder n) (lambda (x) (+ x n)))")
    ev("(define add5 (adder 5))")
    check("closure captures environment", ev("(add5 100)") == 105)

    # 18. let introduces local bindings.
    check("let bindings", ev("(let ((a 3) (b 4)) (+ a b))") == 7)

    # 19. and / or short-circuit.
    check("and short-circuits", ev("(and (eq 1 1) (eq 2 2))") is True)
    check("or short-circuits", ev("(or (eq 1 2) 'found)") == "found")

    # 20. Code as data: build a program, then evaluate it with eval.
    ev("(define prog (cons '+ (cons 20 (cons 22 '()))))")
    check("build then eval a program", ev("(eval prog)") == 42)

    # 21. The metacircular eval runs Lisp inside Lisp.
    check("metacircular: build a list",
          ev("(mc-eval '(cons (quote a) (cons (quote b) (quote ()))) '())")
          == ["a", "b"])
    check("metacircular: variable lookup",
          ev("(mc-eval '(cdr x) '((x (1 2 3))))") == [2, 3])
    check("metacircular: cond",
          ev("(mc-eval '(cond ((eq (quote p) (quote q)) (quote first)) "
             "((eq (quote r) (quote r)) (quote second))) '())") == "second")

    # 22. Unbound symbols raise.
    raised = False
    try:
        ev("totally-undefined")
    except NameError:
        raised = True
    check("unbound symbol raises", raised)

    print("\n  " + str(passed) + " passed, " + str(failed) + " failed")
    return failed == 0


# ── Entry point ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    verbose = "--verbose" in sys.argv

    if "--test" in sys.argv:
        print("Running test suite...\n")
        ok = run_tests()
        sys.exit(0 if ok else 1)
    elif "--demo" in sys.argv:
        demo(verbose)
    else:
        # A REPL is hard to use non-interactively, so fall back to the demo when
        # there is no terminal attached (for example in CI or a pipe).
        if sys.stdin.isatty():
            repl(verbose)
        else:
            demo(verbose)
