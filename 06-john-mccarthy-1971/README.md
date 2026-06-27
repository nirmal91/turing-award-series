# Week 06 — John McCarthy (1971)

**ACM Turing Award citation:** *"Dr. McCarthy's lecture 'The Present State of Research on Artificial Intelligence' is a topic that covers the area in which he has achieved considerable recognition for his work."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — McCarthy's eval in miniature: one function that reads a list, decides what kind of expression it is, and computes its value by calling itself on the pieces. Code and data are the same lists, so the last example builds a program with `cons` and then runs it.

[`implementation.py`](./implementation.py) — a working Lisp interpreter built around eval/apply, with a reader, lexical environments, closures, recursion, and McCarthy's own eval written in this dialect and run inside it:

```
source text
    ↓
reader  (tokenize → parse)          text becomes nested lists (S-expressions)
    ↓
eval / apply                        the seven primitives + cond + lambda + define
    ↓   ├── environments            lexical scope via a parent chain
    ↓   └── closures                a lambda plus the environment it was born in
    ↓
value  →  printed back as Lisp text
```

What it supports:
- Parse Lisp source into lists with `'` shorthand for `quote`
- The seven primitive operators McCarthy reduced Lisp to: `quote atom eq car cdr cons cond`
- `if`, `cond`, `define`, `lambda`, `let`, `begin`, `and`, `or`, recursion, and closures
- A read-eval-print loop (the REPL, which Lisp invented)
- The metacircular evaluator: run `mc-eval`, a Lisp interpreter written in Lisp, inside this interpreter

```bash
python3 concept.py                      # the core idea, plain
python3 implementation.py               # interactive REPL
python3 implementation.py --demo        # guided tour
python3 implementation.py --test        # test suite (31 cases)
python3 implementation.py --verbose     # show reader, parse tree, and eval steps
```

Example session:

```
lisp> (define (fact n) (if (= n 0) 1 (* n (fact (- n 1)))))
fact
lisp> (fact 5)
120
lisp> (define prog (cons '* (cons 6 (cons 7 '()))))
prog
lisp> prog
(* 6 7)
lisp> (mc-eval '(cons (quote a) (cons (quote b) (quote ()))) '())
(a b)
```

The third line builds a list that happens to be a valid program. The last line runs an interpreter, written in Lisp, on top of this one.

---

## Full Worked Example

The thing to understand is eval: how one function runs a program by calling itself on the program's parts. We will trace `(fact 3)` by hand, every frame, then look at the two ideas that make Lisp Lisp.

### Step 0 — Everything is a list

The reader turns text into nested lists. There is no separate syntax tree. The list *is* the tree.

```
"(* n (fact (- n 1)))"   reads as   ["*", "n", ["fact", ["-", "n", 1]]]
```

A symbol like `n` is a name. A number like `1` stands for itself. A list means "apply the first element to the rest." That is the whole grammar.

### Step 1 — The definition

```
(define (fact n) (if (= n 0) 1 (* n (fact (- n 1)))))
```

`define` stores a closure under the name `fact`. A closure is three things kept together: the parameter list `(n)`, the body `(if (= n 0) 1 (* n (fact (- n 1))))`, and the environment it was defined in (the global one, where `fact`, `*`, `-`, `=` all live).

### Step 2 — Evaluate `(fact 3)`

`eval` sees a list whose head `fact` is not a special form, so this is a function call. It evaluates the operator (look up `fact` → the closure) and the argument (`3` → `3`), then applies.

Apply makes a new environment frame where `n = 3`, with the global environment as its parent, and evaluates the body there.

```
frame A:  n = 3   → eval (if (= n 0) 1 (* n (fact (- n 1))))
```

`if` evaluates the test `(= n 0)`. Look up `n` → 3, compare to 0 → false. So `if` takes the else branch: `(* n (fact (- n 1)))`.

To compute that, eval needs `(fact (- n 1))` first. `(- n 1)` is `3 - 1 = 2`, so it calls `(fact 2)`.

```
frame B:  n = 2   → (* n (fact (- n 1)))   needs (fact 1)
frame C:  n = 1   → (* n (fact (- n 1)))   needs (fact 0)
frame D:  n = 0   → (if (= n 0) 1 ...)     test is true → returns 1
```

Frame D hits the base case. `(= n 0)` is true, so `if` returns `1` without recursing further. Now the stack unwinds, each frame multiplying by its own `n`:

