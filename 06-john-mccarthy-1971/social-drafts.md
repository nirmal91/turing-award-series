# Week 06 — John McCarthy — social drafts

These are drafts. The LinkedIn opener should pull a line or two from your My Take
once you write it. For now it leads with the contribution.

---

## LinkedIn post

Week 06 of my learning series on Turing Award winners: John McCarthy.

In 1958 he built Lisp. The part that still gets me is that a program and the data it works on are the same thing. A list of numbers and a list that means "multiply these numbers" have the exact same shape. So you can build a program while your code is running and then run it.

McCarthy proved the point by writing the Lisp interpreter in Lisp, in about a page. Alan Kay called that page the Maxwell's equations of software. McCarthy also coined the term artificial intelligence back in 1955. And garbage collection, the thing that quietly frees memory in Python and Java today, was his too.

Most of how we program now traces back to one idea. Code is data.

Link in comments.

---

## X thread

**Tweet 1** (attach the split image)
I miss learning for its own sake, so I read one Turing Award winner a week and write it up. Week 6 is John McCarthy, the man who made code and data the same thing.

**Tweet 2**
Most of each writeup is automated. The code, the explanations, the history. One section every week is written by me with no AI. Writing is how I check that I actually understand something.

**Tweet 3**
In 1958 McCarthy built Lisp. A program is a list. Data is a list. Same shape. So you can build a program while your code runs, then hand it back to the interpreter and run it. He boiled the whole language down to seven tiny operations.

**Tweet 4**
That one idea is everywhere now. Python and JavaScript have his lambda. Java and Go reclaim memory with the garbage collection he invented. He also coined the term artificial intelligence in 1955, the phrase every Mag 7 earnings call now leans on.

**Tweet 5**
github.com/nirmal91/turing-award-series

---

## Image spec

Split image. Dark background (near black, #0d0d0d). Monospace font (something like
JetBrains Mono or IBM Plex Mono). No text labels, no headings, no headshots, no
logos. The two sides must read as old/painful on the left and clean/alive on the
right purely from the code.

**Left side — before Lisp (Fortran-era numeric code, factorial the hard way).**
Show boxy, line-numbered imperative code in a dim gray-green. Fixed memory, an
explicit loop, a GOTO, no recursion. Something like:

```
10    INTEGER N, F, I
20    F = 1
30    DO 50 I = 1, N
40    F = F * I
50    CONTINUE
60    IF (F) 70, 70, 80
70    STOP
80    WRITE (6, *) F
```

It should feel rigid: numbers in fixed slots, control by line number, the program
clearly a different kind of object from the data.

**Right side — after Lisp (recursion, and code that is data).**
Brighter, warmer (soft cyan/amber on the dark background). Show the recursive
definition and, underneath, the same list shown first as data and then run as a
program. Parentheses aligned, airy:

```
(define (fact n)
  (if (= n 0) 1 (* n (fact (- n 1)))))

(fact 5)                  => 120

(cons '* (cons 6 (cons 7 '())))   => (* 6 7)     ; data
(eval '(* 6 7))                   => 42          ; same list, run as code
```

The contrast to land: left is a machine following slots and jumps; right is a
function calling itself, and a list that is data on one line and a running program
on the next. Left = boxed in, right = open. No words needed.
