# Week 06 — John McCarthy (1971)

**ACM Turing Award citation:** *"Dr. McCarthy's lecture 'The Present State of Research on Artificial Intelligence' is a topic that covers the area in which he has achieved considerable recognition for his own work."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — McCarthy's 1960 evaluator in about 40 lines: one function, `eval`, that takes a Lisp program written as a list and computes what it means. That function *is* the language.

[`implementation.py`](./implementation.py) — a full working Lisp interpreter. Text goes in, values come out:

```
source text
    ↓
tokenize          "(+ 1 2)"  →  ['(', '+', '1', '2', ')']
    ↓
read (parse)      →  nested lists, the same shape as data
    ↓
eval  ←──────────┐  walks the list; special forms + function application
    ↓            │
apply  ──────────┘  binds args in a new scope, recurses into the body
    ↓
value  →  write (print)
```

What it supports:
- Arithmetic, comparisons, and the list primitives `cons` / `car` / `cdr`
- The special forms McCarthy introduced: `quote`, `cond`, `lambda`, plus `if`, `let`, `define`, `set!`, `begin`, `and`, `or`
- Recursion, closures, lexical scope, and higher-order functions (`map` takes a function as an argument)
- Code as data: a program is a list, so programs can build and run programs
- A metacircular evaluator: McCarthy's `eval`, written in Lisp, running on top of this interpreter — Lisp defining Lisp

```bash
python concept.py                       # the core idea, plain
python implementation.py                # guided demo, then a REPL if interactive
python implementation.py --test         # test suite (24 cases)
python implementation.py --verbose      # show tokens, parse tree, and eval trace
```

Example session:

```
BEFORE Lisp, a function could not call itself. Factorial meant a loop
and a mutable counter. AFTER Lisp, it is a function defined in terms
of itself:

    (define (fact n)
      (if (= n 0)
          1
          (* n (fact (- n 1)))))

    (fact 5)  =>  120
    (fact 10) =>  3628800

The punchline of the 1960 paper: eval written in Lisp, running on top
of this interpreter.

    (mc-eval '(cdr (cons (quote a) (quote (b c)))) '())
    =>  (b c)

The Python eval ran the Lisp eval, which computed the answer.
```

---

## Full Worked Example

The claim that makes Lisp special: you can define the whole language in the language itself, in one function. Here is that function running, by hand, on a small expression. No steps skipped.

We evaluate this Lisp program:

```
(cdr (cons (quote a) (quote (b c))))
```

The true answer is `(b c)`: build the list `(a b c)` by consing `a` onto `(b c)`, then take the `cdr`, which drops the first element.

### Step 0 — Everything is a list

The program above is not text to `eval`. It is already a list of lists:

```
["cdr",
   ["cons",
      ["quote", "a"],
      ["quote", ["b", "c"]]]]
```

That is McCarthy's central trick. Code and data have the same shape, so the evaluator can treat a program as ordinary data and walk it.

### Step 1 — eval looks at the head

`eval(expr, env)` reads the first element of the list to decide what to do.

```
expr = (cdr (cons (quote a) (quote (b c))))
head = cdr
```

`cdr` is not a special form. It is a function call. So the rule is: evaluate the argument, then apply `cdr` to the result.

### Step 2 — Evaluate the argument to cdr

The argument is `(cons (quote a) (quote (b c)))`. Recurse into `eval` on it.

```
expr = (cons (quote a) (quote (b c)))
head = cons
```

`cons` is also a function call. Evaluate its two arguments first.

### Step 3 — Evaluate the arguments to cons

First argument: `(quote a)`.

```
head = quote
```

`quote` is a special form. Its whole job is to return its argument **without** evaluating it. So `(quote a)` returns the symbol `a`. This is how a program writes down literal data.

Second argument: `(quote (b c))` returns the list `(b c)`, again unevaluated.

### Step 4 — Apply cons

Now `cons` has its two evaluated arguments:

```
cons(a, (b c))  →  (a b c)
```

`cons` glues an element onto the front of a list. The result of the inner call is `(a b c)`.

### Step 5 — Apply cdr

