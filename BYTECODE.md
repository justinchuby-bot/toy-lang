# Bytecode Compiler & Stack-Based VM

A bytecode compiler and virtual machine for Toy Lang, added alongside the existing tree-walking interpreter.

## Quick Start

```bash
# Run with the tree-walking interpreter (original)
python3 interpreter.py examples/functions.toy

# Run with the bytecode VM
python3 vm.py examples/functions.toy

# Run with execution tracing (see every instruction)
python3 vm.py --trace examples/functions.toy

# Disassemble only (see the compiled bytecode)
python3 compiler.py examples/functions.toy
```

## The Instruction Set

| Opcode | Operand | Stack Effect | Description |
|--------|---------|-------------|-------------|
| `CONST` | index | → value | Push `constants[index]` onto stack |
| `NONE` | — | → None | Push None |
| `ADD` | — | a, b → a+b | Addition |
| `SUB` | — | a, b → a-b | Subtraction |
| `MUL` | — | a, b → a*b | Multiplication |
| `DIV` | — | a, b → a/b | Division |
| `NEG` | — | a → -a | Unary negate |
| `EQ` | — | a, b → a==b | Equality |
| `NEQ` | — | a, b → a!=b | Not equal |
| `LT` | — | a, b → a<b | Less than |
| `GT` | — | a, b → a>b | Greater than |
| `LTE` | — | a, b → a<=b | Less or equal |
| `GTE` | — | a, b → a>=b | Greater or equal |
| `LOAD` | slot | → value | Push local variable from slot |
| `STORE` | slot | value → value | Store top into local slot (keeps on stack) |
| `LOAD_GLOBAL` | index | → value | Push global by name (name in constants) |
| `STORE_GLOBAL` | index | value → value | Store to global by name |
| `JUMP` | target | — | Unconditional jump |
| `JUMP_IF_FALSE` | target | cond → | Pop; jump if falsy |
| `CALL` | argc | fn, args... → result | Call function with argc arguments |
| `RETURN` | — | value → | Return from current frame |
| `CLOSURE` | index | → closure | Create closure from compiled chunk |
| `PRINT` | — | value → | Pop and print |
| `POP` | — | value → | Discard top of stack |

## How Compilation Works (AST → Bytecode)

The compiler (`compiler.py`) walks the AST recursively and emits instructions into a `Chunk` — a flat list of `(opcode, operand)` tuples plus a constant pool.

**Key ideas:**

1. **Expressions compile naturally** — for `2 + 3 * 4`, the compiler emits:
   ```
   CONST 2    # push 2
   CONST 3    # push 3
   CONST 4    # push 4
   MUL        # 3 * 4 → 12
   ADD        # 2 + 12 → 14
   ```
   The parser already handles precedence, so the AST is `Add(2, Mul(3, 4))` and we just compile left, right, operator.

2. **If/else uses jump patching** — we emit a `JUMP_IF_FALSE` with a placeholder target, compile the then-block, then patch the jump to point past it. For else blocks, an additional `JUMP` skips over the else after the then-block completes.

3. **Functions become sub-Chunks** — each `fn` definition creates a new `Compiler` that emits into a new `Chunk`. That chunk is stored in the parent's constant pool and wrapped in a `CLOSURE` instruction at runtime.

4. **Variables use two strategies:**
   - Top-level: `LOAD_GLOBAL` / `STORE_GLOBAL` with the variable *name* — simple and dynamic.
   - Inside functions: indexed local slots (`LOAD 0`, `STORE 1`) — fast and stack-based. Parameters automatically become the first slots.

## How the VM Executes (Fetch-Decode-Execute Loop)

The VM (`vm.py`) is a classic stack machine:

```
while True:
    instruction = code[ip]    # FETCH
    ip += 1
    match instruction:        # DECODE
        case ADD: ...         # EXECUTE
```

**Key data structures:**
- **Operand stack** — all values live here. Arithmetic pops operands, pushes results.
- **Call frames** — each function call pushes a `CallFrame(closure, ip=0, bp=stack_pos)`. The base pointer (bp) lets us address local variables relative to the frame.
- **Globals dict** — top-level variables stored by name.

**Function calls work like this:**
1. Push the function onto the stack
2. Push each argument
3. `CALL n` creates a new frame where bp points at the first argument
4. The function body executes, using `LOAD 0`, `LOAD 1` to access params
5. `RETURN` pops the frame, cleans up the stack, pushes the result

## Tree-Walking vs Bytecode: What I Learned

| Aspect | Tree-Walking (`evaluate()`) | Bytecode VM |
|--------|---------------------------|-------------|
| **Speed** | Slow — traverses AST nodes, creates Python objects per visit | Faster — flat array of instructions, simple loop |
| **Simplicity** | Very easy to write (~80 lines) | More code (~350 lines for compiler + VM) |
| **Debugging** | Hard to see what's happening | `--trace` flag shows every instruction |
| **Function calls** | Python call stack (recursive `evaluate()`) | Explicit call frames — you control the stack |
| **Variables** | Chained `Environment` dicts with parent pointers | Indexed slots (locals) or a single dict (globals) |
| **Control flow** | Python's own `if` statements | Jump instructions with patched targets |

**The big insight:** Tree-walking mixes *what to compute* with *how to compute it* — the AST is both the program representation and the execution engine. Bytecode separates these: the compiler figures out *what*, and the VM provides a simple, uniform *how*.

This is why real languages (Python, Lua, Ruby, Java) all compile to bytecode — the VM loop is cache-friendly, predictable, and easy to optimize. The tree-walker is great for prototyping but hits a wall when you want performance or features like coroutines and debuggers.

## File Overview

| File | Purpose |
|------|---------|
| `interpreter.py` | Lexer + Parser + Tree-walking evaluator (original) |
| `compiler.py` | AST → Bytecode compiler |
| `vm.py` | Stack-based VM that executes bytecode |
| `BYTECODE.md` | This file |
