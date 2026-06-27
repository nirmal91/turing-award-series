"""
Lisp's eval — the core idea (John McCarthy, 1960)

Before Lisp, a program and the data it worked on were different kinds of
thing. Code was instructions for a machine. Data was numbers sitting in
memory. McCarthy saw that if you write programs as nested lists, then a
program is just data with the same shape as everything else. And once code
is data, you can write one short function that READS that data and runs it.
He called it eval.

This file is that function, in miniature. eval looks at an expression,
decides what kind it is, and computes its value, calling itself on the
pieces. Alan Kay called McCarthy's eval "the Maxwell's equations of
software": the whole of computation folded onto half a page. Everything
here is built from three things only: numbers, symbols, and lists.
"""


def seval(x, env):
    # A symbol is the name of something. Look up what it stands for.
    if isinstance(x, str):
        return env[x]

    # A number stands for itself. Nothing to compute.
    if not isinstance(x, list):
        return x

    head = x[0]

    # quote: hand back the expression WITHOUT evaluating it. This is the move
    # that makes code into data. (quote (a b c)) is just the list (a b c).
    if head == "quote":
        return x[1]

    # The seven primitive operators McCarthy said all of Lisp reduces to.
    if head == "atom":                       # is it a single thing, not a list?
        value = seval(x[1], env)
        return not isinstance(value, list)
    if head == "eq":                         # are two atoms the same?
        return seval(x[1], env) == seval(x[2], env)
    if head == "car":                        # the first item of a list
        return seval(x[1], env)[0]
    if head == "cdr":                        # everything after the first item
        return seval(x[1], env)[1:]
    if head == "cons":                       # put an item on the front of a list
        item = seval(x[1], env)
        rest = seval(x[2], env)
        return [item] + rest
    if head == "cond":                       # first true branch wins (if/elif)
        for clause in x[1:]:
            test = clause[0]
            result = clause[1]
            if is_true(seval(test, env)):
                return seval(result, env)
        return []

    # lambda: build a function value. It remembers its parameters, its body,
    # and the environment it was born in.
    if head == "lambda":
        return ["closure", x[1], x[2], env]

    # define: give a name to a value (often a function) in the environment.
    if head == "define":
        env[x[1]] = seval(x[2], env)
        return x[1]

    # Anything else is a function call. Evaluate the operator, evaluate every
    # argument, then apply.
    proc = seval(head, env)
    args = []
    for sub in x[1:]:
        args.append(seval(sub, env))
    return sapply(proc, args)


def sapply(proc, args):
    # A built-in (Python) operation like + or *.
    if callable(proc):
        return proc(*args)

    # A Lisp closure: bind the arguments to the parameter names in a fresh copy
    # of the closure's environment, then evaluate the body there.
    _, params, body, env = proc
    call_env = dict(env)
    for i in range(len(params)):
        call_env[params[i]] = args[i]
    return seval(body, call_env)


def is_true(value):
    # Falsity is the empty list (Lisp's nil) or the boolean false.
    # Every other value, including 0, is true.
    if value is False:
        return False
    if value == []:
        return False
    return True


# The starting environment. Arithmetic operators are ordinary functions, not
# special forms: they are just names bound to Python operations.
GLOBAL = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
}


# ── Example 1: code that builds and takes apart data ────────────────────────────
# Lists are the only data structure, so the same car/cdr/cons that a program is
# made of also work ON programs. cons two symbols onto nil to build (a b).
program = ["cons", ["quote", "a"], ["cons", ["quote", "b"], ["quote", []]]]
print("build a list:   ", seval(program, GLOBAL))          # ['a', 'b']
print("first of it:    ", seval(["car", program], GLOBAL))  # a
print("rest of it:     ", seval(["cdr", program], GLOBAL))  # ['b']


# ── Example 2: recursion, the thing Fortran could not do in 1958 ────────────────
# Define factorial as a function that calls itself. cond is the base case.
seval(["define", "fact",
       ["lambda", ["n"],
        ["cond",
         [["eq", "n", 0], 1],
         [["quote", "t"], ["*", "n", ["fact", ["-", "n", 1]]]]]]],
      GLOBAL)
print("fact 5:         ", seval(["fact", 5], GLOBAL))       # 120


# ── Example 3: the punchline — eval an expression you BUILT at runtime ───────────
# Construct the expression (* 6 7) as plain data with cons, then run it.
built = seval(["cons", ["quote", "*"],
               ["cons", ["quote", 6], ["cons", ["quote", 7], ["quote", []]]]],
              GLOBAL)
print("built program:  ", built)                            # ['*', 6, 7]
print("then ran it:    ", seval(built, GLOBAL))             # 42
print()
print("Code and data are the same lists. eval is the one function that turns")
print("the second into the first. That equivalence is McCarthy's whole idea.")