```
frame D returns  1
frame C:  (* 1 1)  = 1        (n = 1, times fact 0)
frame B:  (* 2 1)  = 2        (n = 2, times fact 1)
frame A:  (* 3 2)  = 6        (n = 3, times fact 2)
```

`(fact 3)` is `6`. Each frame kept its own `n` because each call got its own environment with the global one as parent. That parent chain is lexical scope.

### Step 3 — Why this was impossible before

Fortran in 1957 had no recursion. A subroutine could not call itself, because there was one fixed block of memory per routine, not a fresh frame per call. The factorial above could not be written. You wrote a loop and a counter and managed the storage yourself. McCarthy's eval gives every call its own frame, so a function calling itself just works. The four frames above are four separate environments, automatically.

### Step 4 — The first idea: cond and the conditional expression

Before McCarthy, a "test" was a jump: `IF (X) 40, 50, 60` sent control to a line number depending on a sign. McCarthy made the conditional an *expression* that returns a value:

```
(cond ((eq 1 2) 'no)
      ((eq 2 2) 'yes)
      (t        'fallback))   =>  yes
```

eval walks the clauses, evaluates each test, and returns the result of the first true one. This is the `if/elif/else` and the `?:` of every language since. It came from here.

### Step 5 — The second idea: code is data

A program is a list. So you can build one with the same `cons` you use for any list, then hand it to eval.

```
(define prog (cons '* (cons 6 (cons 7 '()))))
prog                =>  (* 6 7)        a piece of data
(eval prog)         =>  42             the same data, run as code
```

Nothing else in 1960 could do this. In Fortran a program was punched cards, fundamentally a different kind of object from the numbers it added. In Lisp there is one kind of object. That is why Lisp grew macros, symbolic algebra, and AI systems that write and run their own code.

### Step 6 — The punchline: eval written in Lisp

If a program is just a list, and eval is just a function, you can write eval *in Lisp*. McCarthy did, in his 1960 paper, in about a page. [`implementation.py`](./implementation.py) carries that program as `mc-eval` and runs it on top of the Python interpreter:

```
(mc-eval '(cons (quote a) (cons (quote b) (quote ()))) '())   =>  (a b)
(mc-eval '(car x) '((x (1 2 3))))                             =>  1
```

The second call passes an environment `((x (1 2 3)))` as an association list. `mc-eval` looks `x` up in it, takes the `car`, and returns `1`. An interpreter, written in the language, interpreting the language. Alan Kay called this half-page of code "the Maxwell's equations of software."

### Edge case — a program that is also broken data

Because code and data share one representation, a malformed program is just a malformed list, and the reader catches it as a list error:

```
lisp> (+ 1 2
error: missing )
```

There is no separate "syntax error" subsystem. The same reader that builds your data builds your code, so the same check guards both. That uniformity is the cost and the gift of homoiconicity.

---

## ELI5

Imagine your toy box has only one kind of toy: little nesting cups. You can put cups inside cups to make anything.

Before, a *story* about your cups (do this, then this) had to be written on paper, totally separate from the cups themselves. The cups were one thing. The instructions were another.

John McCarthy had a magic idea. He said: write the instructions out of cups too. Now the instructions are made of the exact same stuff as the toys. And here is the trick. He built one special cup-reader that looks at a stack of instruction-cups and actually does what they say.

So you can build a little tower of cups that means "multiply six and seven," hand it to the reader, and out comes forty-two. The recipe and the ingredients are the same cups. That one idea is most of what computers do today.

---

## ELI10

In the late 1950s computers were good at one thing: arithmetic on numbers stored in fixed slots of memory. The popular language, Fortran, was built for exactly that. But John McCarthy wanted computers to do something harder. He wanted them to reason, to manipulate symbols and ideas, not just crunch numbers. For that he needed a language that could handle lists of things and could even handle programs as things. Fortran could not. It could not even let a function call itself.

So in 1958 McCarthy designed Lisp. His big move was to make everything a list. Data is a list. A program is a list too. To run a program you call one function, `eval`, that looks at the list, figures out what it means, and computes the answer by calling itself on the smaller pieces. He boiled the whole language down to seven basic operations with strange short names like `car`, `cdr`, and `cons`, plus a way to ask questions (`cond`) and a way to make new functions (`lambda`). From those seven pieces you can build everything else, including recursion, where a function calls itself to solve a smaller version of the same problem.

