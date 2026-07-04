"""
Lisp eval — the core idea (John McCarthy, 1960)

Before Lisp, a program and its data were different kinds of thing. Code was a
fixed sequence of machine operations. Data was numbers in fixed slots. You could
not hand a program to another program as ordinary data and take it apart.

McCarthy noticed that if you write both code and data in the same shape — nested
lists of symbols, the S-expression — then a program is just a piece of data, and
you can write one short function that reads that data and runs it. He called that
function eval. eval is Lisp defined in itself: give it an expression and a table
of what the names mean, and it computes the value. The seven operators below
(quote, atom, eq, car, cdr, cons, cond) plus lambda are all McCarthy needed. Every
other Lisp feature is built out of these. This tiny function is the thing that got
copied into Scheme, Clojure, Python, JavaScript, and every language with a REPL.
"""

# An S-expression is either an atom (here, a Python string) or a list of
# S-expressions. Code and data share this one shape. That sameness is the point.

def eval_(e, env):
    # A bare atom is a name. Look up what it stands for in the environment.
    if isinstance(e, str):
        return env[e]

    op = e[0]

    if op == "quote":            # (quote X) -> X itself, treated as data, not run
        return e[1]

    if op == "atom":             # is the argument an atom rather than a list?
        x = eval_(e[1], env)
        return "t" if isinstance(x, str) else "f"

    if op == "eq":               # are two atoms the same atom?
        a = eval_(e[1], env)
        b = eval_(e[2], env)
        return "t" if a == b else "f"

    if op == "car":              # the first element of a list
        return eval_(e[1], env)[0]

    if op == "cdr":              # everything after the first element
        return eval_(e[1], env)[1:]

    if op == "cons":             # stick a new first element onto a list
        head = eval_(e[1], env)
        tail = eval_(e[2], env)
        return [head] + tail

    if op == "cond":             # first branch whose test is "t" wins
        for pair in e[1:]:
            if eval_(pair[0], env) == "t":
                return eval_(pair[1], env)
        return []

    if op == "lambda":           # a function evaluates to itself, held as data
        return e

    # Anything else is a function application: (f arg1 arg2 ...).
    # Evaluate f to get a lambda, bind its parameters to the evaluated args,
    # then evaluate the body in that extended environment.
    f = eval_(op, env)           # f is [ "lambda", [params...], body ]
    params = f[1]
    body = f[2]
    local = dict(env)
    for i in range(len(params)):
        local[params[i]] = eval_(e[i + 1], env)
    return eval_(body, local)


def show(x):
    """Print an S-expression the way Lisp would: atoms plain, lists in parens."""
    if isinstance(x, str):
        return x
    return "(" + " ".join(show(item) for item in x) + ")"


# ── Two expressions, run by the same eval ───────────────────────────────────────

env = {}

# 1. Plain data manipulation. Build a list by consing an atom onto a quoted list.
expr1 = ["cons", ["quote", "a"], ["quote", ["b", "c"]]]
print("expr:  ", show(expr1))
print("value: ", show(eval_(expr1, env)))
print()

# 2. Define a function inline and apply it. The lambda is data until eval runs it.
#    ((lambda (x) (cons x (quote (b c)))) (quote a))  ->  (a b c)
expr2 = [["lambda", ["x"], ["cons", "x", ["quote", ["b", "c"]]]],
         ["quote", "a"]]
print("expr:  ", show(expr2))
print("value: ", show(eval_(expr2, env)))
print()

print("The same eval ran both. Code and data are the same nested lists,")
print("so a program can be built, taken apart, and run as ordinary data.")
