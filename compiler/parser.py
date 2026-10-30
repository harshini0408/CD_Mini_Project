"""
LogicFlow Recursive-Descent Parser
Converts the token stream into an AST.

Grammar (EBNF):
  program          = { statement } EOF ;
  statement        = inputStatement
                   | printStatement
                   | assignment
                   | ifStatement
                   | repeatStatement ;
  inputStatement   = KW_ASK_FOR identifier NEWLINE ;
  assignment       = SET identifier TO expression NEWLINE ;
  printStatement   = PRINT expression NEWLINE ;
  ifStatement      = IF condition NEWLINE
                       block
                     [ ELSE NEWLINE block ]
                     KW_END_IF NEWLINE ;
  repeatStatement  = REPEAT expression TIMES NEWLINE
                       block
                     KW_END_REPEAT NEWLINE ;
  condition        = expression comparisonOp expression ;
  comparisonOp     = KW_IS_EQUAL_TO | KW_IS_NOT_EQUAL_TO
                   | KW_IS_GREATER_THAN | KW_IS_LESS_THAN
                   | KW_IS_GREATER_THAN_OR_EQUAL_TO
                   | KW_IS_LESS_THAN_OR_EQUAL_TO ;
  expression       = term { ('+' | '-') term } ;
  term             = factor { ('*' | '/' | '%') factor } ;
  factor           = NUMBER | STRING | identifier
                   | '(' expression ')' | '-' factor ;
  block            = { statement } ;
  identifier       = IDENTIFIER ;
"""

from .tokens import Token, TokenType
from .ast_nodes import (
    Program, InputStatement, PrintStatement, Assignment,
    NumberLiteral, StringLiteral, VariableReference,
    BinaryExpression, ComparisonExpression, IfStatement, RepeatStatement,
    ASTNode
)
from .errors import ParseError

_COMPARISON_TYPES = {
    TokenType.KW_IS_EQUAL_TO,
    TokenType.KW_IS_NOT_EQUAL_TO,
    TokenType.KW_IS_GREATER_THAN,
    TokenType.KW_IS_LESS_THAN,
    TokenType.KW_IS_GREATER_THAN_OR_EQUAL_TO,
    TokenType.KW_IS_LESS_THAN_OR_EQUAL_TO,
}


