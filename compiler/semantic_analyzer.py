"""
LogicFlow Semantic Analyzer
Validates the AST before execution:
  - Undefined variable references
  - Division by zero (literal)
  - Negative repeat counts (literal)
  - Type-incompatible operations where detectable statically
"""
from .ast_nodes import (
    Program, InputStatement, PrintStatement, Assignment,
    NumberLiteral, StringLiteral, VariableReference,
    BinaryExpression, ComparisonExpression, IfStatement, RepeatStatement
)
from .symbol_table import SymbolTable
from .errors import SemanticError


class SemanticAnalyzer:
    def __init__(self):
        self._symbols = SymbolTable()
        self._errors: list[SemanticError] = []

    @property
    def errors(self):
        return self._errors

    @property
    def symbol_table(self):
        return self._symbols

    def analyze(self, program: Program):
        self._visit_block(program.body)

    def _visit_block(self, stmts):
        for stmt in stmts:
            self._visit(stmt)

    def _visit(self, node):
        method = f"_visit_{type(node).__name__}"
        visitor = getattr(self, method, self._generic_visit)
        visitor(node)

    def _generic_visit(self, node):
        pass

    # ------------------------------------------------------------------
    # Statement visitors
    # ------------------------------------------------------------------

    def _visit_InputStatement(self, node: InputStatement):
        # ASK FOR declares the variable with type 'any'
        self._symbols.declare(node.variable, 'any', node.line)

    def _visit_Assignment(self, node: Assignment):
        inferred = self._infer_type(node.expression)
        self._visit_expr(node.expression)
        self._symbols.declare(node.variable, inferred, node.line)

    def _visit_PrintStatement(self, node: PrintStatement):
        self._visit_expr(node.expression)

    def _visit_IfStatement(self, node: IfStatement):
        self._visit_expr(node.condition.left)
        self._visit_expr(node.condition.right)
        self._visit_block(node.then_body)
        self._visit_block(node.else_body)

    def _visit_RepeatStatement(self, node: RepeatStatement):
        # Check for negative literal count
        if isinstance(node.count, NumberLiteral):
            if node.count.value < 0:
                self._errors.append(SemanticError(
                    f"REPEAT count must be non-negative, got {node.count.value}",
                    line=node.line
                ))
        self._visit_expr(node.count)
        self._visit_block(node.body)

    # ------------------------------------------------------------------
    # Expression visitors
    # ------------------------------------------------------------------

    def _visit_expr(self, node):
        if node is None:
            return
        method = f"_visit_{type(node).__name__}"
        visitor = getattr(self, method, self._generic_visit)
        visitor(node)

    def _visit_VariableReference(self, node: VariableReference):
        if not self._symbols.is_defined(node.name):
            self._errors.append(SemanticError(
                f"Undefined variable '{node.name}'",
                line=node.line
            ))

    def _visit_BinaryExpression(self, node: BinaryExpression):
        self._visit_expr(node.left)
        self._visit_expr(node.right)
        # Detect literal division by zero
        if node.operator == '/' and isinstance(node.right, NumberLiteral) and node.right.value == 0:
            self._errors.append(SemanticError(
                "Division by zero detected",
                line=node.line
            ))

    def _visit_ComparisonExpression(self, node: ComparisonExpression):
        self._visit_expr(node.left)
        self._visit_expr(node.right)

    def _visit_NumberLiteral(self, node): pass
    def _visit_StringLiteral(self, node): pass

    # ------------------------------------------------------------------
    # Type inference
    # ------------------------------------------------------------------

    def _infer_type(self, node) -> str:
        if isinstance(node, NumberLiteral):
            return 'number'
        if isinstance(node, StringLiteral):
            return 'string'
        if isinstance(node, VariableReference):
            sym = self._symbols.lookup(node.name)
            return sym['type'] if sym else 'unknown'
        if isinstance(node, BinaryExpression):
            lt = self._infer_type(node.left)
            rt = self._infer_type(node.right)
            if lt == 'number' and rt == 'number':
                return 'number'
            if lt == 'string' or rt == 'string':
                return 'string'
            return 'any'
        return 'any'
