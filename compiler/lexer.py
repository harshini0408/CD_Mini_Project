"""
LogicFlow Lexer
Handwritten lexer that converts source text into a token stream.
Handles multi-word keywords, string literals, numbers, comments, and operators.
"""
import re
from .tokens import Token, TokenType
from .errors import LexerError

# Single-word keyword mapping
KEYWORDS = {
    'ASK': TokenType.ASK,
    'FOR': TokenType.FOR,
    'PRINT': TokenType.PRINT,
    'SET': TokenType.SET,
    'TO': TokenType.TO,
    'IF': TokenType.IF,
    'ELSE': TokenType.ELSE,
    'END': TokenType.END,
    'REPEAT': TokenType.REPEAT,
    'TIMES': TokenType.TIMES,
    'IS': TokenType.IS,
    'NOT': TokenType.NOT,
    'GREATER': TokenType.GREATER,
    'LESS': TokenType.LESS,
    'THAN': TokenType.THAN,
    'EQUAL': TokenType.EQUAL,
    'OR': TokenType.OR,
    'AND': TokenType.AND,
}

# Operator characters
OPERATORS = {
    '+': TokenType.PLUS,
    '-': TokenType.MINUS,
    '*': TokenType.STAR,
    '/': TokenType.SLASH,
    '%': TokenType.PERCENT,
    '(': TokenType.LPAREN,
    ')': TokenType.RPAREN,
}