Back up in Step 1, `cdr` now has its argument:

```
cdr((a b c))  →  (b c)
```

`cdr` returns everything after the first element. The final answer is `(b c)`. ✓

### The same run, but through McCarthy's eval instead of Python's

Everything above is what `implementation.py`'s Python `eval` does. The 1960 paper's real achievement is that the *identical* logic can be written **in Lisp**. Here is the core of `mc-eval` (from `PRELUDE` in the code):

```
(define (mc-eval e env)
  (cond
    ((atom? e) (assoc e env))                          ; a symbol: look it up
    ((atom? (car e))
     (cond
       ((eq? (car e) (quote quote)) (cadr e))          ; quote: return arg as-is
       ((eq? (car e) (quote car))   (car (mc-eval (cadr e) env)))
       ((eq? (car e) (quote cdr))   (cdr (mc-eval (cadr e) env)))
       ((eq? (car e) (quote cons))  (cons (mc-eval (cadr e) env)
                                          (mc-eval (caddr e) env)))
       ...))
    ((eq? (caar e) (quote lambda))                     ; a lambda call: bind + recurse
     (mc-eval (caddr (car e))
              (pairlis (cadr (car e)) (evlis (cdr e) env) env)))))
```

Run it on our expression:

```
(mc-eval '(cdr (cons (quote a) (quote (b c)))) '())   =>   (b c)
```

The Python `eval` is now running a Lisp program (`mc-eval`) that is itself an evaluator, and *that* evaluator computes `(b c)`. Two interpreters stacked, both following the exact same five steps above. That self-definition is the whole point: the language is small enough and expressive enough to describe itself.

### Edge case — recursion, which is where the environment earns its keep

A flat expression never needs a function to remember anything. `fact` does. Watch the environment chain on `(fact 3)`:

```
(define (fact n) (if (= n 0) 1 (* n (fact (- n 1)))))

(fact 3)
  env: {n: 3}         → (* 3 (fact 2))
  (fact 2)
    env: {n: 2}       → (* 2 (fact 1))
    (fact 1)
      env: {n: 1}     → (* 1 (fact 0))
      (fact 0)
        env: {n: 0}   → 1            ; base case, the recursion stops
      = 1
    = 2 * 1 = 2
  = 3 * 2 = 6
```

Each call gets a fresh scope where `n` has a different value, and each of those scopes is chained to the environment where `fact` was defined. That chaining is why the name `fact` is still visible from inside `fact`. Before Lisp, mainstream languages could not do this at all. A FORTRAN subroutine had one fixed set of variables, so it could not safely call itself. Recursion was McCarthy's, and the environment chain is how the interpreter above pulls it off.

---

## ELI5

Imagine you have a box of building blocks, and you also have an instruction card that says how to snap blocks together.

Before, the instructions had to be carved into the table. If you wanted new instructions, you needed a whole new table. The instructions and the table were stuck together.

John McCarthy did something clever. He made the instruction card out of the same blocks. Now the instructions are just another thing you can pick up, change, and hand to a friend, because they are made of the same stuff as everything else.

And here is the magic trick. He wrote one instruction card whose only job was to read other instruction cards and do what they say. That one card is a tiny machine that can follow any set of block instructions, including a copy of itself.

---

## ELI10

In the late 1950s, computers ran programs written as long lists of tiny machine steps, mostly moving numbers between memory cells. The best language of the day, FORTRAN, was built for arithmetic. It had no easy way for a function to call itself, and no way to treat a program as data you could look at or change. If you wanted the computer to do something with words, lists, or logic instead of numbers, you were mostly on your own.

John McCarthy wanted computers to reason, not just calculate. In 1955 he had coined the phrase "artificial intelligence" for a summer workshop at Dartmouth, and to actually build thinking programs he needed a language that could shuffle symbols around, not just crunch numbers. So in 1958 he designed Lisp. Its big idea was that a program and a piece of data look exactly the same: both are just lists in parentheses, like `(+ 1 2)`. Because a program is a list, another program can build it, inspect it, and run it.

