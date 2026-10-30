"""
LogicFlow AST Interpreter
Executes the AST directly without using eval() or exec().
Supports:
  - Arithmetic with correct precedence
  - Conditionals (IF/ELSE)
  - REPEAT loops
  - ASK FOR (pauses execution and resumes when input is provided)

Execution returns an ordered list of events for flowchart highlighting.
"""
from .ast_nodes import (
    Program, InputStatement, PrintStatement, Assignment,
    NumberLiteral, StringLiteral, VariableReference,
    BinaryExpression, ComparisonExpression, IfStatement, RepeatStatement
)
from .errors import RuntimeError_, ExecutionLimitError

MAX_STATEMENTS = 10_000
MAX_LOOP_ITERATIONS = 1_000


class ExecutionEvent:
    """A single event emitted during execution (for flowchart highlighting)."""
    __slots__ = ('event_type', 'node_id', 'detail')

    def __init__(self, event_type: str, node_id: str, detail: dict = None):
        self.event_type = event_type
        self.node_id = node_id
        self.detail = detail or {}

    def to_dict(self):
        return {'event': self.event_type, 'node_id': self.node_id, 'detail': self.detail}


class Interpreter:
    """
    AST interpreter that returns a complete execution report.
    For ASK FOR statements, if inputs are pre-supplied, they are consumed
    in order. If no input is available, an InputRequired signal is raised.
    """

    def __init__(self, inputs: list[str] = None):
        self._env: dict[str, object] = {}
        self._output: list[str] = []
        self._events: list[ExecutionEvent] = []
        self._inputs = list(inputs or [])
        self._input_index = 0
        self._statement_count = 0
        self._status = 'ready'
        self._errors: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, program: Program) -> dict:
        """Execute the full program and return the report."""
        self._status = 'running'
        self._emit('program_start', 'node_start', {})
        try:
            self._exec_block(program.body)
            self._status = 'completed'
        except _InputRequired as e:
            self._status = 'waiting_input'
            return self._report(waiting_for=e.variable)
        except ExecutionLimitError as e:
            self._status = 'error'
            self._errors.append(str(e))
        except RuntimeError_ as e:
            self._status = 'error'
            self._errors.append(str(e))
        except Exception as e:
            self._status = 'error'
            self._errors.append(f"Internal error: {e}")
        self._emit('program_end', 'node_end', {})
        return self._report()

    def _report(self, waiting_for=None):
        return {
            'status': self._status,
            'output': self._output,
            'events': [e.to_dict() for e in self._events],
            'variables': {k: v for k, v in self._env.items() if not k.startswith('__')},
            'errors': self._errors,
            'waiting_for': waiting_for,
        }

    # ------------------------------------------------------------------
    # Block / statement execution
    # ------------------------------------------------------------------

    def _exec_block(self, stmts):
        for stmt in stmts:
            self._statement_count += 1
            if self._statement_count > MAX_STATEMENTS:
                raise ExecutionLimitError(f"Execution limit of {MAX_STATEMENTS} statements exceeded")
            self._exec(stmt)

    def _exec(self, node):
        method = f"_exec_{type(node).__name__}"
        getattr(self, method, self._exec_unknown)(node)

    def _exec_unknown(self, node):
        raise RuntimeError_(f"Unknown AST node: {type(node).__name__}")

    def _exec_InputStatement(self, node: InputStatement):
        self._emit('enter_node', node.node_id, {'type': 'input', 'variable': node.variable})
        if self._input_index >= len(self._inputs):
            raise _InputRequired(node.variable)
        raw = self._inputs[self._input_index]
        self._input_index += 1
        # Try numeric conversion
        value = self._convert_input(raw)
        self._env[node.variable] = value
        self._emit('input_received', node.node_id, {'variable': node.variable, 'value': value})

    def _exec_PrintStatement(self, node: PrintStatement):
        self._emit('enter_node', node.node_id, {'type': 'output'})
        val = self._eval(node.expression)
        result = self._to_display(val)
        self._output.append(result)
        self._emit('output', node.node_id, {'value': result})

    def _exec_Assignment(self, node: Assignment):
        self._emit('enter_node', node.node_id, {'type': 'process'})
        val = self._eval(node.expression)
        self._env[node.variable] = val
        self._emit('assign', node.node_id, {'variable': node.variable, 'value': val})

    def _exec_IfStatement(self, node: IfStatement):
        self._emit('enter_node', node.node_id, {'type': 'decision'})
        cond_val = self._eval_condition(node.condition)
        self._emit('decision', node.node_id, {'result': cond_val})
        if cond_val:
            self._emit('branch', node.node_id, {'branch': 'true'})
            self._exec_block(node.then_body)
        else:
            self._emit('branch', node.node_id, {'branch': 'false'})
            self._exec_block(node.else_body)

    def _exec_RepeatStatement(self, node: RepeatStatement):
        self._emit('enter_node', node.node_id, {'type': 'loop'})
        count = self._eval(node.count)
        if not isinstance(count, (int, float)):
            raise RuntimeError_("REPEAT count must be a number", line=node.line)
        count = int(count)
        if count < 0:
            raise RuntimeError_("REPEAT count must be non-negative", line=node.line)
        iterations = 0
        for i in range(count):
            if iterations >= MAX_LOOP_ITERATIONS:
                raise ExecutionLimitError(f"Loop iteration limit of {MAX_LOOP_ITERATIONS} exceeded")
            self._emit('loop_iteration', node.node_id, {'iteration': i + 1, 'total': count})
            self._exec_block(node.body)
            iterations += 1
        self._emit('loop_exit', node.node_id, {'iterations': iterations})

    # ------------------------------------------------------------------
    # Expression evaluation (no eval/exec)
    # ------------------------------------------------------------------

    def _eval(self, node):
        method = f"_eval_{type(node).__name__}"
        return getattr(self, method, self._eval_unknown)(node)

    def _eval_unknown(self, node):
        raise RuntimeError_(f"Cannot evaluate node: {type(node).__name__}")

    def _eval_NumberLiteral(self, node: NumberLiteral):
        return node.value

    def _eval_StringLiteral(self, node: StringLiteral):
        return node.value

    def _eval_VariableReference(self, node: VariableReference):
        if node.name not in self._env:
            raise RuntimeError_(f"Undefined variable '{node.name}'", line=node.line)
        return self._env[node.name]

    def _eval_BinaryExpression(self, node: BinaryExpression):
        left = self._eval(node.left)
        right = self._eval(node.right)
        op = node.operator
        if op == '+':
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            return left + right
        if op == '-':
            return self._num(left, node) - self._num(right, node)
        if op == '*':
            return self._num(left, node) * self._num(right, node)
        if op == '/':
            r = self._num(right, node)
            if r == 0:
                raise RuntimeError_("Division by zero", line=node.line)
            result = self._num(left, node) / r
            return int(result) if result == int(result) else result
        if op == '%':
            r = self._num(right, node)
            if r == 0:
                raise RuntimeError_("Modulo by zero", line=node.line)
            return self._num(left, node) % r
        raise RuntimeError_(f"Unknown operator '{op}'")

    def _eval_ComparisonExpression(self, node: ComparisonExpression):
        return self._eval_condition(node)

    def _eval_condition(self, node: ComparisonExpression) -> bool:
        left = self._eval(node.left)
        right = self._eval(node.right)
        op = node.operator
        try:
            if op == 'IS EQUAL TO':
                return left == right
            if op == 'IS NOT EQUAL TO':
                return left != right
            if op == 'IS GREATER THAN':
                return left > right
            if op == 'IS LESS THAN':
                return left < right
            if op == 'IS GREATER THAN OR EQUAL TO':
                return left >= right
            if op == 'IS LESS THAN OR EQUAL TO':
                return left <= right
        except TypeError:
            raise RuntimeError_(f"Cannot compare {type(left).__name__} and {type(right).__name__}", line=node.line)
        raise RuntimeError_(f"Unknown comparison operator '{op}'")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _num(self, val, node):
        if isinstance(val, (int, float)):
            return val
        try:
            return float(val)
        except (TypeError, ValueError):
            raise RuntimeError_(f"Expected a number but got '{val}'", line=getattr(node, 'line', None))

    def _convert_input(self, raw: str):
        """Convert raw string input to the most appropriate type."""
        raw = raw.strip()
        try:
            i = int(raw)
            return i
        except ValueError:
            pass
        try:
            f = float(raw)
            return f
        except ValueError:
            pass
        return raw

    def _to_display(self, val) -> str:
        if isinstance(val, float) and val == int(val):
            return str(int(val))
        return str(val)

    def _emit(self, event_type: str, node_id: str, detail: dict):
        self._events.append(ExecutionEvent(event_type, node_id, detail))


class _InputRequired(Exception):
    """Signal raised when an ASK FOR has no available input."""
    def __init__(self, variable: str):
        self.variable = variable
        super().__init__(f"Input required for variable '{variable}'")
