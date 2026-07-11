"""
Lisp — a working interpreter for McCarthy's language
Based on the work of John McCarthy (Turing Award, 1971).

Usage:
    python implementation.py            # guided demo, then a REPL if interactive
    python implementation.py --test     # test suite (24 cases)
    python implementation.py --verbose  # show tokens, parse tree, and results

Before McCarthy (late 1950s): a program was a sequence of machine operations on
    numbers in fixed memory cells. FORTRAN, the state of the art, had no
    recursion and no way to treat a program as data. To compute a factorial you
    wrote a loop and mutated a counter, because a function could not call
    itself. Code and data lived in separate worlds.

After McCarthy (Lisp, 1960): programs are symbolic expressions (lists), and so
    is data, so a program can build and run another program. Functions are
    values you can pass around. Recursion is the natural way to compute. The
    whole language is defined by one function, eval, that you can even write IN
    the language (see the metacircular evaluator demo below). McCarthy also
    invented the conditional expression, the if/else in every language since,
    and garbage collection, so programs stopped hand-managing memory.

        FORTRAN-era factorial              Lisp factorial
        (loop, mutate a cell)              (a function that calls itself)
        ------------------------           -----------------------------
        FACT = 1                           (define (fact n)
        DO 10 I = 1, N                       (if (= n 0)
        FACT = FACT * I                          1
        10 CONTINUE                              (* n (fact (- n 1)))))

This file is a real interpreter: text -> tokens -> parse tree -> eval -> value.
It mirrors the 1960 paper, right down to running McCarthy's eval written in
Lisp on top of this eval written in Python.
"""

import sys


# The one flag the whole file reads. Set from the command line in main().
VERBOSE = False


# ── Values ──────────────────────────────────────────────────────────────────────
#
# Lisp has very few kinds of value. We reuse Python's:
#   symbol      -> Symbol (a str subclass, so we can tell names from... nothing
#                  else, since this Lisp has no string literals, only symbols)
#   number      -> int or float
#   boolean     -> Python True / False, printed as #t / #f
#   list / nil  -> Python list; the empty list [] is nil, Lisp's "nothing"
#   procedure   -> Procedure (a closure) or a Python callable (a primitive)


class Symbol(str):
    """A Lisp name. A subclass of str so it hashes and compares like its text,
    but stays distinguishable as 'a symbol' in the code below."""


class Procedure:
    """A closure: parameters, a body, and the environment it was defined in.

    The captured environment is what makes lexical scope and recursion work. A
    function remembers the world it was born into, so when it calls itself by
    name that name is still in reach."""

    def __init__(self, params, body, env, name="lambda"):
        self.params = params
        self.body = body            # a list of body expressions, run in order
        self.env = env
        self.name = name

    def __repr__(self):
        return "#<procedure {} ({})>".format(self.name, " ".join(self.params))


# ── Reader: text -> tokens -> parse tree ─────────────────────────────────────────
#
# McCarthy's key move was that a program has the same shape as data: a list.
# So "reading" a program is just parsing nested parentheses into nested lists.


def tokenize(text):
    """Split source text into tokens. Parentheses become their own tokens; a
    quote mark ' becomes a token so 'x can be sugar for (quote x)."""
    out = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == ";":                       # comment: skip to end of line
            while i < len(text) and text[i] != "\n":
                i += 1
        elif c in "()":
            out.append(c)
            i += 1
        elif c == "'":
            out.append("'")
            i += 1
        elif c.isspace():
            i += 1
        else:                              # an atom: read until whitespace/paren
            start = i
            while i < len(text) and not text[i].isspace() and text[i] not in "()';":
                i += 1
            out.append(text[start:i])
    return out


