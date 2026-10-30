"""
LogicFlow Token Definitions
All token types recognized by the lexer.
"""
from enum import Enum, auto


class TokenType(Enum):
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # Keywords (single-word)
    ASK = auto()
    FOR = auto()
    PRINT = auto()
    SET = auto()
    TO = auto()
    IF = auto()
    ELSE = auto()
    END = auto()
    REPEAT = auto()
    TIMES = auto()
    IS = auto()
    NOT = auto()
    GREATER = auto()
    LESS = auto()
    THAN = auto()
    EQUAL = auto()
    OR = auto()
    AND = auto()

    # Composite keyword tokens (multi-word, assembled by lexer)
    KW_ASK_FOR = auto()             # ASK FOR
    KW_END_IF = auto()              # END IF
    KW_END_REPEAT = auto()          # END REPEAT
    KW_IS_EQUAL_TO = auto()         # IS EQUAL TO
    KW_IS_NOT_EQUAL_TO = auto()     # IS NOT EQUAL TO
    KW_IS_GREATER_THAN = auto()     # IS GREATER THAN
    KW_IS_LESS_THAN = auto()        # IS LESS THAN
    KW_IS_GREATER_THAN_OR_EQUAL_TO = auto()   # IS GREATER THAN OR EQUAL TO
    KW_IS_LESS_THAN_OR_EQUAL_TO = auto()      # IS LESS THAN OR EQUAL TO

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()

    # Punctuation
    LPAREN = auto()
    RPAREN = auto()

    # Structure
    NEWLINE = auto()
    COMMENT = auto()
    EOF = auto()
    UNKNOWN = auto()


class Token:
    """Represents a single lexical token."""
    __slots__ = ('type', 'value', 'line', 'column')

    def __init__(self, type_: TokenType, value: str, line: int, column: int):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:C{self.column})"

    def to_dict(self):
        return {
            'type': self.type.name,
            'value': self.value,
            'line': self.line,
            'column': self.column,
        }
