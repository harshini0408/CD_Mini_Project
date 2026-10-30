"""
LogicFlow Error Classes
Structured error reporting for all compiler stages.
"""


class LogicFlowError(Exception):
    """Base class for all LogicFlow errors."""
    category = "Error"

    def __init__(self, message: str, line: int = None, column: int = None, source_line: str = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column
        self.source_line = source_line

    def to_dict(self):
        return {
            'category': self.category,
            'message': self.message,
            'line': self.line,
            'column': self.column,
            'source_line': self.source_line,
        }

    def __str__(self):
        loc = ""
        if self.line is not None:
            loc = f" [Line {self.line}"
            if self.column is not None:
                loc += f", Col {self.column}"
            loc += "]"
        return f"{self.category}{loc}: {self.message}"


class LexerError(LogicFlowError):
    category = "Lexer Error"


class ParseError(LogicFlowError):
    category = "Parse Error"


class SemanticError(LogicFlowError):
    category = "Semantic Error"


class RuntimeError_(LogicFlowError):
    category = "Runtime Error"


class ExecutionLimitError(RuntimeError_):
    category = "Execution Limit Error"