def read_from_tokens(tokens):
    """Consume one whole expression from the front of the token list and return
    it as a nested Python list. Mutates tokens (pops from the front)."""
    if not tokens:
        raise SyntaxError("unexpected end of input")

    token = tokens.pop(0)

    if token == "'":
        # 'expr  ==  (quote expr)
        return [Symbol("quote"), read_from_tokens(tokens)]

    if token == "(":
        lst = []
        while tokens[0] != ")":
            lst.append(read_from_tokens(tokens))
            if not tokens:
                raise SyntaxError("missing )")
        tokens.pop(0)                      # drop the closing )
        return lst

    if token == ")":
        raise SyntaxError("unexpected )")

    return atomize(token)


def atomize(token):
    """Turn a single text token into a value: a number if it looks like one, the
    booleans #t / #f, otherwise a Symbol."""
    if token == "#t":
        return True
    if token == "#f":
        return False
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return Symbol(token)


def read_all(text):
    """Parse every top-level expression in the text into a list of parse trees."""
    tokens = tokenize(text)
    forms = []
    while tokens:
        forms.append(read_from_tokens(tokens))
    return forms


# ── Environment ──────────────────────────────────────────────────────────────────
#
# An environment maps names to values. It has a parent (an outer scope). Looking
# up a name walks outward until it is found. This chain is lexical scope.


class Environment:
    def __init__(self, params=(), args=(), parent=None):
        self.vars = dict(zip(params, args))
        self.parent = parent

    def find(self, name):
        """Return the environment where name is bound, searching outward."""
        if name in self.vars:
            return self
        if self.parent is not None:
            return self.parent.find(name)
        raise NameError("unbound symbol: " + name)

    def get(self, name):
        return self.find(name).vars[name]

    def set(self, name, value):
        self.vars[name] = value


# ── eval: the heart of the language (McCarthy, 1960) ─────────────────────────────
#
# Everything the interpreter does funnels through here. eval takes an expression
# and an environment and returns a value. Special forms (quote, if, cond, define,
# lambda, let, begin, and, or) are handled directly; anything else is a function
# call: evaluate the head to get a procedure, evaluate the arguments, apply.


def lisp_eval(expr, env, depth=0):
    if VERBOSE:
        print("  " * depth + "eval: " + write(expr))

    # A symbol: look up its value.
    if isinstance(expr, Symbol):
        return env.get(expr)

    # Numbers, booleans, and nil evaluate to themselves.
    if not isinstance(expr, list):
        return expr
    if expr == []:
        return []

    head = expr[0]

    # ---- special forms ----
    if isinstance(head, Symbol):
        if head == "quote":                        # (quote x) -> x, unevaluated
            return expr[1]

        if head == "if":                           # (if test then else)
            test = lisp_eval(expr[1], env, depth + 1)
            if is_true(test):
                return lisp_eval(expr[2], env, depth + 1)
            if len(expr) > 3:
                return lisp_eval(expr[3], env, depth + 1)
            return []

        if head == "cond":                         # (cond (test body...) ...)
            for clause in expr[1:]:
                test = clause[0]
                # 'else' (or #t) is the catch-all last clause.
                if test == Symbol("else") or is_true(lisp_eval(test, env, depth + 1)):
                    return eval_sequence(clause[1:], env, depth + 1)
            return []

        if head == "define":                       # (define name val)
            return do_define(expr, env, depth)     # or (define (f a b) body...)

        if head == "set!":                         # (set! name val)
            value = lisp_eval(expr[2], env, depth + 1)
            env.find(expr[1]).set(expr[1], value)
            return value

        if head == "lambda":                       # (lambda (params...) body...)
            return Procedure(expr[1], expr[2:], env)

        if head == "let":                          # (let ((v e) ...) body...)
            names = [pair[0] for pair in expr[1]]
            values = [lisp_eval(pair[1], env, depth + 1) for pair in expr[1]]
            inner = Environment(names, values, parent=env)
            return eval_sequence(expr[2:], inner, depth + 1)

        if head == "begin":                        # (begin e1 e2 ... en) -> en
            return eval_sequence(expr[1:], env, depth + 1)

        if head == "and":                          # short-circuit AND
            result = True
            for sub in expr[1:]:
                result = lisp_eval(sub, env, depth + 1)
                if not is_true(result):
                    return False
            return result

        if head == "or":                           # short-circuit OR
            for sub in expr[1:]:
                result = lisp_eval(sub, env, depth + 1)
                if is_true(result):
                    return result
            return False

    # ---- a function call ----
    proc = lisp_eval(head, env, depth + 1)
    args = [lisp_eval(arg, env, depth + 1) for arg in expr[1:]]
    return lisp_apply(proc, args, depth)


