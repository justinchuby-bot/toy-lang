#!/usr/bin/env python3
"""
Toy Language Interpreter
========================
A minimal interpreter demonstrating: lexing → parsing → AST → evaluation.
Educational focus: clarity over cleverness.
"""

# ============================================================
# TOKENS
# ============================================================

class Token:
    """A lexical token with a type and optional value."""
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"

# Token types
TT_NUMBER   = 'NUMBER'
TT_STRING   = 'STRING'
TT_IDENT    = 'IDENT'
TT_PLUS     = 'PLUS'
TT_MINUS    = 'MINUS'
TT_MUL      = 'MUL'
TT_DIV      = 'DIV'
TT_ASSIGN   = 'ASSIGN'    # =
TT_EQ       = 'EQ'        # ==
TT_NEQ      = 'NEQ'       # !=
TT_LT       = 'LT'        # <
TT_GT       = 'GT'        # >
TT_LPAREN   = 'LPAREN'
TT_RPAREN   = 'RPAREN'
TT_LBRACE   = 'LBRACE'
TT_RBRACE   = 'RBRACE'
TT_IF       = 'IF'
TT_ELSE     = 'ELSE'
TT_PRINT    = 'PRINT'
TT_NEWLINE  = 'NEWLINE'
TT_EOF      = 'EOF'

KEYWORDS = {'if': TT_IF, 'else': TT_ELSE, 'print': TT_PRINT}

# ============================================================
# LEXER
# ============================================================

class Lexer:
    """Converts source text into a stream of tokens."""

    def __init__(self, text):
        self.text = text
        self.pos = 0

    def _current(self):
        return self.text[self.pos] if self.pos < len(self.text) else None

    def _advance(self):
        self.pos += 1

    def tokenize(self):
        tokens = []
        while self.pos < len(self.text):
            ch = self._current()

            # Skip spaces/tabs (but not newlines)
            if ch in ' \t':
                self._advance()

            # Newlines as statement separators
            elif ch == '\n':
                tokens.append(Token(TT_NEWLINE))
                self._advance()

            # Comments: # until end of line
            elif ch == '#':
                while self._current() and self._current() != '\n':
                    self._advance()

            # Numbers (integers and floats)
            elif ch.isdigit():
                tokens.append(self._read_number())

            # Strings (double-quoted)
            elif ch == '"':
                tokens.append(self._read_string())

            # Identifiers and keywords
            elif ch.isalpha() or ch == '_':
                tokens.append(self._read_ident())

            # Two-character operators
            elif ch == '=' and self._peek() == '=':
                tokens.append(Token(TT_EQ)); self._advance(); self._advance()
            elif ch == '!' and self._peek() == '=':
                tokens.append(Token(TT_NEQ)); self._advance(); self._advance()

            # Single-character tokens
            elif ch == '=': tokens.append(Token(TT_ASSIGN)); self._advance()
            elif ch == '+': tokens.append(Token(TT_PLUS)); self._advance()
            elif ch == '-': tokens.append(Token(TT_MINUS)); self._advance()
            elif ch == '*': tokens.append(Token(TT_MUL)); self._advance()
            elif ch == '/': tokens.append(Token(TT_DIV)); self._advance()
            elif ch == '<': tokens.append(Token(TT_LT)); self._advance()
            elif ch == '>': tokens.append(Token(TT_GT)); self._advance()
            elif ch == '(': tokens.append(Token(TT_LPAREN)); self._advance()
            elif ch == ')': tokens.append(Token(TT_RPAREN)); self._advance()
            elif ch == '{': tokens.append(Token(TT_LBRACE)); self._advance()
            elif ch == '}': tokens.append(Token(TT_RBRACE)); self._advance()

            else:
                raise SyntaxError(f"Unexpected character: {ch!r} at position {self.pos}")

        tokens.append(Token(TT_EOF))
        return tokens

    def _peek(self):
        p = self.pos + 1
        return self.text[p] if p < len(self.text) else None

    def _read_number(self):
        start = self.pos
        while self._current() and (self._current().isdigit() or self._current() == '.'):
            self._advance()
        text = self.text[start:self.pos]
        return Token(TT_NUMBER, float(text) if '.' in text else int(text))

    def _read_string(self):
        self._advance()  # skip opening "
        start = self.pos
        while self._current() and self._current() != '"':
            self._advance()
        if self._current() != '"':
            raise SyntaxError("Unterminated string")
        value = self.text[start:self.pos]
        self._advance()  # skip closing "
        return Token(TT_STRING, value)

    def _read_ident(self):
        start = self.pos
        while self._current() and (self._current().isalnum() or self._current() == '_'):
            self._advance()
        word = self.text[start:self.pos]
        tt = KEYWORDS.get(word, TT_IDENT)
        return Token(tt, word)


