"""
Lisp eval — the core idea (John McCarthy, 1960)

Before Lisp, a "programming language" was a pile of machine code. To run a new
language you first wrote a compiler for it, by hand, in thousands of lines of
assembly. The language and the machine were welded together.

McCarthy showed something startling in his 1960 paper: you can define the
meaning of a whole language in the language itself, on one page. This function,
eval, IS Lisp. Feed it a Lisp expression written as a list, and it tells you
what that expression computes. Alan Kay later called it "the Maxwell's
equations of software" — the whole thing collapsed into a few lines.

The trick that makes it possible: code and data are the SAME shape. A program
is just a list, so a program can be handed to another program as ordinary data.
Everything below manipulates lists. There are no numbers here on purpose — this
is McCarthy's original pure symbolic Lisp, seven primitives and a lambda.
"""

# Symbols are Python strings. Lists are Python lists. The empty list [] is "nil".


def eval_(e, env):
    # An atom (a symbol) is looked up in the environment: what is it bound to?
    if isinstance(e, str):
        return lookup(e, env)

    head = e[0]

    # quote: hand back the argument WITHOUT evaluating it. This is how a program
    # names a piece of data. (quote (a b c)) is the literal list (a b c).
    if head == "quote":
        return e[1]

    # atom: is the argument a single symbol (or nil), rather than a list?
    if head == "atom":
        x = eval_(e[1], env)
        return "t" if (isinstance(x, str) or x == []) else []

    # eq: are two atoms the same atom?
    if head == "eq":
        a = eval_(e[1], env)
        b = eval_(e[2], env)
        return "t" if (a == b and (isinstance(a, str) or a == [])) else []

    # car / cdr / cons: take a list apart and put one back together.
    if head == "car":
        return eval_(e[1], env)[0]
    if head == "cdr":
        return eval_(e[1], env)[1:]
    if head == "cons":
        return [eval_(e[1], env)] + eval_(e[2], env)

    # cond: the conditional. Walk the clauses; run the first whose test is true.
    # McCarthy invented this form. if/else in every language descends from it.
    if head == "cond":
        for clause in e[1:]:
            if eval_(clause[0], env) != []:
                return eval_(clause[1], env)
        return []

    # A function call. The head is either a lambda, or a name bound to one.
    fn = e[0]
    if isinstance(fn, str):
        fn = lookup(fn, env)               # (label/define bound name -> lambda)
    args = [eval_(arg, env) for arg in e[1:]]
    params = fn[1]
    body = fn[2]
    new_env = dict(env)
    for name, value in zip(params, args):
        new_env[name] = value
    return eval_(body, new_env)            # apply: run the body with args bound


def lookup(name, env):
    if name in env:
        return env[name]
    raise NameError("unbound symbol: " + name)


# ── Two programs, written as data, evaluated by the function above ──────────────

# 1. Pull the list apart and glue it back. Pure structure, no arithmetic.
program1 = ["cons", ["quote", "a"], ["cdr", ["quote", ["x", "b", "c"]]]]
print("cons a onto (cdr (x b c)) =>", eval_(program1, {}))

# 2. Recursion, McCarthy's way. ff finds the first atom by walking down car.
#    Given ((a b) c), it should return a. The function refers to itself by name,
#    which is the whole reason recursion belongs in a programming language.
env = {"ff": ["lambda", ["x"],
              ["cond",
               [["atom", "x"], "x"],
               [["quote", "t"], ["ff", ["car", "x"]]]]]}
program2 = ["ff", ["quote", [["a", "b"], "c"]]]
print("first atom of ((a b) c)  =>", eval_(program2, env))

print()
print("The evaluator above is about 40 lines. It is a complete language.")
print("Code is data: every program here is just a list eval walks over.")