def do_define(expr, env, depth):
    """Handle both (define name value) and the (define (f args) body...) sugar."""
    target = expr[1]
    if isinstance(target, list):
        # (define (f a b) body...) == (define f (lambda (a b) body...))
        name = target[0]
        params = target[1:]
        proc = Procedure(params, expr[2:], env, name=name)
        env.set(name, proc)
    else:
        name = target
        value = lisp_eval(expr[2], env, depth + 1)
        if isinstance(value, Procedure):
            value.name = name
        env.set(name, value)
    return Symbol(name)


def eval_sequence(exprs, env, depth):
    """Evaluate expressions in order, return the value of the last one."""
    result = []
    for e in exprs:
        result = lisp_eval(e, env, depth)
    return result


def lisp_apply(proc, args, depth=0):
    """Call a procedure on already-evaluated arguments."""
    if VERBOSE:
        print("  " * depth + "apply: " + write(proc) + " to " + write(args))

    # A primitive is a plain Python function.
    if callable(proc) and not isinstance(proc, Procedure):
        return proc(*args)

    if isinstance(proc, Procedure):
        if len(args) != len(proc.params):
            raise TypeError("{} wanted {} args, got {}".format(
                proc.name, len(proc.params), len(args)))
        # New scope: bind params to args, chained to where the proc was defined.
        # That chaining is why a recursive function can still see its own name.
        inner = Environment(proc.params, args, parent=proc.env)
        return eval_sequence(proc.body, inner, depth + 1)

    raise TypeError("not a procedure: " + write(proc))


def is_true(x):
    """Lisp truth: only #f and nil (the empty list) are false. Following
    McCarthy's convention that an empty result means 'no'."""
    return x is not False and x != []


# ── Primitives: the built-in functions eval calls out to ─────────────────────────


def prim_add(*a):
    total = 0
    for x in a:
        total += x
    return total


def prim_sub(*a):
    if len(a) == 1:
        return -a[0]
    result = a[0]
    for x in a[1:]:
        result -= x
    return result


def prim_mul(*a):
    result = 1
    for x in a:
        result *= x
    return result


def prim_div(*a):
    result = a[0]
    for x in a[1:]:
        result /= x
    return result


def prim_cons(x, lst):
    if not isinstance(lst, list):
        raise TypeError("cons expects a list as its second argument")
    return [x] + lst


def prim_car(lst):
    if not isinstance(lst, list) or lst == []:
        raise TypeError("car of a non-list or empty list")
    return lst[0]


def prim_cdr(lst):
    if not isinstance(lst, list) or lst == []:
        raise TypeError("cdr of a non-list or empty list")
    return lst[1:]


def prim_eq(a, b):
    """eq?: same atom. Numbers, symbols, booleans, and nil compare by value;
    two non-empty lists are never eq? (they are different cells)."""
    if isinstance(a, list) or isinstance(b, list):
        return a == [] and b == []
    return a == b and type(a) == type(b)


def prim_atom(x):
    """atom?: true for anything that is not a non-empty list. Nil is an atom,
    exactly as in the 1960 paper."""
    return not isinstance(x, list) or x == []


def prim_list_pred(x):
    return isinstance(x, list)


def prim_append(*lists):
    out = []
    for lst in lists:
        out = out + lst
    return out


def prim_map(proc, *lists):
    out = []
    for group in zip(*lists):
        out.append(lisp_apply(proc, list(group)))
    return out


