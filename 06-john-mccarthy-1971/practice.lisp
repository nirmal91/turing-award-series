; practice.lisp — scratch file for writing Lisp by hand.
; Anything after a semicolon is a comment (ignored).
; Run it with:   python3 implementation.py practice.lisp
;
; Rules of the syntax:
;   - every form is a list in parentheses: (operator arg1 arg2 ...)
;   - the operator comes FIRST (prefix), so 6 * 7 is written (* 6 7)
;   - whitespace and newlines don't matter; only the parentheses do
;   - parentheses must balance: every ( needs a matching )

; 1. multiply 6 by 7
(* 6 7)

; 2. the second element of (x y z): car of the cdr
(car (cdr (quote (x y z))))

; 3. build (a b c) by consing a onto (b c)
(cons (quote a) (quote (b c)))
