#!/usr/bin/env python3
"""
Stack-Based Virtual Machine for Toy Lang
==========================================
Executes bytecode produced by compiler.py using the classic
fetch-decode-execute loop.

Architecture:
  - Operand stack: values are pushed/popped for every operation.
  - Call frames: each function call creates a new CallFrame with its own
    instruction pointer (ip) and base pointer (bp) into the shared stack.
  - Globals: a dict keyed by variable name (for top-level scope).
  - Locals: stored on the operand stack itself, addressed as bp + slot.

This is the same architecture used by CPython, Lua, and (with typed stacks)
the JVM — just drastically simplified for learning.
"""

from compiler import (
    Chunk, Compiler,
    OP_CONST, OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_NEG,
    OP_EQ, OP_NEQ, OP_LT, OP_GT, OP_LTE, OP_GTE,
    OP_LOAD, OP_STORE,
    OP_LOAD_GLOBAL, OP_STORE_GLOBAL,
    OP_JUMP, OP_JUMP_IF_FALSE,
    OP_CALL, OP_RETURN,
    OP_PRINT, OP_CLOSURE, OP_POP, OP_NONE,
)


class VMClosure:
    """Runtime representation of a function — a Chunk + captured environment."""
    def __init__(self, chunk):
        self.chunk = chunk
        self.arity = getattr(chunk, 'arity', 0)

    def __repr__(self):
        return f'<fn {self.chunk.name}>'


class CallFrame:
    """
    One activation record on the call stack.

    Fields:
      closure  – the VMClosure being executed
      ip       – instruction pointer (index into closure.chunk.code)
      bp       – base pointer: index into VM.stack where this frame's
                 locals begin.  Slot 0 is the closure itself, then params.
    """
    def __init__(self, closure, bp):
        self.closure = closure
        self.ip = 0
        self.bp = bp


class VMError(RuntimeError):
    pass