def compare(op):
    """Build a chained comparison primitive: (< 1 2 3) is true."""
    def f(*a):
        for i in range(len(a) - 1):
            if not op(a[i], a[i + 1]):
                return False
        return True
    return f


def make_global_env():
    env = Environment()
    env.vars.update({
        Symbol("+"): prim_add,
        Symbol("-"): prim_sub,
        Symbol("*"): prim_mul,
        Symbol("/"): prim_div,
        Symbol("="): compare(lambda x, y: x == y),
        Symbol("<"): compare(lambda x, y: x < y),
        Symbol(">"): compare(lambda x, y: x > y),
        Symbol("<="): compare(lambda x, y: x <= y),
        Symbol(">="): compare(lambda x, y: x >= y),
        Symbol("cons"): prim_cons,
        Symbol("car"): prim_car,
        Symbol("cdr"): prim_cdr,
        Symbol("list"): lambda *a: list(a),
        Symbol("append"): prim_append,
        Symbol("map"): prim_map,
        Symbol("length"): lambda lst: len(lst),
        Symbol("reverse"): lambda lst: list(reversed(lst)),
        Symbol("eq?"): prim_eq,
        Symbol("equal?"): lambda a, b: a == b,
        Symbol("atom?"): prim_atom,
        Symbol("null?"): lambda x: x == [],
        Symbol("pair?"): lambda x: isinstance(x, list) and x != [],
        Symbol("list?"): prim_list_pred,
        Symbol("not"): lambda x: not is_true(x),
        Symbol("zero?"): lambda x: x == 0,
        Symbol("add1"): lambda x: x + 1,
        Symbol("sub1"): lambda x: x - 1,
        Symbol("nil"): [],
    })
    return env


# ── Printer: value -> text ───────────────────────────────────────────────────────


def write(value):
    """Render a value the way Lisp prints it."""
    if value is True:
        return "#t"
    if value is False:
        return "#f"
    if isinstance(value, list):
        return "(" + " ".join(write(v) for v in value) + ")"
    if callable(value) and not isinstance(value, Procedure):
        return "#<primitive " + getattr(value, "__name__", "fn") + ">"
    return str(value)


# ── A small standard library, and McCarthy's own eval written in Lisp ────────────
#
# The block below is Lisp source. The last definition, mc-eval, is McCarthy's
# 1960 evaluator transcribed into this dialect. Running it means our Python eval
# is interpreting a Lisp program that is itself a Lisp interpreter. That is the
# metacircular evaluator, the paper's punchline and the reason Lisp is special.

PRELUDE = """
(define (caar x) (car (car x)))
(define (cadr x) (car (cdr x)))
(define (caddr x) (car (cdr (cdr x))))
(define (cdar x) (cdr (car x)))

; pair up a list of keys with a list of values into an association list
(define (pairlis keys vals env)
  (cond ((null? keys) env)
        (else (cons (cons (car keys) (car vals))
                    (pairlis (cdr keys) (cdr vals) env)))))

; look a key up in an association list
(define (assoc k env)
  (cond ((eq? (caar env) k) (cdar env))
        (else (assoc k (cdr env)))))

; evaluate the arguments of a call, left to right
(define (evlis args env)
  (cond ((null? args) (quote ()))
        (else (cons (mc-eval (car args) env)
                    (evlis (cdr args) env)))))

; walk cond clauses, evaluate the body of the first true one
(define (evcon clauses env)
  (cond ((mc-eval (caar clauses) env) (mc-eval (cadr (car clauses)) env))
        (else (evcon (cdr clauses) env))))

; McCarthy's eval: the pure symbolic Lisp of 1960, defined in Lisp itself.
(define (mc-eval e env)
  (cond
    ((atom? e) (assoc e env))
    ((atom? (car e))
     (cond
       ((eq? (car e) (quote quote)) (cadr e))
       ((eq? (car e) (quote atom))  (atom? (mc-eval (cadr e) env)))
       ((eq? (car e) (quote eq))    (eq? (mc-eval (cadr e) env) (mc-eval (caddr e) env)))
       ((eq? (car e) (quote car))   (car (mc-eval (cadr e) env)))
       ((eq? (car e) (quote cdr))   (cdr (mc-eval (cadr e) env)))
       ((eq? (car e) (quote cons))  (cons (mc-eval (cadr e) env) (mc-eval (caddr e) env)))
       ((eq? (car e) (quote cond))  (evcon (cdr e) env))
       (else (mc-eval (cons (assoc (car e) env) (cdr e)) env))))
    ((eq? (caar e) (quote lambda))
     (mc-eval (caddr (car e))
              (pairlis (cadr (car e)) (evlis (cdr e) env) env)))))
"""