The part that still amazes people is what happens when code and data are the same shape. You can write a program that builds another program as a list, then runs it. McCarthy proved the point by writing `eval`, the Lisp interpreter, in Lisp itself, in about one page. An interpreter that interprets its own language. Alan Kay, who later helped invent the personal computer, called that page "the Maxwell's equations of software," meaning it captured the essence of computing the way four equations capture all of electromagnetism.

McCarthy did more than Lisp. He coined the term "artificial intelligence" in 1955 when he and three others proposed a summer workshop at Dartmouth. He pushed the idea that many people could share one computer at the same time, which became time-sharing and, much later, the seed of the idea that computing could be a public utility you rent, the way we now rent cloud servers. The conditional expression you see as `if/else` or `? :` in every language today came from his work. And garbage collection, where the computer automatically reclaims memory you are done with, was his invention for Lisp. Python, JavaScript, Java, and almost every modern language do it because he did it first.

---

## CS Graduate Level — Why Lisp and eval Mattered

### 1. The State of the Art Before (mid-1950s)

The frontier language was Fortran (1957). It was a triumph for numerical computing, but it reflected the machine underneath it: variables were fixed memory cells, control flow was the arithmetic `IF` and `GOTO` to statement numbers, and there was no recursion, because there was no automatically allocated stack frame per call. Data structures were arrays of fixed size. There was no notion of a program as a manipulable object; source was input to a compiler and nothing more. Symbolic computation, the kind needed for theorem proving, algebra, and the AI McCarthy was after, had to be hand-encoded into integer arrays with bookkeeping the programmer maintained by hand.

The dominant model of "what a computation is" was therefore Turing's tape and von Neumann's stored program, both operational and machine-shaped. Lambda calculus existed (Church, 1930s) as a theory of computation built on functions and substitution, but it was a logician's tool, not something anyone had made a machine speak.

### 2. McCarthy's Insight

McCarthy fused three things: Church's lambda calculus, the recursive function theory of Kleene, and a concrete list representation. The result, laid out in "Recursive Functions of Symbolic Expressions and Their Computation by Machine, Part I" (CACM, 1960), rests on a few decisions that look obvious only in retrospect.

**Symbolic expressions (S-expressions).** Everything is an atom or a pair of S-expressions. Lists are built from pairs. There is one universal data structure, and it nests arbitrarily.

**Seven primitives.** All of pure Lisp reduces to `quote`, `atom`, `eq`, `car`, `cdr`, `cons`, and `cond`. `car` and `cdr` take apart a pair; `cons` builds one; `atom` and `eq` are the predicates; `quote` suspends evaluation; `cond` chooses. The names `car`/`cdr` are an accident of the IBM 704's address and decrement registers, and they stuck.

**The conditional expression.** `cond` returns a value rather than transferring control. This is a deeper change than it sounds: it makes the language *expression-oriented*, which is what lets functions be defined by composition and recursion instead of by sequences of side effects. The `if-then-else` expression and the ternary operator descend directly from it, and McCarthy carried the idea into ALGOL 60, which is why nearly every language has it.

**lambda and recursion.** Functions are first-class values created by `lambda`, and they can refer to themselves, so recursion is the natural control structure. Combined with per-call environments, this made the call stack and lexical scope ordinary.

**Homoiconicity.** Because a program is written as an S-expression, programs and data have one representation. `quote` is the hinge: it lets you hold a piece of code as data, and eval lets you run a piece of data as code.

### 3. How eval Works

The center of the paper is `eval`, a universal function: given a representation of any Lisp expression and an environment, it returns the value of that expression. Sketched in the dialect this chapter implements:

```
(define (mc-eval e env)
  (cond
    ((atom e) (assoc e env))                 ; a symbol: look it up
    ((eq (car e) (quote quote)) (car (cdr e)))   ; (quote x) -> x
    ((eq (car e) (quote atom)) (atom (mc-eval (car (cdr e)) env)))
    ((eq (car e) (quote car))  (car  (mc-eval (car (cdr e)) env)))
    ((eq (car e) (quote cdr))  (cdr  (mc-eval (car (cdr e)) env)))
    ((eq (car e) (quote cons)) (cons (mc-eval (car (cdr e)) env)
                                     (mc-eval (car (cdr (cdr e))) env)))
    ((eq (car e) (quote cond)) (mc-evcon (cdr e) env))
    (t (quote unknown-form))))
```

