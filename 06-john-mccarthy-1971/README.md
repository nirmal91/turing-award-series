# Week 06 — John McCarthy (1971)

**ACM Turing Award citation:** *"Dr. McCarthy's lecture 'The Present State of Research on Artificial Intelligence' is a topic that covers the area in which he has achieved considerable recognition for his work."*

---

## My Take

Tracing some history of artificial intelligence, I was looking forward to this chapter. John McCarthy coined the term artificial intelligence. He is also directly or indirectly responsible for Lisp, macros, garbage collection, time sharing, and code as data. He is the quintessential computer scientist.

Before McCarthy, computing was mostly calculation, not generation. You fed the machine numbers and it handed numbers back. He was one of the first to get a machine to create new facts out of facts it already had. Socrates is a man. All men are mortal. So Socrates is mortal. A computer before McCarthy could not produce that last line on its own. To do that, a machine has to take old facts apart and build new ones. Which means facts can't sit there as frozen instructions. They have to be data the machine can pick up and rework. McCarthy's twist was to write the code in that same form, so code and data became the same thing.

The thing about Lisp that stuck with me: in a normal language your code gets parsed and compiled into something else before it runs. You never see that middle. In Lisp there is no middle. The list you write is the same list that runs. A small function called eval reads it and runs it on the spot. The code and the thing that runs the code are the same. And because Lisp makes and throws away lists constantly, he had to invent garbage collection to clean up. That is now standard in most languages, like Java, Python, and Go.

After 20+ years of writing code, I finally wrote Lisp for the first time.

---

## The Code

[`concept.py`](./concept.py) — McCarthy's `eval` in about 60 lines: one function that reads a program written as a nested list and computes its value, proving code and data are the same thing.

[`implementation.py`](./implementation.py) — a full working Lisp: a reader that turns text into S-expressions, an evaluator (`eval` / `apply`), lexical environments with real closures, recursion via `label`, and the seven primitives McCarthy started from.

```
source text
    ↓ tokenize      split into ( ) and atoms
    ↓ parse         build nested Python lists = S-expressions
    ↓ eval          walk the S-expression against an environment
    ↓ apply         bind arguments, evaluate the body
    ↓
  value
```