def run(source, env):
    """Read and evaluate every top-level form in source. Return the last value."""
    result = []
    for form in read_all(source):
        result = lisp_eval(form, env)
    return result


# ── The guided demo ──────────────────────────────────────────────────────────────


def demo():
    env = make_global_env()
    run(PRELUDE, env)

    print("=" * 70)
    print("Lisp — John McCarthy, 1960 (Turing Award 1971)")
    print("=" * 70)
    print()
    print("BEFORE Lisp, a function could not call itself. Factorial meant a loop")
    print("and a mutable counter. AFTER Lisp, it is a function defined in terms")
    print("of itself:")
    print()

    factorial = """
    (define (fact n)
      (if (= n 0)
          1
          (* n (fact (- n 1)))))
    """
    print("    " + factorial.strip())
    run(factorial, env)
    print()
    print("    (fact 5)  =>  " + write(run("(fact 5)", env)))
    print("    (fact 10) =>  " + write(run("(fact 10)", env)))
    print()

    print("-" * 70)
    print("Code is data. A program is just a list, so programs build programs.")
    print("map takes a function as an argument, another idea Lisp introduced:")
    print()
    run("(define (square x) (* x x))", env)
    print("    (map square (list 1 2 3 4 5)) => "
          + write(run("(map square (list 1 2 3 4 5))", env)))
    print("    (append '(a b) '(c d))       => "
          + write(run("(append '(a b) '(c d))", env)))
    print()

    print("-" * 70)
    print("The punchline of the 1960 paper: eval written in Lisp, running on top")
    print("of this interpreter. Lisp defining Lisp. We evaluate the expression")
    print("    (cdr (cons (quote a) (quote (b c))))")
    print("using mc-eval, McCarthy's own evaluator, not the Python one:")
    print()
    metacircular = "(mc-eval '(cdr (cons (quote a) (quote (b c)))) '())"
    print("    " + metacircular)
    print("    =>  " + write(run(metacircular, env)))
    print()
    print("The Python eval ran the Lisp eval, which computed the answer. That")
    print("self-definition is what Alan Kay called the Maxwell's equations of")
    print("software.")
    print()

    if sys.stdin.isatty():
        repl(env)
    else:
        print("(Run interactively for a REPL, or pass --test / --verbose.)")


def repl(env):
    print("-" * 70)
    print("REPL. Type Lisp expressions. Ctrl-D to exit.")
    while True:
        try:
            line = input("lisp> ")
        except EOFError:
            print()
            return
        if not line.strip():
            continue
        try:
            print(write(run(line, env)))
        except Exception as err:
            print("error: " + str(err))


# ── Test suite ─────────────────────────────────────────────────────────────────


