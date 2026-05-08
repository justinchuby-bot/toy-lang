#!/usr/bin/env python3
"""
Bytecode Compiler for Toy Lang
===============================
Walks the AST produced by the parser and emits a flat list of bytecode
instructions for the stack-based VM.

Design decisions:
  - Instructions are simple (opcode, optional operand) tuples — no raw bytes,
    keeping it readable and educational.
  - Each function body is compiled into its own Chunk (list of instructions +
    constant pool).  The top-level program is also a Chunk.
  - Closures capture variables by reference via the VM's upvalue mechanism
    (see vm.py).
"""

from interpreter import (
    Number, String, BinOp, UnaryOp, Variable, Assign, Print,
    If, Block, FnDef, FnCall, Return,
    TT_PLUS, TT_MINUS, TT_MUL, TT_DIV,
    TT_EQ, TT_NEQ, TT_LT, TT_GT, TT_LTE, TT_GTE,
    Lexer, Parser,
)

# ── Opcodes ──────────────────────────────────────────────────────────────
# Each opcode is just a string for readability.  A production compiler would
# use integers, but strings make debugging and learning much easier.

OP_CONST       = 'CONST'        # Push constants[arg] onto stack
OP_ADD         = 'ADD'
OP_SUB         = 'SUB'
OP_MUL         = 'MUL'
OP_DIV         = 'DIV'
OP_NEG         = 'NEG'          # Unary minus
OP_EQ          = 'EQ'
OP_NEQ         = 'NEQ'
OP_LT          = 'LT'
OP_GT          = 'GT'
OP_LTE         = 'LTE'
OP_GTE         = 'GTE'
OP_LOAD        = 'LOAD'         # Push local variable slots[arg]
OP_STORE       = 'STORE'        # Pop top → local variable slots[arg]
OP_LOAD_GLOBAL = 'LOAD_GLOBAL'  # Push globals[name]
OP_STORE_GLOBAL= 'STORE_GLOBAL' # Pop top → globals[name]
OP_JUMP        = 'JUMP'         # Unconditional jump to arg
OP_JUMP_IF_FALSE = 'JUMP_IF_FALSE'  # Pop; jump if falsy
OP_CALL        = 'CALL'         # Call function with arg arguments
OP_RETURN      = 'RETURN'       # Return top of stack from current frame
OP_PRINT       = 'PRINT'        # Pop and print
OP_CLOSURE     = 'CLOSURE'      # Create closure from constants[arg]
OP_POP         = 'POP'          # Discard top of stack
OP_NONE        = 'NONE'         # Push None


class Chunk:
    """A compiled unit — holds instructions and a constant pool."""

    def __init__(self, name='<script>'):
        self.name = name
        self.code = []          # list of (opcode, operand|None)
        self.constants = []     # constant pool (numbers, strings, sub-Chunks)

    def emit(self, op, operand=None):
        idx = len(self.code)
        self.code.append((op, operand))
        return idx  # useful for patching jumps later

    def add_constant(self, value):
        self.constants.append(value)
        return len(self.constants) - 1

    def patch_jump(self, offset):
        """Patch a previously emitted jump to point to the current position."""
        self.code[offset] = (self.code[offset][0], len(self.code))

    # ── Pretty printer ───────────────────────────────────────────────────
    def disassemble(self, indent=0):
        pad = '  ' * indent
        lines = [f'{pad}=== {self.name} ===']
        for i, (op, arg) in enumerate(self.code):
            if arg is not None:
                if op == OP_CONST:
                    val = self.constants[arg]
                    if isinstance(val, Chunk):
                        lines.append(f'{pad}{i:4d}  {op:<18s} {arg}  (<fn {val.name}>)')
                    else:
                        lines.append(f'{pad}{i:4d}  {op:<18s} {arg}  ({val!r})')
                else:
                    lines.append(f'{pad}{i:4d}  {op:<18s} {arg}')
            else:
                lines.append(f'{pad}{i:4d}  {op}')
        # Recurse into sub-chunks
        for c in self.constants:
            if isinstance(c, Chunk):
                lines.append('')
                lines.extend(c.disassemble(indent + 1).split('\n'))
        return '\n'.join(lines)


class Local:
    """Tracks a local variable during compilation."""
    def __init__(self, name, depth):
        self.name = name
        self.depth = depth