class Parser:
    def __init__(self, tokens: list[Token]):
        # Filter out COMMENT tokens; keep NEWLINEs
        self._tokens = [t for t in tokens if t.type != TokenType.COMMENT]
        self._pos = 0
        self._node_counter = 0
        self._errors: list[ParseError] = []

    @property
    def errors(self):
        return self._errors

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _peek(self, offset=1) -> Token:
        idx = self._pos + offset
        if idx < len(self._tokens):
            return self._tokens[idx]
        return self._tokens[-1]  # EOF

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
        return tok

    def _skip_newlines(self):
        while self._current().type == TokenType.NEWLINE:
            self._advance()

    def _expect(self, tok_type: TokenType, msg: str = None) -> Token:
        if self._current().type == tok_type:
            return self._advance()
        tok = self._current()
        err_msg = msg or f"Expected {tok_type.name} but got '{tok.value}' ({tok.type.name})"
        raise ParseError(err_msg, line=tok.line, column=tok.column)

    def _consume_newline(self):
        """Consume newline(s) or EOF."""
        if self._current().type in (TokenType.NEWLINE, TokenType.EOF):
            while self._current().type == TokenType.NEWLINE:
                self._advance()
        # If already at EOF, that's fine

    def _new_id(self) -> str:
        self._node_counter += 1
        return f"n{self._node_counter}"

    def _tag(self, node: ASTNode) -> ASTNode:
        node.node_id = self._new_id()
        return node

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def parse(self) -> Program:
        self._skip_newlines()
        body = []
        while self._current().type != TokenType.EOF:
            self._skip_newlines()
            if self._current().type == TokenType.EOF:
                break
            try:
                stmt = self._parse_statement()
                if stmt is not None:
                    body.append(stmt)
            except ParseError as e:
                self._errors.append(e)
                self._recover()
        prog = Program(body=body, line=1)
        prog.node_id = 'start'
        return prog

    def _recover(self):
        """Skip to the next newline to recover from a parse error."""
        while self._current().type not in (TokenType.NEWLINE, TokenType.EOF):
            self._advance()
        if self._current().type == TokenType.NEWLINE:
            self._advance()

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _parse_statement(self) -> ASTNode | None:
        tok = self._current()

        if tok.type == TokenType.NEWLINE:
            self._advance()
            return None

        if tok.type == TokenType.KW_ASK_FOR:
            return self._parse_input()

        if tok.type == TokenType.PRINT:
            return self._parse_print()

        if tok.type == TokenType.SET:
            return self._parse_assignment()

        if tok.type == TokenType.IF:
            return self._parse_if()

        if tok.type == TokenType.REPEAT:
            return self._parse_repeat()

        raise ParseError(
            f"Unexpected token '{tok.value}'. Expected a statement keyword (ASK FOR, PRINT, SET, IF, REPEAT).",
            line=tok.line, column=tok.column
        )

    def _parse_input(self) -> InputStatement:
        tok = self._advance()  # consume KW_ASK_FOR
        var_tok = self._expect(TokenType.IDENTIFIER, "Expected variable name after 'ASK FOR'")
        self._consume_newline()
        node = InputStatement(variable=var_tok.value, line=tok.line)
        return self._tag(node)

    def _parse_print(self) -> PrintStatement:
        tok = self._advance()  # consume PRINT
        expr = self._parse_expression()
        self._consume_newline()
        node = PrintStatement(expression=expr, line=tok.line)
        return self._tag(node)

    def _parse_assignment(self) -> Assignment:
        tok = self._advance()  # consume SET
        var_tok = self._expect(TokenType.IDENTIFIER, "Expected variable name after 'SET'")
        self._expect(TokenType.TO, "Expected 'TO' after variable name in assignment")
        expr = self._parse_expression()
        self._consume_newline()
        node = Assignment(variable=var_tok.value, expression=expr, line=tok.line)
        return self._tag(node)

    def _parse_if(self) -> IfStatement:
        tok = self._advance()  # consume IF
        condition = self._parse_condition()
        self._consume_newline()
        then_body = self._parse_block({TokenType.KW_END_IF, TokenType.ELSE})
        else_body = []
        if self._current().type == TokenType.ELSE:
            self._advance()  # consume ELSE
            self._consume_newline()
            else_body = self._parse_block({TokenType.KW_END_IF})
        self._expect(TokenType.KW_END_IF, "Expected 'END IF' to close IF block")
        self._consume_newline()
        node = IfStatement(condition=condition, then_body=then_body, else_body=else_body, line=tok.line)
        return self._tag(node)

    def _parse_repeat(self) -> RepeatStatement:
        tok = self._advance()  # consume REPEAT
        count_expr = self._parse_expression()
        self._expect(TokenType.TIMES, "Expected 'TIMES' after repeat count")
        self._consume_newline()
        body = self._parse_block({TokenType.KW_END_REPEAT})
        self._expect(TokenType.KW_END_REPEAT, "Expected 'END REPEAT' to close REPEAT block")
        self._consume_newline()
        node = RepeatStatement(count=count_expr, body=body, line=tok.line)
        return self._tag(node)

    # ------------------------------------------------------------------
    # Blocks
    # ------------------------------------------------------------------

    def _parse_block(self, terminators: set) -> list[ASTNode]:
        body = []
        while self._current().type not in terminators and self._current().type != TokenType.EOF:
            self._skip_newlines()
            if self._current().type in terminators or self._current().type == TokenType.EOF:
                break
            try:
                stmt = self._parse_statement()
                if stmt is not None:
                    body.append(stmt)
            except ParseError as e:
                self._errors.append(e)
                self._recover()
        return body

    # ------------------------------------------------------------------
    # Conditions
    # ------------------------------------------------------------------

    def _parse_condition(self) -> ComparisonExpression:
        left = self._parse_expression()
        if self._current().type not in _COMPARISON_TYPES:
            tok = self._current()
            raise ParseError(
                f"Expected comparison operator (IS EQUAL TO, IS GREATER THAN, etc.) but got '{tok.value}'",
                line=tok.line, column=tok.column
            )
        op_tok = self._advance()
        right = self._parse_expression()
        node = ComparisonExpression(operator=op_tok.value, left=left, right=right, line=op_tok.line)
        return self._tag(node)

    # ------------------------------------------------------------------
    # Expressions (recursive descent, handles precedence)
    # ------------------------------------------------------------------

    def _parse_expression(self) -> ASTNode:
        """expression = term { ('+' | '-') term }"""
        node = self._parse_term()
        while self._current().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._advance()
            right = self._parse_term()
            new_node = BinaryExpression(operator=op.value, left=node, right=right, line=op.line)
            self._tag(new_node)
            node = new_node
        return node

    def _parse_term(self) -> ASTNode:
        """term = factor { ('*' | '/' | '%') factor }"""
        node = self._parse_factor()
        while self._current().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self._advance()
            right = self._parse_factor()
            new_node = BinaryExpression(operator=op.value, left=node, right=right, line=op.line)
            self._tag(new_node)
            node = new_node
        return node

    def _parse_factor(self) -> ASTNode:
        """factor = NUMBER | STRING | identifier | '(' expression ')' | '-' factor"""
        tok = self._current()

        if tok.type == TokenType.NUMBER:
            self._advance()
            raw = tok.value
            val = float(raw) if '.' in raw else int(raw)
            node = NumberLiteral(value=val, line=tok.line)
            return self._tag(node)

        if tok.type == TokenType.STRING:
            self._advance()
            node = StringLiteral(value=tok.value, line=tok.line)
            return self._tag(node)

        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            node = VariableReference(name=tok.value, line=tok.line)
            return self._tag(node)

        if tok.type == TokenType.LPAREN:
            self._advance()  # consume '('
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN, "Expected ')' to close parenthesized expression")
            return expr

        if tok.type == TokenType.MINUS:
            self._advance()
            factor = self._parse_factor()
            zero = NumberLiteral(value=0, line=tok.line)
            self._tag(zero)
            node = BinaryExpression(operator='-', left=zero, right=factor, line=tok.line)
            return self._tag(node)

        raise ParseError(
            f"Unexpected token '{tok.value}' in expression. Expected a number, string, variable, or '('.",
            line=tok.line, column=tok.column
        )