To pin down what the language meant, McCarthy wrote a single function called `eval` that reads any Lisp expression and computes its value. Then he noticed something wild. He could write `eval` in Lisp itself. A one-page program that defines the entire language it is written in. Alan Kay later called it "the Maxwell's equations of software," because a whole world collapsed into a few lines. Along the way McCarthy also invented the if/else conditional that every language now has, and garbage collection, which is the computer automatically cleaning up memory you are done with so programmers stop doing it by hand.

That reframe still shapes how we build things. Every time your phone frees memory on its own, you are using McCarthy's garbage collection. Every `if` statement descends from his conditional. And the idea that code is just data you can generate and run is exactly what lets modern tools write and execute other programs, including the AI systems he was aiming at from the very beginning.

---

## CS Graduate Level — Why Lisp Mattered

### 1. The State of the Art Before (1955–1958)

The two languages that existed were FORTRAN (1957) and assembly. Both were models of the machine: named memory cells, arithmetic, and jumps. FORTRAN I had no recursion, because activation records were statically allocated, one fixed frame per subroutine, so a routine could not have two live invocations of itself. Data structures were arrays of fixed size. There was no first-class notion of a function, no dynamic allocation you could rely on, and nothing resembling symbolic computation.

McCarthy's goal was not numerics. It was artificial intelligence, a term he coined in the 1955 proposal for the 1956 Dartmouth Summer Research Project. Reasoning programs need to manipulate symbolic expressions, logical formulas, algebraic terms, plans, whose size and shape are not known ahead of time. None of the existing tools could do that cleanly. Lisp was designed backward from that need.

### 2. What Was Technically New

**Symbolic expressions (S-expressions).** The universal data structure is the list, built from cons cells (a pair of pointers). An atom is a symbol or number; everything else is a list of expressions. `(a (b c) d)` is a tree. This single recursive datatype replaced the array-of-scalars worldview.

**Homoiconicity: code is data.** A Lisp program is written as an S-expression. `(+ 1 2)` is simultaneously a call to `+` and a three-element list you can take apart with `car` and `cdr`. Because programs are data, a program can construct another program at runtime and evaluate it. This is the foundation of macros, symbolic differentiation, theorem provers, and every "programs that write programs" technique since.

**The conditional expression.** McCarthy introduced `cond`, an expression (it returns a value) rather than a statement (it directs control flow). `(cond (p1 e1) (p2 e2) ... (else en))` evaluates to the first `ei` whose `pi` is true. Every `if`/`else`, every ternary operator, every `switch` expression in every language descends from this. Before McCarthy, conditionals were `GOTO`-based control flow; he made them compositional.

**Recursion as the primary control structure.** With `cond` for the base case and self-reference for the step, recursion replaces the loop. This required activation records to be allocated dynamically (a stack), which in turn required...

**Garbage collection.** Cons cells are allocated constantly and their lifetimes are not statically knowable. McCarthy invented automatic garbage collection (described in the 1960 paper) so the programmer never frees memory by hand. Mark-and-sweep, reference counting, generational collectors, the whole field starts here.

**`eval` and the metacircular evaluator.** The semantics of Lisp are given by a function `eval[e, a]` that takes an expression `e` and an association list `a` (the environment) and returns the value. `apply` handles function calls. Crucially, `eval` can be written in Lisp, so the language defines itself.

### 3. How It Works: eval and apply

The two functions are mutually recursive. In modern pseudo-Lisp, stripped to the pure 1960 core:

```
eval[e, env] =
    atom?[e]        → lookup[e, env]
    e = (quote x)   → x
    e = (cond ...)  → evcon[clauses, env]
    e = (car x)     → car[eval[x, env]]      ; likewise cdr, cons, atom, eq
    atom?[car[e]]   → eval[cons[lookup[car[e], env], cdr[e]], env]   ; named fn
    caar[e] = lambda → eval[body, pairlis[params, evlis[args, env], env]]

apply[fn, args, env] = eval[body-of-fn, bind[params-of-fn, args, env]]
```

