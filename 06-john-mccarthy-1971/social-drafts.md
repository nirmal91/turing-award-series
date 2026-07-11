# Week 06 — John McCarthy — social drafts

> Note: the LinkedIn opener and the Substack body are meant to be built from your
> My Take. My Take is still a placeholder, so these are stand-in drafts written
> from the contribution. Swap in the one or two most concrete lines from your My
> Take once you write it. Publish Substack first, then point LinkedIn ("Link in
> comments") and X at it.

---

## LinkedIn post

Week 06 of my learning series on Turing Award winners: John McCarthy built a language whose entire definition fits on one page, written in itself.

Before Lisp a program was a list of machine steps on numbers, and a function could not even call itself. McCarthy made code and data the same shape, just lists in parentheses, so a program could build and run another program. Then he wrote one function, eval, that reads any Lisp program and computes it. That function is the whole language, and you can write it in the language it defines.

The ideas leaked into everything. The if/else you wrote today is his conditional. Garbage collection cleaning up your memory is his. And code that writes and runs other code, the thing that makes an AI emitting a program even make sense, is the principle he made concrete in 1960.

Link in comments.

---

## X thread

**Tweet 1**
I keep falling down rabbit holes on the people who built the ground we stand on. Week 06 of my Turing Award series: John McCarthy, who wrote a whole programming language that fits on one page. [attach image]

**Tweet 2**
The series is an experiment. The code and the technical writeups are AI generated. One section each week is written by me, no AI, because writing is how I actually check that I understand something.

**Tweet 3**
Before Lisp, a function could not call itself and a program could not be treated as data. McCarthy made code and data the same thing: lists in parentheses. Then he wrote one function, eval, that runs any Lisp program. That function IS the language.

**Tweet 4**
You use his ideas every day. Every if/else descends from his conditional expression. Every time your phone frees memory on its own, that is his garbage collection. And code that generates and runs code, the whole premise of an LLM writing a program, is his 1960 insight.

**Tweet 5**
Code and full writeup: github.com/nirmal91/turing-award-series

---

## Image spec

Split image, dark background, monospace font. No headshots, no stock photos, no text labels.

- **Left side (before):** a block of FORTRAN-style factorial. All caps, line numbers, a mutable counter and a DO loop. It should look boxy, rigid, and mechanical.
  ```
        FACT = 1
        DO 10 I = 1, N
        FACT = FACT * I
     10 CONTINUE
  ```
- **Right side (after):** the Lisp factorial, a small nest of parentheses that reads like a definition of itself.
  ```
     (define (fact n)
       (if (= n 0)
           1
           (* n (fact (- n 1)))))
  ```
- The contrast to land: left is a machine grinding through a counter; right is a single self-referential sentence. Left looks like instructions carved for a machine, right looks like an idea. Same computation, and the eye should read right as lighter and more human without any label saying so.
- Optional accent: tint the recursive call `(fact ...)` on the right so the self-reference pops, since that is the thing FORTRAN could not do.

Expect two generations. On the first pass check: the parentheses balance, the FORTRAN column alignment reads as old/rigid, no decorative icons crept in, and there are no text labels.

---

## Substack post

**Title:** Week 06: John McCarthy, and the one-page language hiding inside every AI

**Subtitle:** How does a program become something another program can read, change, and run?

**Cover image:** the split FORTRAN / Lisp image above.

**Body:** *[Use your My Take verbatim once written. Do not rewrite it into a fresh essay.]*

**Tags:** Artificial Intelligence, Computer Science, Programming Languages, Lisp, History of Computing

**Link:** Code and the full writeup: github.com/nirmal91/turing-award-series