class VM:
    """
    The virtual machine.  Call vm.run(chunk) to execute compiled bytecode.

    Tracing:
      Pass trace=True to print every instruction as it executes — very
      useful for understanding the fetch-decode-execute loop.
    """

    MAX_FRAMES = 256
    MAX_STACK  = 1024

    def __init__(self, trace=False):
        self.stack = []
        self.frames = []
        self.globals = {}
        self.trace = trace

    # ── Public API ───────────────────────────────────────────────────────

    def run(self, chunk):
        """Execute a top-level Chunk."""
        # Wrap top-level code in a closure and push the first call frame
        top = VMClosure(chunk)
        self.stack.append(top)
        self.frames.append(CallFrame(top, bp=0))
        return self._execute()

    # ── Core loop ────────────────────────────────────────────────────────

    def _execute(self):
        """
        The fetch-decode-execute loop.

        This is the heart of any bytecode VM:
          1. FETCH  – read the instruction at the current ip
          2. DECODE – look at the opcode to decide what to do
          3. EXECUTE – perform the operation (push/pop/jump/etc.)
          4. Advance ip and repeat
        """
        while True:
            frame = self.frames[-1]
            chunk = frame.closure.chunk
            ip = frame.ip

            # ── FETCH ────────────────────────────────────────────────────
            if ip >= len(chunk.code):
                # Ran off the end — treat as implicit return None
                return None

            op, arg = chunk.code[ip]
            frame.ip += 1

            # ── TRACE (optional) ─────────────────────────────────────────
            if self.trace:
                stack_preview = self.stack[frame.bp:]
                print(f"  [{chunk.name}:{ip:3d}] {op:<18s} "
                      f"{arg if arg is not None else '':>4}  "
                      f"stack={stack_preview}")

            # ── DECODE + EXECUTE ─────────────────────────────────────────

            # -- Constants & literals --
            if op == OP_CONST:
                self.stack.append(chunk.constants[arg])

            elif op == OP_NONE:
                self.stack.append(None)

            # -- Arithmetic --
            elif op == OP_ADD:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a + b)

            elif op == OP_SUB:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a - b)

            elif op == OP_MUL:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a * b)

            elif op == OP_DIV:
                b, a = self.stack.pop(), self.stack.pop()
                if b == 0:
                    raise VMError("Division by zero")
                self.stack.append(a / b)

            elif op == OP_NEG:
                self.stack.append(-self.stack.pop())

            # -- Comparison --
            elif op == OP_EQ:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a == b)

            elif op == OP_NEQ:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a != b)

            elif op == OP_LT:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a < b)

            elif op == OP_GT:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a > b)

            elif op == OP_LTE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a <= b)

            elif op == OP_GTE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a >= b)

            # -- Local variables --
            elif op == OP_LOAD:
                self.stack.append(self.stack[frame.bp + arg])

            elif op == OP_STORE:
                value = self.stack[-1]  # peek, don't pop (assignment is an expression)
                slot = frame.bp + arg
                # Extend stack if needed (new local)
                while len(self.stack) <= slot:
                    self.stack.append(None)
                self.stack[slot] = value

            # -- Global variables --
            elif op == OP_LOAD_GLOBAL:
                name = chunk.constants[arg]
                if name not in self.globals:
                    raise VMError(f"Undefined variable: {name}")
                self.stack.append(self.globals[name])

            elif op == OP_STORE_GLOBAL:
                name = chunk.constants[arg]
                self.stack[-1]  # peek — value stays on stack
                self.globals[name] = self.stack[-1]

            # -- Control flow --
            elif op == OP_JUMP:
                frame.ip = arg

            elif op == OP_JUMP_IF_FALSE:
                condition = self.stack.pop()
                if not condition:
                    frame.ip = arg

            # -- Functions --
            elif op == OP_CLOSURE:
                fn_chunk = chunk.constants[arg]
                closure = VMClosure(fn_chunk)
                self.stack.append(closure)

            elif op == OP_CALL:
                argc = arg
                # The function sits below the arguments on the stack
                fn = self.stack[-(argc + 1)]
                if not isinstance(fn, VMClosure):
                    raise VMError(f"Cannot call {fn!r} — not a function")
                if fn.arity != argc:
                    raise VMError(
                        f"{fn.chunk.name}() expects {fn.arity} args, got {argc}")
                # Create new call frame; bp points to the function's slot
                new_frame = CallFrame(fn, bp=len(self.stack) - argc)
                if len(self.frames) >= self.MAX_FRAMES:
                    raise VMError("Stack overflow: too many nested calls")
                self.frames.append(new_frame)

            elif op == OP_RETURN:
                result = self.stack.pop()
                # Pop everything this frame pushed (including locals)
                returning_frame = self.frames.pop()
                # Discard the frame's stack window + the function slot
                del self.stack[returning_frame.bp - 1:]
                if not self.frames:
                    # Returning from top-level — we're done
                    return result
                self.stack.append(result)

            # -- I/O --
            elif op == OP_PRINT:
                value = self.stack.pop()
                print(value)

            elif op == OP_POP:
                self.stack.pop()

            else:
                raise VMError(f"Unknown opcode: {op}")

            # Safety check
            if len(self.stack) > self.MAX_STACK:
                raise VMError("Stack overflow")


# ── Convenience: compile + run ───────────────────────────────────────────

def run_bytecode(source, trace=False):
    """Compile source and execute via the VM.  Returns the final value."""
    compiler = Compiler()
    chunk = compiler.compile(source)
    vm = VM(trace=trace)
    return vm.run(chunk)


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    trace = '--trace' in sys.argv
    files = [a for a in sys.argv[1:] if a != '--trace']

    if not files:
        # REPL mode
        print("Toy Lang VM REPL (type 'quit' to exit, '--trace' to toggle tracing)")
        vm = VM(trace=trace)
        while True:
            try:
                line = input("vm> ")
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break
            if line.strip() == 'quit':
                break
            if line.strip() == '--trace':
                vm.trace = not vm.trace
                print(f"Trace {'ON' if vm.trace else 'OFF'}")
                continue
            if not line.strip():
                continue
            # Multi-line support
            if line.rstrip().endswith('{'):
                depth = line.count('{') - line.count('}')
                while depth > 0:
                    try:
                        cont = input("... ")
                    except (EOFError, KeyboardInterrupt):
                        print("\nBye!")
                        sys.exit(0)
                    line += '\n' + cont
                    depth += cont.count('{') - cont.count('}')
            try:
                compiler = Compiler()
                chunk = compiler.compile(line)
                result = vm.run(chunk)
                if result is not None:
                    print(result)
            except Exception as e:
                print(f"Error: {e}")
    else:
        with open(files[0]) as f:
            source = f.read()
        run_bytecode(source, trace=trace)
