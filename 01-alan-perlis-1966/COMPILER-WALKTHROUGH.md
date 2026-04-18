# `compiler.py` — pipeline walkthrough

This note is for readers who want a **detailed** tour of the mini compiler. The chapter [README](./README.md) stays high-level; open this file when you want the full story.

**Pipeline:** source text → tokens → AST → stack bytecode → execution (same idea as Perlis’s IT, without targeting the IBM 650).

---

## 1. Lexer (source → tokens)

The lexer scans the string and produces a flat list of `Token(type, value)`. Whitespace is skipped between matches.

**Example source:** `y = x * (2 + 4)`

| Order | Type     | Value |
|-------|----------|--------|
| 1     | `NAME`   | `y`   |
| 2     | `EQ`     | `=`   |
| 3     | `NAME`   | `x`   |
| 4     | `STAR`   | `*`   |
| 5     | `LPAREN` | `(`   |
| 6     | `NUM`    | `2`   |
| 7     | `PLUS`   | `+`   |
| 8     | `NUM`    | `4`   |
| 9     | `RPAREN` | `)`   |
| 10    | `EOF`    |       |

There is no tree yet—only typed tokens so the parser can distinguish names, operators, and punctuation.

---

## 2. Parser (tokens → AST) — recursive descent

The parser keeps a cursor (`pos`) on the token list (`peek` / `consume`). Each `parse_*` function either builds a **leaf** from the current token(s) or **calls** another `parse_*` for a smaller piece, then combines results. That mirrors the grammar in the docstring of `Parser` in `compiler.py`.

### How the AST is obtained from the tokens (same example)

Assume the input after tokenization is the list above.

1. **`parse_stmt`**  
   - `peek()` is `NAME` (`y`); the **next** token is `EQ` → this is an **assignment**.  
   - Consume `y`, consume `=`, call **`parse_expr()`** for the rest: `x * (2 + 4)`.

2. **`parse_expr()`** (RHS)  
   - Calls **`parse_term()`** once to parse a full term.  
   - Loops while the next token is `+` or `-` to extend with more terms.  
   - Here, after the full term `x * (2 + 4)`, the next token is `EOF`, so no extra `+`/`-` at this level.

3. **`parse_term()`** for `x * (2 + 4)`  
   - Calls **`parse_unary()`** → **`parse_primary()`** → sees `NAME` → **`VarNode("x")`**.  
   - Next token is `*`. The `while` in `parse_term` consumes `*` and calls **`parse_unary()`** again for the right operand.  
   - Right side: **`parse_primary()`** sees `(` → consume `(`, call **`parse_expr()`** for `2 + 4`, consume `)`.

4. **Inner `parse_expr()`** for `2 + 4`  
   - **`parse_term()`** → **`NumNode(2.0)`**.  
   - Next is `+` → consume `+`, **`parse_term()`** again → **`NumNode(4.0)`**.  
   - Builds **`BinOpNode("+", left=2, right=4)`**.

5. Back out: the right child of `*` is that `+` node → **`BinOpNode("*", VarNode("x"), BinOpNode("+", ...))`**.  
   - Wrapped in **`AssignNode("y", ...)`**.

**Resulting AST (conceptually):**

```text
AssignNode(
  "y",
  BinOpNode(
    "*",
    VarNode("x"),
    BinOpNode("+", NumNode(2.0), NumNode(4.0)),
  ),
)
```

Precedence (`*` tighter than `+`) and parentheses are **already** in the tree shape; no separate precedence table is needed after this point.

---

## 3. Infix, prefix, postfix (notation vs your bytecode)

| Notation | Where the operator sits | Same meaning as `2 + 3 * 4` |
|----------|-------------------------|-----------------------------|
| **Infix**  | Between operands        | `2 + 3 * 4`                 |
| **Prefix** (Polish) | Before operands | `+ 2 * 3 4`                 |
| **Postfix** (RPN)   | After operands  | `2 3 4 * +`                 |