# ============================================================
# AST NODES
# ============================================================

class Number:
    def __init__(self, value): self.value = value
    def __repr__(self): return f"Number({self.value})"

class String:
    def __init__(self, value): self.value = value
    def __repr__(self): return f"String({self.value!r})"

class BinOp:
    def __init__(self, left, op, right):
        self.left = left; self.op = op; self.right = right
    def __repr__(self): return f"BinOp({self.left} {self.op} {self.right})"

class UnaryOp:
    def __init__(self, op, operand):
        self.op = op; self.operand = operand

class Variable:
    def __init__(self, name): self.name = name

class Assign:
    def __init__(self, name, expr):
        self.name = name; self.expr = expr

class Print:
    def __init__(self, expr): self.expr = expr

class If:
    def __init__(self, condition, then_block, else_block=None):
        self.condition = condition
        self.then_block = then_block
        self.else_block = else_block

class Block:
    def __init__(self, statements): self.statements = statements


# ============================================================
# PARSER (Recursive Descent)
# ============================================================

class Parser:
    """
    Grammar (simplified):
        program    → statement*
        statement  → print_stmt | if_stmt | assign_stmt | expr
        print_stmt → 'print' expr
        if_stmt    → 'if' expr '{' block '}' ('else' '{' block '}')?
        assign_stmt→ IDENT '=' expr
        expr       → comparison
        comparison → addition (('==' | '!=' | '<' | '>') addition)*
        addition   → multiply (('+' | '-') multiply)*
        multiply   → unary (('*' | '/') unary)*
        unary      → ('-') unary | atom
        atom       → NUMBER | STRING | IDENT | '(' expr ')'
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def _current(self):
        return self.tokens[self.pos]

    def _eat(self, tt):
        tok = self._current()
        if tok.type != tt:
            raise SyntaxError(f"Expected {tt}, got {tok.type}")
        self.pos += 1
        return tok

    def _match(self, *types):
        if self._current().type in types:
            tok = self._current()
            self.pos += 1
            return tok
        return None

    def _skip_newlines(self):
        while self._current().type == TT_NEWLINE:
            self.pos += 1

    def parse(self):
        """Parse the full program into a Block of statements."""
        stmts = []
        self._skip_newlines()
        while self._current().type != TT_EOF:
            stmts.append(self._statement())
            self._skip_newlines()
        return Block(stmts)

    def _statement(self):
        tok = self._current()

        if tok.type == TT_PRINT:
            return self._print_stmt()
        elif tok.type == TT_IF:
            return self._if_stmt()
        # Look ahead for assignment: IDENT '='
        elif tok.type == TT_IDENT and self.pos + 1 < len(self.tokens) \
                and self.tokens[self.pos + 1].type == TT_ASSIGN:
            return self._assign_stmt()
        else:
            return self._expr()

    def _print_stmt(self):
        self._eat(TT_PRINT)
        expr = self._expr()
        return Print(expr)

    def _if_stmt(self):
        self._eat(TT_IF)
        condition = self._expr()
        self._skip_newlines()
        self._eat(TT_LBRACE)
        then_block = self._block()
        self._eat(TT_RBRACE)
        self._skip_newlines()
        else_block = None
        if self._current().type == TT_ELSE:
            self._eat(TT_ELSE)
            self._skip_newlines()
            self._eat(TT_LBRACE)
            else_block = self._block()
            self._eat(TT_RBRACE)
        return If(condition, then_block, else_block)

    def _block(self):
        stmts = []
        self._skip_newlines()
        while self._current().type not in (TT_RBRACE, TT_EOF):
            stmts.append(self._statement())
            self._skip_newlines()
        return Block(stmts)

    def _assign_stmt(self):
        name = self._eat(TT_IDENT).value
        self._eat(TT_ASSIGN)
        expr = self._expr()
        return Assign(name, expr)

    def _expr(self):
        return self._comparison()

    def _comparison(self):
        left = self._addition()
        while tok := self._match(TT_EQ, TT_NEQ, TT_LT, TT_GT):
            right = self._addition()
            left = BinOp(left, tok.type, right)
        return left

    def _addition(self):
        left = self._multiply()
        while tok := self._match(TT_PLUS, TT_MINUS):
            right = self._multiply()
            left = BinOp(left, tok.type, right)
        return left

    def _multiply(self):
        left = self._unary()
        while tok := self._match(TT_MUL, TT_DIV):
            right = self._unary()
            left = BinOp(left, tok.type, right)
        return left

    def _unary(self):
        if tok := self._match(TT_MINUS):
            return UnaryOp(TT_MINUS, self._unary())
        return self._atom()

    def _atom(self):
        tok = self._current()
        if tok.type == TT_NUMBER:
            self.pos += 1
            return Number(tok.value)
        elif tok.type == TT_STRING:
            self.pos += 1
            return String(tok.value)
        elif tok.type == TT_IDENT:
            self.pos += 1
            return Variable(tok.value)
        elif tok.type == TT_LPAREN:
            self.pos += 1
            expr = self._expr()
            self._eat(TT_RPAREN)
            return expr
        else:
            raise SyntaxError(f"Unexpected token: {tok}")


# ============================================================
# EVALUATOR (Tree-Walking Interpreter)
# ============================================================

class Environment:
    """
    Variable scope. Each environment has an optional parent for lexical scoping.
    Variable lookup walks up the chain; assignment creates in current scope.
    """
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"Undefined variable: {name}")

    def set(self, name, value):
        self.vars[name] = value


def evaluate(node, env):
    """Recursively evaluate an AST node in the given environment."""

    if isinstance(node, Number):
        return node.value

    elif isinstance(node, String):
        return node.value

    elif isinstance(node, Variable):
        return env.get(node.name)

    elif isinstance(node, BinOp):
        left = evaluate(node.left, env)
        right = evaluate(node.right, env)
        ops = {
            TT_PLUS: lambda a, b: a + b,
            TT_MINUS: lambda a, b: a - b,
            TT_MUL: lambda a, b: a * b,
            TT_DIV: lambda a, b: a / b,
            TT_EQ: lambda a, b: a == b,
            TT_NEQ: lambda a, b: a != b,
            TT_LT: lambda a, b: a < b,
            TT_GT: lambda a, b: a > b,
        }
        return ops[node.op](left, right)

    elif isinstance(node, UnaryOp):
        operand = evaluate(node.operand, env)
        if node.op == TT_MINUS:
            return -operand

    elif isinstance(node, Assign):
        value = evaluate(node.expr, env)
        env.set(node.name, value)
        return value

    elif isinstance(node, Print):
        value = evaluate(node.expr, env)
        print(value)
        return value

    elif isinstance(node, If):
        condition = evaluate(node.condition, env)
        # Truthy: anything except 0, False, empty string
        if condition:
            return evaluate(node.then_block, Environment(parent=env))
        elif node.else_block:
            return evaluate(node.else_block, Environment(parent=env))
        return None

    elif isinstance(node, Block):
        result = None
        for stmt in node.statements:
            result = evaluate(stmt, env)
        return result

    else:
        raise RuntimeError(f"Unknown node type: {type(node).__name__}")


# ============================================================
# RUN & REPL
# ============================================================

def run(source, env=None):
    """Lex, parse, and evaluate a source string."""
    if env is None:
        env = Environment()
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    return evaluate(ast, env)


def repl():
    """Interactive Read-Eval-Print Loop."""
    print("Toy Lang REPL (type 'quit' to exit)")
    env = Environment()
    while True:
        try:
            line = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if line.strip() == 'quit':
            break
        if not line.strip():
            continue
        try:
            result = run(line, env)
            if result is not None:
                print(result)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        # Run a file
        with open(sys.argv[1]) as f:
            run(f.read())
    else:
        repl()