class Compiler:
    """
    Walks the AST and emits bytecode into a Chunk.

    Variable resolution strategy (simplified):
      - Top-level (scope_depth == 0): use LOAD_GLOBAL / STORE_GLOBAL with
        the variable *name* as operand.
      - Inside functions (scope_depth > 0): allocate numbered local slots.
        Function parameters are the first locals.

    This keeps the global scope dynamic (like Python) while making function
    bodies efficient with indexed locals.
    """

    def __init__(self):
        self.chunk = Chunk()
        self.locals = []        # stack of Local
        self.scope_depth = 0

    def compile(self, source):
        """Compile source code string → Chunk."""
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        self._compile_node(ast)
        self.chunk.emit(OP_NONE)   # implicit return None
        self.chunk.emit(OP_RETURN)
        return self.chunk

    def compile_ast(self, ast):
        """Compile an already-parsed AST → Chunk."""
        self._compile_node(ast)
        self.chunk.emit(OP_NONE)
        self.chunk.emit(OP_RETURN)
        return self.chunk

    # ── Node dispatch ────────────────────────────────────────────────────

    def _compile_node(self, node):
        method = f'_compile_{type(node).__name__}'
        handler = getattr(self, method, None)
        if handler is None:
            raise RuntimeError(f"Compiler: unhandled node {type(node).__name__}")
        handler(node)

    # ── Literals ─────────────────────────────────────────────────────────

    def _compile_Number(self, node):
        idx = self.chunk.add_constant(node.value)
        self.chunk.emit(OP_CONST, idx)

    def _compile_String(self, node):
        idx = self.chunk.add_constant(node.value)
        self.chunk.emit(OP_CONST, idx)

    # ── Arithmetic / comparison ──────────────────────────────────────────

    _binop_map = {
        TT_PLUS: OP_ADD, TT_MINUS: OP_SUB,
        TT_MUL: OP_MUL, TT_DIV: OP_DIV,
        TT_EQ: OP_EQ, TT_NEQ: OP_NEQ,
        TT_LT: OP_LT, TT_GT: OP_GT,
        TT_LTE: OP_LTE, TT_GTE: OP_GTE,
    }

    def _compile_BinOp(self, node):
        self._compile_node(node.left)
        self._compile_node(node.right)
        self.chunk.emit(self._binop_map[node.op])

    def _compile_UnaryOp(self, node):
        self._compile_node(node.operand)
        if node.op == TT_MINUS:
            self.chunk.emit(OP_NEG)

    # ── Variables ────────────────────────────────────────────────────────

    def _resolve_local(self, name):
        """Search locals from top of stack downward; return slot index or -1."""
        for i in range(len(self.locals) - 1, -1, -1):
            if self.locals[i].name == name:
                return i
        return -1

    def _compile_Variable(self, node):
        slot = self._resolve_local(node.name)
        if slot != -1:
            self.chunk.emit(OP_LOAD, slot)
        else:
            # Fall back to global lookup by name
            idx = self.chunk.add_constant(node.name)
            self.chunk.emit(OP_LOAD_GLOBAL, idx)

    def _compile_Assign(self, node):
        self._compile_node(node.expr)
        slot = self._resolve_local(node.name)
        if slot != -1:
            self.chunk.emit(OP_STORE, slot)
        elif self.scope_depth > 0:
            # New local in a function scope
            self.locals.append(Local(node.name, self.scope_depth))
            slot = len(self.locals) - 1
            self.chunk.emit(OP_STORE, slot)
        else:
            idx = self.chunk.add_constant(node.name)
            self.chunk.emit(OP_STORE_GLOBAL, idx)

    # ── Print ────────────────────────────────────────────────────────────

    def _compile_Print(self, node):
        self._compile_node(node.expr)
        self.chunk.emit(OP_PRINT)

    # ── If / else ────────────────────────────────────────────────────────

    def _compile_If(self, node):
        # Compile condition
        self._compile_node(node.condition)
        # Jump over then-block if false
        jump_false = self.chunk.emit(OP_JUMP_IF_FALSE, 0)  # placeholder

        # Then block
        self._compile_node(node.then_block)

        if node.else_block:
            # Jump over else-block after then
            jump_end = self.chunk.emit(OP_JUMP, 0)  # placeholder
            self.chunk.patch_jump(jump_false)
            self._compile_node(node.else_block)
            self.chunk.patch_jump(jump_end)
        else:
            self.chunk.patch_jump(jump_false)

    # ── Blocks ───────────────────────────────────────────────────────────

    def _compile_Block(self, node):
        for stmt in node.statements:
            self._compile_node(stmt)

    # ── Functions ────────────────────────────────────────────────────────

    def _compile_FnDef(self, node):
        """
        Compile a function definition:
          1. Create a sub-Compiler for the function body.
          2. Parameters become the first local slots.
          3. The compiled Chunk is stored as a constant.
          4. Emit OP_CLOSURE to wrap it at runtime.
          5. If named, store the closure in the appropriate scope.
        """
        fn_compiler = Compiler()
        fn_compiler.scope_depth = self.scope_depth + 1
        fn_compiler.chunk = Chunk(name=node.name or '<anon>')

        # Parameters → first local slots
        for param in node.params:
            fn_compiler.locals.append(Local(param, fn_compiler.scope_depth))

        # Compile body
        fn_compiler._compile_node(node.body)

        # Implicit return None if body doesn't end with RETURN
        fn_compiler.chunk.emit(OP_NONE)
        fn_compiler.chunk.emit(OP_RETURN)

        # Store the compiled chunk and emit closure instruction
        fn_compiler.chunk.arity = len(node.params)
        idx = self.chunk.add_constant(fn_compiler.chunk)
        self.chunk.emit(OP_CLOSURE, idx)

        # Bind name
        if node.name:
            slot = self._resolve_local(node.name)
            if slot != -1:
                self.chunk.emit(OP_STORE, slot)
            elif self.scope_depth > 0:
                self.locals.append(Local(node.name, self.scope_depth))
                slot = len(self.locals) - 1
                self.chunk.emit(OP_STORE, slot)
            else:
                name_idx = self.chunk.add_constant(node.name)
                self.chunk.emit(OP_STORE_GLOBAL, name_idx)

    # ── Function calls ───────────────────────────────────────────────────

    def _compile_FnCall(self, node):
        # Push the function onto the stack
        self._compile_node(Variable(node.name))
        # Push each argument
        for arg in node.args:
            self._compile_node(arg)
        self.chunk.emit(OP_CALL, len(node.args))

    # ── Return ───────────────────────────────────────────────────────────

    def _compile_Return(self, node):
        self._compile_node(node.expr)
        self.chunk.emit(OP_RETURN)


# ── CLI: compile and disassemble ─────────────────────────────────────────

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python compiler.py <file.toy>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        source = f.read()
    compiler = Compiler()
    chunk = compiler.compile(source)
    print(chunk.disassemble())