def run_tests():
    env = make_global_env()
    run(PRELUDE, env)

    # Each case: (source, expected value). We compare against Python values.
    cases = [
        # 1. arithmetic and nested calls
        ("(+ 1 2 3 4)", 10),
        # 2. subtraction and division chain
        ("(- (* 6 7) 2)", 40),
        # 3. the conditional McCarthy invented
        ("(cond ((< 3 2) 'no) ((> 3 2) 'yes) (else 'maybe))", Symbol("yes")),
        # 4. if with the false branch
        ("(if (= 1 2) 'a 'b)", Symbol("b")),
        # 5. quote returns data unevaluated
        ("(quote (a b c))", [Symbol("a"), Symbol("b"), Symbol("c")]),
        # 6. car / cdr / cons round trip
        ("(cons 1 (cons 2 (quote ())))", [1, 2]),
        # 7. car
        ("(car '(x y z))", Symbol("x")),
        # 8. cdr
        ("(cdr '(x y z))", [Symbol("y"), Symbol("z")]),
        # 9. atom? on a symbol is true, nil is an atom too
        ("(atom? 'x)", True),
        # 10. atom? on a non-empty list is false
        ("(atom? '(1 2))", False),
        # 11. eq? on equal symbols
        ("(eq? 'a 'a)", True),
        # 12. eq? on different symbols
        ("(eq? 'a 'b)", False),
        # 13. recursion: factorial
        ("(begin (define (f n) (if (= n 0) 1 (* n (f (- n 1))))) (f 6))", 720),
        # 14. recursion: fibonacci
        ("(begin (define (fib n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2))))) (fib 10))", 55),
        # 15. higher-order function: map
        ("(map (lambda (x) (* x x)) '(1 2 3 4))", [1, 4, 9, 16]),
        # 16. closures capture their environment
        ("(begin (define (adder n) (lambda (x) (+ x n))) (define add5 (adder 5)) (add5 100))", 105),
        # 17. let binding
        ("(let ((a 3) (b 4)) (+ (* a a) (* b b)))", 25),
        # 18. lexical scope: inner define does not leak, outer n is used
        ("(begin (define n 10) (define (g x) (+ x n)) (g 5))", 15),
        # 19. append
        ("(append '(1 2) '(3 4) '(5))", [1, 2, 3, 4, 5]),
        # 20. and short-circuits, returns last truthy value
        ("(and 1 2 3)", 3),
        # 21. or returns first truthy value
        ("(or #f #f 7)", 7),
        # 22. set! mutates an existing binding
        ("(begin (define c 0) (set! c (+ c 1)) (set! c (+ c 1)) c)", 2),
        # 23. mutual recursion: even?/odd?
        ("""(begin
              (define (even? n) (if (= n 0) #t (odd? (- n 1))))
              (define (odd? n)  (if (= n 0) #f (even? (- n 1))))
              (even? 10))""", True),
        # 24. THE metacircular test: McCarthy's eval, in Lisp, computes an answer
        ("(mc-eval '(car (cons (quote hello) (quote (world)))) '())", Symbol("hello")),
    ]

    passed = 0
    for i, (source, expected) in enumerate(cases, 1):
        try:
            got = run(source, env)
            ok = got == expected and type(got) == type(expected)
            status = "PASS" if ok else "FAIL"
            if ok:
                passed += 1
            print("{:>2}. {} {}".format(i, status, source.strip().splitlines()[0][:52]))
            if not ok:
                print("      expected {!r}, got {!r}".format(expected, got))
        except Exception as err:
            print("{:>2}. FAIL {}  (error: {})".format(i, source.strip()[:40], err))

    print()
    print("{} / {} passed".format(passed, len(cases)))
    return passed == len(cases)


# ── Entry point ────────────────────────────────────────────────────────────────


def main():
    global VERBOSE
    args = sys.argv[1:]

    if "--verbose" in args:
        VERBOSE = True

    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    if VERBOSE:
        # In verbose mode, show the full pipeline on one small expression.
        env = make_global_env()
        run(PRELUDE, env)
        source = "(* (+ 1 2) (- 10 4))"
        print("source: " + source)
        print("tokens: " + str(tokenize(source)))
        print("parsed: " + write(read_all(source)[0]))
        print("--- eval trace ---")
        result = run(source, env)
        print("result: " + write(result))
        return

    demo()


if __name__ == "__main__":
    main()