What it supports:
- The seven primitives from the 1960 paper: `quote`, `atom`, `eq`, `car`, `cdr`, `cons`, `cond`
- `lambda` with real lexical closures (a function remembers where it was born)
- Recursion two ways: `label` (McCarthy's original) and `define`
- Arithmetic and comparison so the examples do real work
- A REPL, a 17-case test suite, and a verbose mode that prints every `eval` step

```bash
python3 concept.py                      # the core idea, plain
python3 implementation.py               # interactive REPL
python3 implementation.py practice.lisp # load and run a Lisp source file
python3 implementation.py --test        # test suite (17 cases)
python3 implementation.py --verbose     # REPL that prints every eval step
```

Example session:

```
lisp> (cons (quote a) (quote (b c)))
(a b c)
lisp> (define fact (lambda (n) (cond ((eq n 0) 1) (t (* n (fact (- n 1)))))))
fact
lisp> (fact 5)
120
lisp> (((lambda (y) (lambda (x) (+ x y))) 10) 5)
15
```

The last line is a closure. The inner `lambda` captures `y = 10` and carries it around as data. That is the whole reason the same `eval` can run a program you just built out of lists.

---

## Full Worked Example

The claim in McCarthy's 1960 paper is that a whole interpreter fits in one function, `eval`, because a program is just a list. Here is `eval` running two programs by hand, step by step.

### Step 0 — Everything is a list

A program is written in exactly the same shape as its data: an atom (a symbol or number) or a list of them. `(cons x y)` is a three-element list whose first element happens to name an operation. That sameness is what lets one function walk both.

The environment is a table of what names mean. It starts with the built-ins:

```
env = { car: <builtin>, cdr: <builtin>, cons: <builtin>,
        atom: <builtin>, eq: <builtin>, +: <builtin>, ... , t: t }
```

### Step 1 — Apply a lambda to an argument

Evaluate `((lambda (x) (cons x (quote (b c)))) (quote a))`.

The expression is a list. Its first element is itself a list starting with `lambda`, so this is a **function application**: evaluate the operator, evaluate the argument, then apply.

```
eval  ((lambda (x) (cons x (quote (b c)))) (quote a))     env
```

**Evaluate the operator.** `(lambda (x) (cons x (quote (b c))))` evaluates to a closure: the parameter list `(x)`, the body `(cons x (quote (b c)))`, and a pointer to `env`.

**Evaluate the argument.** `(quote a)` is a special form. `quote` returns its argument without evaluating it, so this is the atom `a`.

**Apply.** Make a fresh environment whose parent is `env` and bind the parameter:

```
local = { x: a }   -> parent env
```

Now evaluate the body `(cons x (quote (b c)))` in `local`:

```
eval  (cons x (quote (b c)))              local
    eval  cons          -> <builtin>       (found by walking local -> env)
    eval  x             -> a               (found in local)
    eval  (quote (b c)) -> (b c)           (quote, unevaluated)
    apply cons to (a, (b c))
        [a] + [b, c]    -> (a b c)
=> (a b c)
```

Result: `(a b c)`. Notice `eval` called itself three times on the sub-expressions, then handed off to `apply`, which called `eval` again on the body. `eval` and `apply` calling each other is the entire engine.

### Step 2 — Recursion with `label`

`lambda` alone cannot refer to itself, because the function has no name inside its own body. McCarthy's fix was `label`: `(label f (lambda ...))` binds the name `f` to the closure inside an environment the closure can see. Evaluate factorial of 3:

```
((label fact (lambda (n) (cond ((eq n 0) 1) (t (* n (fact (- n 1))))))) 3)
```

`label` builds an environment where `fact` points to the closure, so every recursive call finds it. Now watch the recursion unwind. Each call gets its own `local` with its own `n`:

```
fact(3):  (eq 3 0) -> f    so take (* 3 (fact (- 3 1)))
  fact(2):  (eq 2 0) -> f    so take (* 2 (fact (- 2 1)))
    fact(1):  (eq 1 0) -> f    so take (* 1 (fact (- 1 1)))
      fact(0):  (eq 0 0) -> t    so return 1
    fact(1) = 1 * 1 = 1
  fact(2) = 2 * 1 = 2
fact(3) = 3 * 2 = 6
```

Four nested environments, each with its own `n`, all pointing back to the one where `fact` is defined. That chain of environments is lexical scope, and it is why the recursion terminates cleanly at `n = 0`.

### Step 3 — `cond` picks the first true branch

Inside each call, `cond` is a special form. It does **not** evaluate all its branches. It walks the clauses in order, evaluates each test, and returns the value of the first clause whose test is not false:

```
(cond ((eq n 0) 1)          test (eq n 0)
      (t (* n (fact ...))))  test t  (always true, the else branch)
```

For `n = 3` the first test is `f`, so `cond` skips the `1` entirely and evaluates the second clause. This short-circuiting is why `cond` has to be a special form and not a function: a function would evaluate `(fact (- n 1))` even at the base case and recurse forever.

### Edge case — an unbound name

Evaluate a symbol that was never defined:

```
eval  banana     env
```

`banana` is a symbol, so `eval` looks it up. It checks `env`, finds nothing, has no parent, and raises:

```
error: unbound symbol: banana
```

No branch, no fallback. Lookup is the base case of `eval` for symbols, and when it fails there is nothing else to try. Compare that to a number like `7`, which is not a symbol and not a list, so `eval` returns it unchanged. Those two cases (self-evaluating atoms and name lookup) are the floor the whole recursion rests on.

---

## ELI5

Imagine your toy instructions and your toys were made of the same blocks.

Before, the instructions for building a toy were locked inside the machine. You could not pick them up, change them, or hand them to a friend. They were one kind of thing, and your toys were another.

John McCarthy made a language where the instructions are built out of the exact same blocks as everything else. `(add 2 3)` is just a little pile of three blocks: `add`, `2`, `3`. You can hold it, take it apart, or build a new pile and hand it to the machine to run.

So he only had to write one tiny helper. You give it a pile of blocks and it does what the blocks say. Because the instructions and the stuff are the same blocks, that one helper can run any program at all.

---

## ELI10

In the 1950s, a program and its data were two completely different things. The program was a fixed list of machine steps burned into how the computer worked. The data was numbers sitting in memory slots. A program could crunch numbers, but it could not read another program, take it apart, or build a new one. And most languages of the day, like early Fortran, could barely do recursion, where a function calls itself.

John McCarthy wanted to write programs that could reason, which meant shuffling around symbols and expressions, not just numbers. So in 1958 he designed a language called Lisp where code and data have the exact same shape: a list written in parentheses. `(+ 1 2)` is a list of three things. So is your shopping list. Because they look identical, a program can build another program the way it would build any list, then run it.

Then McCarthy did something no one had done before. He wrote the language in itself. He defined one function called `eval` that takes a program (a list) and figures out its value, calling a partner function `apply` to plug arguments into functions. `eval` and `apply` take turns calling each other, and together they are a complete interpreter in about a page. When Steve Russell, one of McCarthy's students, hand-translated that one page of math into machine code in 1960, Lisp suddenly existed as a real, running language. McCarthy had not planned that. He thought `eval` was just a neat piece of theory.

That single idea, code as data run by `eval`, is why Lisp gave us so much of what we take for granted: automatic garbage collection (McCarthy invented it so Lisp could make and discard lists freely), the read-eval-print loop that every Python and JavaScript console still uses, and the whole style of writing programs that manipulate other programs. He also coined the term "artificial intelligence" in 1955 and pushed the idea of time-sharing, where many people share one computer at once. Nearly everything about how we actually sit down and talk to a computer traces back to him.

---

## CS Graduate Level — Code as Data, and the Interpreter That Defined Itself

### 1. The State of the Art Before (1954–1958)

Fortran (1957) was the great achievement of the moment, and it was built for numerical computation over statically laid-out arrays. Its data model was fixed: you declared your storage and the compiler assigned it. There was no dynamic allocation of structured data, no first-class notion of a program as a manipulable object, and recursion was not supported (the calling convention used fixed return-address slots). Assembly, the alternative, had none of these things either. For McCarthy's actual goal, the Advice Taker — a program that represents facts about the world as symbolic expressions and derives new ones — none of this was workable. He needed to build and tear apart symbolic structures whose size was not known in advance, and he needed functions defined by recursion over those structures.

### 2. The S-expression and Code-as-Data

McCarthy's foundational decision was a uniform representation: the **symbolic expression**, or S-expression. An S-expression is either an atom or a pair `(x . y)`; lists are built from pairs ending in the special atom `nil`. `(A B C)` is sugar for `(A . (B . (C . nil)))`. The consequence that mattered was that *program text and data share this single structure*. The expression `(cons 1 (quote (2 3)))` is simultaneously a program to run and a list of three elements to inspect. This is **homoiconicity**, and it is the property almost no other language family committed to.

The primitive operations are famously few:

- `cons` builds a pair, `car` and `cdr` take it apart (the names are leftovers from IBM 704 address/decrement registers).
- `atom` and `eq` are the predicates.
- `quote` marks a piece of structure as data rather than code.
- `cond` is the conditional.

From these seven, plus `lambda` for functions and `label` for recursion, the entire language is constructed. `implementation.py` defines exactly this set in `global_env()` and treats `quote`, `cond`, `lambda`, `define`, and `label` as special forms in `seval`.

### 3. eval: The Language Defined in Itself

The centerpiece of the 1960 paper is a function `eval[e, a]` — evaluate expression `e` in association list `a` — written in Lisp itself, alongside its partner `apply`. This is the **metacircular evaluator**: an interpreter for a language, written in that same language. Its structure, translated to the code in this chapter:

```python
def seval(x, env):
    if isinstance(x, Symbol):        # a name        -> look it up
        return env.lookup(x)
    if not isinstance(x, list):      # a number      -> itself
        return x
    op = x[0]
    if op == "quote":  return x[1]                       # data, not code
    if op == "cond":   ...                               # first true clause
    if op == "lambda": return Procedure(x[1], x[2], env) # a closure
    ...
    proc = seval(op, env)            # otherwise: apply
    args = [seval(a, env) for a in x[1:]]
    return apply_(proc, args)
```

Two facts make this profound. First, it is short — the real thing is about a page, because the recursion structure of `eval` mirrors the recursive structure of S-expressions exactly. Second, it is self-describing: reading `eval` tells you precisely what the language *is*, with no gap between specification and implementation. In 1960 Steve Russell observed that this page of theory could simply be hand-compiled into IBM 704 machine code, producing the first Lisp interpreter. The `eval`/`apply` mutual recursion in the paper became a running program essentially unchanged.

A subtle point the worked example above makes concrete: `cond` and `quote` **must** be special forms, evaluated by `eval` itself rather than treated as ordinary functions. If `cond` were a function, all its branches would be evaluated before it ran, and a recursive base case like `((eq n 0) 1)` could never stop the recursion. The distinction between special forms (control the evaluation of their arguments) and functions (receive already-evaluated arguments) starts here.

### 4. Closures and Lexical Environments

A `lambda` is not just its parameters and body; it is those *plus the environment it was created in*. That triple is a **closure**. In the implementation:

```python
class Procedure:
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env          # the environment captured at definition time
```

The test `(((lambda (y) (lambda (x) (+ x y))) 10) 5)` returns `15` because the inner `lambda` captures `y = 10` in its `env` and carries it away after the outer function has returned. Environments form a parent-pointer chain; lookup walks outward until it finds a binding. This is lexical scope, and the closure is the data structure that makes it work. (McCarthy's original used dynamic scope via a single association list — the well-known "funarg problem" — and it took Scheme in 1975 to nail down lexical closures. The version here uses the modern lexical form, which is what descended and won.)

### 5. What Descended From It

- **Garbage collection.** Because Lisp allocates cons cells constantly and cannot know when they die, McCarthy invented automatic garbage collection (mark-and-sweep) in 1959. Every managed-memory language since — Java, Python, Go, JavaScript — is downstream of that necessity.
- **The REPL.** `read` -> `eval` -> `print` -> loop is the Lisp interaction model. Every interactive interpreter console today is a REPL.
- **Recursion and first-class functions.** Lisp made recursion and functions-as-values ordinary. They are now table stakes; in 1958 they were radical.
- **Macros and metaprogramming.** Because code is data, a Lisp program can transform program text before running it. This is the direct ancestor of macro systems and, more loosely, of every tool that generates or rewrites code.
- **Artificial intelligence as a field.** McCarthy coined the term in the 1955 proposal for the 1956 Dartmouth Summer Research Project, the event that founded AI. Lisp was the field's dominant language for decades.
- **Time-sharing.** McCarthy pushed the idea that many users should share one computer interactively rather than submit batch jobs. This shaped CTSS and MIT's Project MAC, and through them the interactive computing we now consider default.
- **Formalizing common-sense reasoning.** His situation calculus (1963) and the earlier Advice Taker proposal put logical knowledge representation on the map, a line that runs through decades of AI.

### 6. Lasting Impact

The deepest legacy is the idea that a language can be its own specification. `eval` collapsed the distance between "what the language means" and "a program that runs it," and it did so by taking one design commitment — code and data have the same structure — completely seriously. That commitment is why Lisp dialects (Scheme, Common Lisp, Clojure, Racket, Emacs Lisp) are still where people go to think clearly about interpreters, macros, and language design. Every time you open a Python shell, hit a JavaScript console, or watch an interpreter read your code as an abstract syntax tree and walk it, you are using machinery McCarthy laid down in a paper he thought was pure theory. The modern connection is almost too neat: today's large language models are steered by prompts and tool calls that are themselves programs-as-data, evaluated by an outer loop — and the field they belong to still goes by the name McCarthy gave it.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Recursive Functions of Symbolic Expressions and Their Computation by Machine, Part I](https://doi.org/10.1145/367177.367199) | Communications of the ACM | 1960 |
| [A Proposal for the Dartmouth Summer Research Project on Artificial Intelligence](https://doi.org/10.1609/aimag.v27i4.1904) *(reprinted 2006)* | AI Magazine (orig. 1955) | 1955 |
| [Programs with Common Sense](https://www-formal.stanford.edu/jmc/mcc59.html) *(the Advice Taker)* | Proc. Teddington Conf. on the Mechanization of Thought Processes | 1959 |
| [LISP 1.5 Programmer's Manual](https://mitpress.mit.edu/9780262130110/lisp-1-5-programmers-manual/) *(book)* | MIT Press | 1962 |
| [Situations, Actions, and Causal Laws](https://doi.org/10.5555/1024368) *(situation calculus)* | Stanford AI Memo 2 | 1963 |
| [Generality in Artificial Intelligence](https://doi.org/10.1145/1283920.1283926) *(Turing Award lecture)* | Communications of the ACM | 1987 |

---

*Previous: [Week 05 — James H. Wilkinson (1970)](../05-james-wilkinson-1970/)*
