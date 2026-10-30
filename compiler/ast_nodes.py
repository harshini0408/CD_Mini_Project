"""
LogicFlow AST Node Definitions
All AST node classes used by the parser and consumed by
the flowchart generator and interpreter.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    node_id: str = field(default="", init=False)
    line: int = field(default=None)

    def accept(self, visitor):
        method_name = f"visit_{type(self).__name__}"
        method = getattr(visitor, method_name, visitor.generic_visit)
        return method(self)


@dataclass
class Program(ASTNode):
    body: List[ASTNode] = field(default_factory=list)
    line: int = field(default=1)


@dataclass
class InputStatement(ASTNode):
    variable: str = ""
    line: int = field(default=None)


@dataclass
class PrintStatement(ASTNode):
    expression: ASTNode = None
    line: int = field(default=None)


@dataclass
class Assignment(ASTNode):
    variable: str = ""
    expression: ASTNode = None
    line: int = field(default=None)


@dataclass
class NumberLiteral(ASTNode):
    value: Any = 0
    line: int = field(default=None)


@dataclass
class StringLiteral(ASTNode):
    value: str = ""
    line: int = field(default=None)


@dataclass
class VariableReference(ASTNode):
    name: str = ""
    line: int = field(default=None)


@dataclass
class BinaryExpression(ASTNode):
    operator: str = ""
    left: ASTNode = None
    right: ASTNode = None
    line: int = field(default=None)


@dataclass
class ComparisonExpression(ASTNode):
    operator: str = ""   # e.g. "IS GREATER THAN OR EQUAL TO"
    left: ASTNode = None
    right: ASTNode = None
    line: int = field(default=None)


@dataclass
class IfStatement(ASTNode):
    condition: ASTNode = None
    then_body: List[ASTNode] = field(default_factory=list)
    else_body: List[ASTNode] = field(default_factory=list)
    line: int = field(default=None)


@dataclass
class RepeatStatement(ASTNode):
    count: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)
    line: int = field(default=None)


def ast_to_dict(node):
    """Recursively convert an AST node to a JSON-serializable dict."""
    if node is None:
        return None
    if isinstance(node, list):
        return [ast_to_dict(n) for n in node]
    if isinstance(node, ASTNode):
        d = {'_type': type(node).__name__, '_id': node.node_id, 'line': node.line}
        for fname, fval in node.__dict__.items():
            if fname in ('node_id', 'line'):
                continue
            d[fname] = ast_to_dict(fval)
        return d
    return node