class Lexer:
    """
    Tokenizes LogicFlow source code.
    After calling tokenize(), call get_tokens() to retrieve the flat
    token list. Multi-word comparison keywords are assembled in a
    second pass using _combine_multiword().
    """

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self._tokens: list[Token] = []
        self._errors: list[LexerError] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        """Return the full token list including EOF."""
        self._scan_all()
        self._tokens = self._combine_multiword(self._tokens)
        self._tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self._tokens

    @property
    def errors(self):
        return self._errors

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def _scan_all(self):
        while self.pos < len(self.source):
            ch = self.source[self.pos]

            # Comment
            if ch == '#':
                self._read_comment()
                continue

            # Newline
            if ch == '\n':
                self._tokens.append(Token(TokenType.NEWLINE, '\\n', self.line, self.column))
                self.pos += 1
                self.line += 1
                self.column = 1
                continue

            # Carriage return (Windows line endings)
            if ch == '\r':
                self.pos += 1
                continue

            # Whitespace
            if ch in (' ', '\t'):
                self.pos += 1
                self.column += 1
                continue

            # String literal
            if ch == '"':
                self._read_string()
                continue

            # Number literal
            if ch.isdigit() or (ch == '-' and self._peek_digit()):
                self._read_number()
                continue

            # Identifier or keyword
            if ch.isalpha() or ch == '_':
                self._read_word()
                continue

            # Operator / punctuation
            if ch in OPERATORS:
                tok = Token(OPERATORS[ch], ch, self.line, self.column)
                self._tokens.append(tok)
                self.pos += 1
                self.column += 1
                continue

            # Unknown character
            err = LexerError(
                f"Unexpected character '{ch}'",
                line=self.line, column=self.column
            )
            self._errors.append(err)
            self._tokens.append(Token(TokenType.UNKNOWN, ch, self.line, self.column))
            self.pos += 1
            self.column += 1

    def _peek_digit(self):
        """Return True if the next character (after a leading '-') is a digit."""
        return self.pos + 1 < len(self.source) and self.source[self.pos + 1].isdigit()

    def _read_comment(self):
        start_col = self.column
        start = self.pos
        while self.pos < len(self.source) and self.source[self.pos] != '\n':
            self.pos += 1
            self.column += 1
        text = self.source[start:self.pos]
        self._tokens.append(Token(TokenType.COMMENT, text, self.line, start_col))

    def _read_string(self):
        start_line, start_col = self.line, self.column
        self.pos += 1  # skip opening "
        self.column += 1
        buf = []
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == '"':
                self.pos += 1
                self.column += 1
                self._tokens.append(Token(TokenType.STRING, ''.join(buf), start_line, start_col))
                return
            if ch == '\n':
                break
            if ch == '\\' and self.pos + 1 < len(self.source):
                nxt = self.source[self.pos + 1]
                escape_map = {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}
                buf.append(escape_map.get(nxt, nxt))
                self.pos += 2
                self.column += 2
                continue
            buf.append(ch)
            self.pos += 1
            self.column += 1
        err = LexerError("Unterminated string literal", line=start_line, column=start_col)
        self._errors.append(err)
        self._tokens.append(Token(TokenType.STRING, ''.join(buf), start_line, start_col))

    def _read_number(self):
        start_col = self.column
        start = self.pos
        if self.source[self.pos] == '-':
            self.pos += 1
            self.column += 1
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            self.pos += 1
            self.column += 1
        if self.pos < len(self.source) and self.source[self.pos] == '.':
            self.pos += 1
            self.column += 1
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                self.pos += 1
                self.column += 1
        raw = self.source[start:self.pos]
        try:
            val = float(raw) if '.' in raw else int(raw)
        except ValueError:
            val = raw
        self._tokens.append(Token(TokenType.NUMBER, raw, self.line, start_col))

    def _read_word(self):
        start_col = self.column
        start = self.pos
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            self.pos += 1
            self.column += 1
        word = self.source[start:self.pos]
        upper = word.upper()
        tok_type = KEYWORDS.get(upper, TokenType.IDENTIFIER)
        self._tokens.append(Token(tok_type, word, self.line, start_col))

    # ------------------------------------------------------------------
    # Multi-word keyword assembly
    # ------------------------------------------------------------------

    def _combine_multiword(self, tokens: list[Token]) -> list[Token]:
        """
        Merge consecutive single-word tokens into composite keyword tokens.
        We try longest match first.
        Patterns (upper-cased values):
          ASK FOR  -> KW_ASK_FOR
          END IF   -> KW_END_IF
          END REPEAT -> KW_END_REPEAT
          IS GREATER THAN OR EQUAL TO -> KW_IS_GREATER_THAN_OR_EQUAL_TO
          IS LESS THAN OR EQUAL TO    -> KW_IS_LESS_THAN_OR_EQUAL_TO
          IS NOT EQUAL TO             -> KW_IS_NOT_EQUAL_TO
          IS EQUAL TO                 -> KW_IS_EQUAL_TO
          IS GREATER THAN             -> KW_IS_GREATER_THAN
          IS LESS THAN                -> KW_IS_LESS_THAN
        """
        # Pattern table: (value_sequence_upper, result_type, result_value)
        PATTERNS = [
            # Longest first
            (['IS', 'GREATER', 'THAN', 'OR', 'EQUAL', 'TO'], TokenType.KW_IS_GREATER_THAN_OR_EQUAL_TO, 'IS GREATER THAN OR EQUAL TO'),
            (['IS', 'LESS', 'THAN', 'OR', 'EQUAL', 'TO'],    TokenType.KW_IS_LESS_THAN_OR_EQUAL_TO,    'IS LESS THAN OR EQUAL TO'),
            (['IS', 'NOT', 'EQUAL', 'TO'],                    TokenType.KW_IS_NOT_EQUAL_TO,              'IS NOT EQUAL TO'),
            (['IS', 'EQUAL', 'TO'],                           TokenType.KW_IS_EQUAL_TO,                  'IS EQUAL TO'),
            (['IS', 'GREATER', 'THAN'],                       TokenType.KW_IS_GREATER_THAN,              'IS GREATER THAN'),
            (['IS', 'LESS', 'THAN'],                          TokenType.KW_IS_LESS_THAN,                 'IS LESS THAN'),
            (['ASK', 'FOR'],                                  TokenType.KW_ASK_FOR,                      'ASK FOR'),
            (['END', 'IF'],                                   TokenType.KW_END_IF,                       'END IF'),
            (['END', 'REPEAT'],                               TokenType.KW_END_REPEAT,                   'END REPEAT'),
        ]

        result = []
        i = 0
        while i < len(tokens):
            matched = False
            for pattern_vals, res_type, res_val in PATTERNS:
                n = len(pattern_vals)
                window = tokens[i:i+n]
                if len(window) < n:
                    continue
                # Skip NEWLINE / COMMENT tokens inside the window check
                raw_vals = [t.value.upper() for t in window if t.type not in (TokenType.NEWLINE, TokenType.COMMENT)]
                actual_window = [t for t in window if t.type not in (TokenType.NEWLINE, TokenType.COMMENT)]
                if len(actual_window) < n:
                    continue
                # Check if we can grab exactly n non-ws tokens starting at i
                j = i
                picked = []
                while len(picked) < n and j < len(tokens):
                    t = tokens[j]
                    if t.type not in (TokenType.NEWLINE, TokenType.COMMENT):
                        picked.append(t)
                    j += 1
                if len(picked) < n:
                    continue
                if [t.value.upper() for t in picked] == pattern_vals:
                    # Consume all tokens up to j (including skipped ws)
                    new_tok = Token(res_type, res_val, picked[0].line, picked[0].column)
                    result.append(new_tok)
                    i = j
                    matched = True
                    break
            if not matched:
                result.append(tokens[i])
                i += 1
        return result