Three things are remarkable. First, it is short: the full version with `lambda` and `label` fits on a page. Second, it is *written in the language it interprets*, so reading it teaches you both the language and its semantics at once. Third, it is constructive proof that the seven primitives plus `lambda` are computationally universal, the Lisp analogue of a universal Turing machine, but in a form a programmer can read. `implementation.py` runs exactly this `mc-eval` on top of its host interpreter:

```
(mc-eval '(cdr x) '((x (1 2 3))))   =>   (2 3)
```

The host interpreter parses that, evaluates the call to `mc-eval`, which walks its own `cond`, finds the `cdr` clause, recursively evaluates `x` by `assoc` against the environment `((x (1 2 3)))`, and takes the `cdr`. An interpreter interpreting an interpreter, with the inner one expressed in the outer one's language.

### 4. From the Model to a Running System

The 1960 paper was theory; Steve Russell then noticed `eval` could be *implemented* rather than just read, and hand-compiled it into machine code for the IBM 704. That made Lisp a real language. Two inventions were forced by the design:

- **Garbage collection.** `cons` allocates without the programmer freeing anything, so memory had to be reclaimed automatically. McCarthy invented garbage collection for Lisp around 1959. Every managed-memory language today, Java, Python, JavaScript, Go, inherits this.
- **The REPL.** Because source is data the reader already knows how to parse, an interactive read-eval-print loop is almost free: read an S-expression, eval it, print the result, repeat. Interactive programming as we know it starts here.

### 5. What Descended From It

- **Languages:** Scheme, Common Lisp, Clojure are direct descendants; the conditional expression, first-class functions, recursion, and dynamic typing spread from Lisp into ML, Haskell, Python, JavaScript, and Ruby. The lambda in Python and the arrow function in JavaScript are McCarthy's lambda.
- **Metaprogramming:** Lisp macros, which transform code as data before evaluation, are the most powerful macro system in wide use, and the idea of programs that manipulate programs runs through compilers, interpreters, and modern build tools.
- **Garbage collection and the REPL:** both now standard far beyond Lisp.
- **AI as a field:** McCarthy named it (Dartmouth, 1956), and Lisp was the language of AI research for thirty years, from SHRDLU to expert systems. He also founded the Stanford AI Lab (1965), formalized commonsense reasoning with the situation calculus (1963) and nonmonotonic logic via circumscription (1980), and proposed time-sharing, the idea that many users could share one machine, which fed into CTSS and Project MAC and, conceptually, into utility and cloud computing.

### 6. Lasting Impact

The deepest legacy is the idea that the boundary between program and data is artificial. Once eval exists, a program is a value you can build, inspect, transform, and run. That equivalence powers compilers (which treat programs as data to be rewritten), interpreters, macro systems, just-in-time compilers, and the entire practice of metaprogramming. It also reframed what a programming language *is*: not a fixed set of statements, but a small core plus an evaluator you can extend, even reimplement, in the language itself. When a modern system parses code into an abstract syntax tree, walks it with an evaluator, and lets user code generate more code at runtime, it is living inside McCarthy's 1960 design. The half-page of `eval` is still, sixty-five years later, the clearest statement of what it means to run a program.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Recursive Functions of Symbolic Expressions and Their Computation by Machine, Part I](https://doi.org/10.1145/367177.367199) | Communications of the ACM | 1960 |
| [A Proposal for the Dartmouth Summer Research Project on Artificial Intelligence](https://doi.org/10.1609/aimag.v27i4.1904) *(coined "artificial intelligence")* | reprinted in AI Magazine | 1955 |
| [Programs with Common Sense](https://www-formal.stanford.edu/jmc/mcc59.html) *(the Advice Taker)* | Mechanisation of Thought Processes | 1959 |
| [LISP 1.5 Programmer's Manual](https://mitpress.mit.edu/9780262130110/lisp-1-5-programmers-manual/) *(book)* | MIT Press | 1962 |
| [Situations, Actions, and Causal Laws](https://www-formal.stanford.edu/jmc/mcchay69.html) *(situation calculus; expanded with P. Hayes, 1969)* | Stanford AI Memo | 1963 |
| [Circumscription — A Form of Non-Monotonic Reasoning](https://doi.org/10.1016/0004-3702(80)90011-9) | Artificial Intelligence | 1980 |

---

*Previous: [Week 05 — James H. Wilkinson (1970)](../05-james-wilkinson-1970/)*
