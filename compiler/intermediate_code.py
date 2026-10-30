"""
LogicFlow Intermediate Code Generator
Produces a simple stack-machine instruction sequence from the AST.
This is used solely for educational inspection; the interpreter
operates directly on the AST.

Instruction set:
  LOAD_CONST <value>
  LOAD <var>
  STORE <var>
  ADD / SUB / MUL / DIV / MOD
  PRINT
  INPUT <var>
  LABEL <name>
  JUMP <label>
  JUMP_IF_FALSE <label>
  COMPARE <op>
"""
from .ast_nodes import (
    Program, InputStatement, PrintStatement, Assignment,
    NumberLiteral, StringLiteral, VariableReference,
    BinaryExpression, ComparisonExpression, IfStatement, RepeatStatement
)


class Instruction:
    __slots__ = ('op', 'arg')

    def __init__(self, op: str, arg=None):
        self.op = op
        self.arg = arg

    def __str__(self):
        if self.arg is None:
            return self.op
        return f"{self.op} {self.arg}"

    def to_dict(self):
        return {'op': self.op, 'arg': self.arg}


class IRGenerator:
    def __init__(self):
        self._instructions: list[Instruction] = []
        self._label_counter = 0

    def generate(self, program: Program) -> list[Instruction]:
        self._instructions = []
        self._emit('PROGRAM_START')
        self._gen_block(program.body)
        self._emit('PROGRAM_END')
        return self._instructions

    def _emit(self, op: str, arg=None):
        self._instructions.append(Instruction(op, arg))

    def _new_label(self, prefix='L') -> str:
        self._label_counter += 1
        return f"{prefix}{self._label_counter}"

    def _gen_block(self, stmts):
        for stmt in stmts:
            self._gen(stmt)

    def _gen(self, node):
        method = f"_gen_{type(node).__name__}"
        getattr(self, method, self._gen_unknown)(node)

    def _gen_unknown(self, node):
        self._emit(f'; unknown node {type(node).__name__}')

    def _gen_InputStatement(self, node: InputStatement):
        self._emit('INPUT', node.variable)

    def _gen_PrintStatement(self, node: PrintStatement):
        self._gen_expr(node.expression)
        self._emit('PRINT')

    def _gen_Assignment(self, node: Assignment):
        self._gen_expr(node.expression)
        self._emit('STORE', node.variable)

    def _gen_IfStatement(self, node: IfStatement):
        else_label = self._new_label('ELSE')
        end_label = self._new_label('END_IF')
        # Evaluate condition
        self._gen_expr(node.condition.left)
        self._gen_expr(node.condition.right)
        self._emit('COMPARE', node.condition.operator)
        self._emit('JUMP_IF_FALSE', else_label)
        self._gen_block(node.then_body)
        self._emit('JUMP', end_label)
        self._emit('LABEL', else_label)
        self._gen_block(node.else_body)
        self._emit('LABEL', end_label)

    def _gen_RepeatStatement(self, node: RepeatStatement):
        loop_label = self._new_label('LOOP')
        end_label = self._new_label('END_LOOP')
        counter_var = f'__counter_{self._label_counter}'
        # Initialize counter to count
        self._gen_expr(node.count)
        self._emit('STORE', counter_var)
        # Loop check
        self._emit('LABEL', loop_label)
        self._emit('LOAD', counter_var)
        self._emit('LOAD_CONST', 0)
        self._emit('COMPARE', 'IS GREATER THAN')
        self._emit('JUMP_IF_FALSE', end_label)
        self._gen_block(node.body)
        # Decrement counter
        self._emit('LOAD', counter_var)
        self._emit('LOAD_CONST', 1)
        self._emit('SUB')
        self._emit('STORE', counter_var)
        self._emit('JUMP', loop_label)
        self._emit('LABEL', end_label)

    def _gen_expr(self, node):
        method = f"_gen_expr_{type(node).__name__}"
        getattr(self, method, self._gen_expr_unknown)(node)

    def _gen_expr_unknown(self, node):
        self._emit('; unknown expr')

    def _gen_expr_NumberLiteral(self, node: NumberLiteral):
        self._emit('LOAD_CONST', node.value)

    def _gen_expr_StringLiteral(self, node: StringLiteral):
        self._emit('LOAD_CONST', repr(node.value))

    def _gen_expr_VariableReference(self, node: VariableReference):
        self._emit('LOAD', node.name)

    def _gen_expr_BinaryExpression(self, node: BinaryExpression):
        self._gen_expr(node.left)
        self._gen_expr(node.right)
        op_map = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV', '%': 'MOD'}
        self._emit(op_map.get(node.operator, f'OP_{node.operator}'))

    def _gen_expr_ComparisonExpression(self, node: ComparisonExpression):
        self._gen_expr(node.left)
        self._gen_expr(node.right)
        self._emit('COMPARE', node.operator)

    def instructions_as_text(self) -> str:
        return '\n'.join(str(i) for i in self._instructions)

    def instructions_as_dicts(self) -> list[dict]:
        return [i.to_dict() for i in self._instructions]
