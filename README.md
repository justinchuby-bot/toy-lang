# Toy Lang

A minimal interpreter for a toy programming language, built in Python for educational purposes.

## Architecture

```
Source Code → Lexer → Tokens → Parser → AST → Evaluator → Result
```

### Components (~350 lines total)

1. **Lexer** — Scans source text character-by-character, producing tokens (numbers, strings, identifiers, operators, keywords).

2. **Parser** — Recursive descent parser that builds an Abstract Syntax Tree. Why recursive descent? It maps 1:1 to the grammar rules, making it easy to read and extend. Each grammar rule is a method.

3. **AST Nodes** — Simple data classes: `Number`, `String`, `BinOp`, `UnaryOp`, `Variable`, `Assign`, `Print`, `If`, `Block`.

4. **Evaluator** — Tree-walking interpreter. Visits each AST node and computes the result. Uses an `Environment` for variable storage.

5. **REPL** — Interactive mode with persistent environment across lines.

## Scoping

The `Environment` class implements lexical scoping via a parent chain:
- Global scope has no parent
- `if` blocks create a child scope (can read parent vars, writes stay local)
- Variable lookup walks up the chain until found

## Language Features

```
# Variables
x = 42
name = "hello"

# Arithmetic with precedence
result = (2 + 3) * 4

# Comparisons
print x > 10

# Conditionals
if x > 0 {
    print "positive"
} else {
    print "non-positive"
}

# Comments start with #
```

## What's Intentionally Left Out

- **Loops** — Would add complexity; if/else demonstrates control flow
- **Functions** — Would need call stacks, closures, return values
- **Type system** — Runtime duck typing only
- **Error recovery** — Fails fast on first error
- **Multi-line REPL** — Single-line input only in interactive mode

These omissions keep the code short and focused on the core interpreter pattern.

## Usage

```bash
# REPL mode
python3 interpreter.py

# Run a file
python3 interpreter.py examples/hello.toy
```

## Running Examples

```bash
python3 interpreter.py examples/hello.toy
python3 interpreter.py examples/math.toy
python3 interpreter.py examples/conditionals.toy
```