**Postfix evaluation (classic stack algorithm):** scan left to right; push numbers; each binary operator pops the **right** operand then the **left**, applies `left op right`, pushes the result. No precedence rules at evaluation time—the order of tokens **is** the structure.

Your implementation does **not** parse postfix source. It **emits** instructions that behave like postfix: push values, then `ADD` / `MUL` / … combine the top of the stack. The VM is that stack evaluator.

**Prefix evaluation** is often described recursively: the first token is an operator; its operands are the **next complete sub-expressions** (or use a right-to-left stack scan). Postfix is usually easier for machines in one pass.

---

## 4. Compiler (AST → bytecode) — how “step 3” works

`compile_node` walks the AST and returns a **flat** `list[Instr]` in **execution order**.

- **`NumNode`** → `PUSH_CONST`  
- **`VarNode`** → `PUSH_VAR`  
- **`UnaryNode`** → compile operand, append `NEG`  
- **`BinOpNode`** → `compile(left) + compile(right) + [opcode]`  
  So the stack sees **left** pushed before **right**; the VM’s `ADD`/`SUB`/… pops **right** then **left** into `b, a` and computes `a op b`.  
- **`AssignNode`** → compile value, append `STORE(name)`

**Example:** `y = x * (2 + 4)`

```text
PUSH_VAR    x
PUSH_CONST  2
PUSH_CONST  4
ADD
MUL
STORE       y
```

The arithmetic part, in RPN words: load `x`, then `2`, then `4`, add, multiply—then store into `y`.

---

## 5. VM (bytecode → stack and variables)

Assume **`vars["x"] == 7`** before running this statement. `VM.run` clears the **stack** for this run but keeps **`vars`**.

| Step | Instruction    | Stack (bottom → top) | Notes        |
|------|----------------|----------------------|--------------|
| 1    | `PUSH_VAR x`   | `[7]`                |              |
| 2    | `PUSH_CONST 2` | `[7, 2]`             |              |
| 3    | `PUSH_CONST 4` | `[7, 2, 4]`          |              |
| 4    | `ADD`          | `[7, 6]`             | `2 + 4`      |
| 5    | `MUL`          | `[42]`               | `7 * 6`      |
| 6    | `STORE y`      | `[]`                 | `y ← 42`; `run` returns `None` for assignment |

So **`y` becomes 42**. In the REPL, an assignment line prints nothing; a later line **`y`** compiles to `PUSH_VAR y` and prints the value (as `int` when it is a whole number).

---

## 6. REPL and multi-statements

`run_statements` splits input on **semicolons or newlines**, strips empty pieces, and runs each piece on the **same** `VM`. Variables persist across lines. The **last** statement’s return value is what the REPL may print; assignments yield `None`.

---

## 7. Shorter examples (optional)

### `2 + 3 * 4` (precedence only)

- AST: `BinOpNode("+", NumNode(2), BinOpNode("*", NumNode(3), NumNode(4)))`  
- Bytecode: `PUSH_CONST 2`, `PUSH_CONST 3`, `PUSH_CONST 4`, `MUL`, `ADD`  
- Stack: `2`, then `3`, `4`, multiply → `12`, add to `2` → `14`.

### `-(3 + 2)` (unary minus)

- AST: `UnaryNode("-", BinOpNode("+", NumNode(3), NumNode(2)))`  
- Bytecode: `PUSH_CONST 3`, `PUSH_CONST 2`, `ADD`, `NEG`.

---

## 8. Where to look in the code

| Stage   | Location in `compiler.py`      |
|---------|------------------------------|
| Lexer   | `_TOKEN_RE`, `tokenize`      |
| Parser  | `Parser`, `parse`, `*Node`   |
| Compiler| `compile_node`, `compile_source` |
| VM      | `VM.run`                     |
| REPL    | `run_statements`, `repl`     |

Run **`python compiler.py --verbose`** to print bytecode for each statement while you type.
