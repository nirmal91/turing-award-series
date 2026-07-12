; scratch.lisp — Nirmal's from-scratch Lisp file.
; Run with:  python3 implementation.py scratch.lisp
;
; A Lisp file is just expressions, evaluated top to bottom.
; No main(), no class, no imports. Each form below runs in order.

; a bare number is already a program: it evaluates to itself
42

; arithmetic — the operator comes first
(+ 10 5)

; name a value so you can reuse it
(define pi 3)

; now use that name
(* pi 2)

; define a function (a lambda), give it the name inc
(define inc (lambda (n) (+ n 1)))

; call it
(inc 41)
