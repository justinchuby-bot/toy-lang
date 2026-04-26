# Toy Lang

A minimal interpreter for a toy programming language, built in Python for educational purposes.

## Architecture

```
Source Code → Lexer → Tokens → Parser → AST → Evaluator → Result
```

### Components (~500 lines total)

1. **Lexer** — Scans source text character-by-character, producing tokens (numbers, strings, identifiers, operators, keywords).

2. **Parser** — Recursive descent parser that builds an Abstract Syntax Tree. Each grammar rule maps to a method.

3. **AST Nodes** — Simple data classes: `Number`, `String`, `BinOp`, `UnaryOp`, `Variable`, `Assign`, `Print`, `If`, `Block`, `FnDef`, `FnCall`, `Return`.

4. **Evaluator** — Tree-walking interpreter with `Environment` for lexical scoping.

5. **REPL** — Interactive mode with readline history (up/down arrows) and multi-line input support.

## Language Features

### Variables & Arithmetic
```
x = 42
name = "hello"
result = (2 + 3) * 4
print x > 10
```

### Conditionals
```
if x > 0 {
    print "positive"
} else {
    print "non-positive"
}
```

### Functions

Inline (single-expression) functions:
```
fn add(a, b) = a + b
print add(3, 4)    # 7
```

Multi-line block functions with `return`:
```
fn factorial(n) {
    if n < 2 {
        return 1
    } else {
        return n * factorial(n - 1)
    }
}
print factorial(10)    # 3628800
```

Recursive fibonacci:
```
fn fib(n) {
    if n < 2 {
        return n
    } else {
        return fib(n - 1) + fib(n - 2)
    }
}
print fib(10)    # 55
```

### Closures

Functions capture their enclosing environment:
```
fn make_adder(x) {
    fn adder(y) = x + y
    return adder
}
plus5 = make_adder(5)
print plus5(3)    # 8
```

### Comments
```
# This is a comment
x = 42  # inline comments work too
```

## Scoping

The `Environment` class implements lexical scoping via a parent chain:
- Global scope has no parent
- `if` blocks create a child scope
- Function bodies run in a new scope with the closure's environment as parent
- This enables closures and recursion naturally

## REPL Features

- **Readline history** — Up/down arrows navigate command history, persisted to `~/.toy_lang_history`
- **Multi-line input** — Lines ending with `{` automatically continue until braces balance
- **Persistent environment** — Variables and functions persist across REPL lines

## Usage

```bash
# REPL mode
python3 interpreter.py

# Run a file
python3 interpreter.py program.toy
```

## What's Intentionally Left Out

- **Loops** — Would add complexity; recursion covers iteration
- **Type system** — Runtime duck typing only
- **Error recovery** — Fails fast on first error
- **First-class function expressions** — Functions must be named (no lambdas)

These omissions keep the code short and focused on the core interpreter pattern.