`eval` dispatches on the shape of the expression: a symbol is looked up, `quote` short-circuits evaluation, the primitives recurse on their arguments, and a lambda application extends the environment by pairing parameters with evaluated arguments (`pairlis`) and evaluates the body there. `implementation.py` runs exactly this as `mc-eval`, defined in Lisp, on top of the Python evaluator. Evaluating

```
(mc-eval '(car (cons (quote hello) (quote (world)))) '())   ⟹   hello
```

means the Python `eval` interprets the Lisp `mc-eval`, which interprets the inner expression. Two evaluators, same rules, one written in the language of the other. That fixed point, a language whose interpreter is expressible in the language, is what makes Lisp a foundation rather than just a tool.

### 4. A Concrete Before/After

```
FORTRAN-era factorial (no recursion; a loop over a mutable cell)

      FACT = 1
      DO 10 I = 1, N
      FACT = FACT * I
   10 CONTINUE

Lisp factorial (a function defined in terms of itself)

   (define (fact n)
     (if (= n 0)
         1
         (* n (fact (- n 1)))))
```

The FORTRAN version threads state through a counter because the language cannot express "the factorial of n is n times the factorial of n minus one." The Lisp version *is* that sentence. This is not cosmetic. Once functions are first-class and recursion is free, you get `map`, `fold`, closures, and the entire functional style, none of which had a home before Lisp.

### 5. What Descended From It

- **Garbage collection everywhere:** Java, Go, Python, JavaScript, C#, every managed runtime. Automatic memory management is now the default, and it started in Lisp.
- **The conditional expression:** `if`/`else`, ternaries, `match`/`switch` expressions, and pattern matching in ML, Haskell, Rust, and Scala.
- **First-class and higher-order functions:** lambdas and closures are now in essentially every mainstream language (Python, JS, Java, C++, Rust). `map`/`filter`/`reduce` are Lisp's `mapcar` and friends.
- **Code as data / metaprogramming:** Lisp macros, then everything from C++ templates to Rust macros to the read-eval-print loop. Interactive REPLs themselves are a Lisp invention.
- **The Lisp family:** Scheme, Common Lisp, Clojure, Racket, Emacs Lisp. Clojure runs on the JVM and is used in production today.
- **AI history:** Lisp was the language of AI research for three decades, from SHRDLU to expert systems to the Lisp Machines built to run it in hardware.
- **Time-sharing:** McCarthy proposed and pushed time-sharing, letting many users share one computer interactively, which shaped every operating system that followed.

### 6. Lasting Impact

The deepest legacy is the idea that a programming language can be built up from a tiny, self-describing core rather than bolted together as a pile of features. `eval` shows that the entire semantics of a language can fit on a page and be written in the language itself. That perspective, that you understand a system best by writing its interpreter, runs through the whole theory of programming languages. Structure and Interpretation of Computer Programs, the book that trained a generation, is organized around building evaluators. And McCarthy's original target has come full circle: the modern practice of programs that generate and run other programs, the thing that makes an LLM emitting and executing code even conceivable, is the code-is-data principle he made concrete in 1960. He set out to build machines that reason, and to do it he had to invent a language flexible enough to describe itself. We are still living inside that language's ideas.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Recursive Functions of Symbolic Expressions and Their Computation by Machine, Part I](https://doi.org/10.1145/367177.367199) | Communications of the ACM | 1960 |
| [A Proposal for the Dartmouth Summer Research Project on Artificial Intelligence](https://doi.org/10.1609/aimag.v27i4.1904) *(the paper that coined "artificial intelligence")* | AI Magazine (reprint) | 1955 |
| [Programs with Common Sense](http://www-formal.stanford.edu/jmc/mcc59.html) *(the "Advice Taker")* | Teddington Conf. on the Mechanization of Thought Processes | 1959 |
| [LISP 1.5 Programmer's Manual](https://mitpress.mit.edu/9780262130110/lisp-15-programmers-manual/) *(book)* | MIT Press | 1962 |
| [History of LISP](https://doi.org/10.1145/800025.808387) | ACM SIGPLAN History of Programming Languages | 1978 |

---

*Previous: [Week 05 — James H. Wilkinson (1970)](../05-james-wilkinson-1970/)*
