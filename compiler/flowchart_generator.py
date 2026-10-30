"""
LogicFlow Flowchart Generator
Converts the AST into a Mermaid.js flowchart definition and a
node-metadata map for execution highlighting.

Each AST node gets a stable flowchart node ID (same as node.node_id).
Additional synthetic nodes are created for:
  - START / END terminators
  - Loop check nodes
  - Merge/join nodes after conditionals
"""
from .ast_nodes import (
    Program, InputStatement, PrintStatement, Assignment,
    NumberLiteral, StringLiteral, VariableReference,
    BinaryExpression, ComparisonExpression, IfStatement, RepeatStatement,
    ASTNode
)


class FlowchartGenerator:
    def __init__(self):
        self._lines: list[str] = []       # Mermaid lines
        self._node_meta: dict[str, dict] = {}  # node_id -> metadata
        self._edge_counter = 0
        self._synth_counter = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, program: Program) -> dict:
        """Return {'mermaid': str, 'nodes': dict}"""
        self._lines = []
        self._node_meta = {}
        self._edge_counter = 0
        self._synth_counter = 0

        self._lines.append('flowchart TD')

        # Define START node (avoid Mermaid reserved word 'start')
        self._def_node('node_start', 'START', 'terminator')
        self._lines.append(f'    node_start([🚀 START])')

        # Generate body — returns the "exit" id we should wire to END
        exit_id = self._gen_block(program.body, 'node_start')

        # Define END node (avoid Mermaid reserved word 'end')
        self._def_node('node_end', 'END', 'terminator')
        self._lines.append(f'    node_end([🏁 END])')
        self._add_edge(exit_id, 'node_end')

        # Add styles
        self._lines.append('')
        self._lines.append('    classDef terminator fill:#4CAF50,stroke:#2E7D32,color:#fff,rx:20')
        self._lines.append('    classDef process fill:#2196F3,stroke:#1565C0,color:#fff')
        self._lines.append('    classDef io fill:#9C27B0,stroke:#6A1B9A,color:#fff')
        self._lines.append('    classDef decision fill:#FF9800,stroke:#E65100,color:#fff')
        self._lines.append('    classDef loop fill:#F44336,stroke:#B71C1C,color:#fff')
        self._lines.append('    class node_start,node_end terminator')

        # Apply class per node
        for nid, meta in self._node_meta.items():
            if nid in ('node_start', 'node_end'):
                continue
            cls = meta.get('shape_class', 'process')
            self._lines.append(f'    class {nid} {cls}')

        mermaid_text = '\n'.join(self._lines)
        return {
            'mermaid': mermaid_text,
            'nodes': self._node_meta,
        }

    # ------------------------------------------------------------------
    # Block generation — returns the last node ID in the block
    # ------------------------------------------------------------------

    def _gen_block(self, stmts, prev_id: str) -> str:
        current = prev_id
        for stmt in stmts:
            current = self._gen_stmt(stmt, current)
        return current

    def _gen_stmt(self, node, prev_id: str) -> str:
        method = f"_gen_{type(node).__name__}"
        return getattr(self, method, self._gen_unknown)(node, prev_id)

    def _gen_unknown(self, node, prev_id):
        return prev_id

    # ------------------------------------------------------------------
    # Statement generators
    # ------------------------------------------------------------------

    def _gen_InputStatement(self, node: InputStatement, prev_id: str) -> str:
        nid = node.node_id
        label = self._escape(f'📥 INPUT: {node.variable}')
        self._lines.append(f'    {nid}[/{label}/]')
        self._def_node(nid, f'INPUT: {node.variable}', 'io')
        self._add_edge(prev_id, nid)
        return nid

    def _gen_PrintStatement(self, node: PrintStatement, prev_id: str) -> str:
        nid = node.node_id
        label = self._escape(f'📤 PRINT: {self._expr_label(node.expression)}')
        self._lines.append(f'    {nid}[/{label}/]')
        self._def_node(nid, f'PRINT: {self._expr_label(node.expression)}', 'io')
        self._add_edge(prev_id, nid)
        return nid

    def _gen_Assignment(self, node: Assignment, prev_id: str) -> str:
        nid = node.node_id
        label = self._escape(f'SET {node.variable} = {self._expr_label(node.expression)}')
        self._lines.append(f'    {nid}["{label}"]')
        self._def_node(nid, f'SET {node.variable} = {self._expr_label(node.expression)}', 'process')
        self._add_edge(prev_id, nid)
        return nid

    def _gen_IfStatement(self, node: IfStatement, prev_id: str) -> str:
        nid = node.node_id
        cond_label = self._escape(self._condition_label(node.condition))
        self._lines.append(f'    {nid}{{{cond_label}}}')
        self._def_node(nid, self._condition_label(node.condition), 'decision')
        self._add_edge(prev_id, nid)

        # Merge node
        merge_id = self._synth_id('merge')
        self._lines.append(f'    {merge_id}[ ]')
        self._def_node(merge_id, 'merge', 'process')

        # TRUE branch
        if node.then_body:
            first_then = node.then_body[0]
            then_exit = self._gen_block(node.then_body, nid)
            # Add TRUE label on first edge of then branch
            self._label_last_edge(nid, first_then.node_id, 'TRUE ✓')
            self._add_edge(then_exit, merge_id)
        else:
            self._add_edge(nid, merge_id, label='TRUE ✓')

        # FALSE branch
        if node.else_body:
            first_else = node.else_body[0]
            else_exit = self._gen_block(node.else_body, nid)
            self._label_last_edge(nid, first_else.node_id, 'FALSE ✗')
            self._add_edge(else_exit, merge_id)
        else:
            self._add_edge(nid, merge_id, label='FALSE ✗')

        return merge_id

    def _gen_RepeatStatement(self, node: RepeatStatement, prev_id: str) -> str:
        nid = node.node_id
        count_label = self._expr_label(node.count)
        loop_check_id = self._synth_id('loop_check')
        loop_end_id = self._synth_id('loop_end')

        # Loop entry
        entry_label = self._escape(f'🔁 REPEAT {count_label} TIMES')
        self._lines.append(f'    {nid}["{entry_label}"]')
        self._def_node(nid, f'REPEAT {count_label} TIMES', 'loop')
        self._add_edge(prev_id, nid)

        # Loop condition check node
        check_label = self._escape('counter > 0 ?')
        self._lines.append(f'    {loop_check_id}{{{check_label}}}')
        self._def_node(loop_check_id, 'Loop condition', 'decision')
        self._add_edge(nid, loop_check_id)

        # Loop body
        if node.body:
            body_exit = self._gen_block(node.body, loop_check_id)
            # Label TRUE going into body
            self._label_last_edge(loop_check_id, node.body[0].node_id, 'TRUE ✓')
            # Back edge
            self._lines.append(f'    {body_exit} --> {loop_check_id}')
            self._edge_counter += 1
        else:
            self._add_edge(loop_check_id, loop_check_id, label='TRUE ✓')

        # Exit
        self._lines.append(f'    {loop_end_id}[ ]')
        self._def_node(loop_end_id, 'loop exit', 'process')
        self._add_edge(loop_check_id, loop_end_id, label='FALSE ✗')

        return loop_end_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _def_node(self, nid: str, label: str, shape_class: str):
        self._node_meta[nid] = {'label': label, 'shape_class': shape_class}

    def _add_edge(self, src: str, dst: str, label: str = None):
        if label:
            self._lines.append(f'    {src} -->|{self._escape(label)}| {dst}')
        else:
            self._lines.append(f'    {src} --> {dst}')
        self._edge_counter += 1

    def _label_last_edge(self, src: str, dst: str, label: str):
        """Replace the last edge src->dst with a labeled version."""
        target = f'    {src} --> {dst}'
        for i in range(len(self._lines) - 1, -1, -1):
            if self._lines[i] == target:
                self._lines[i] = f'    {src} -->|{self._escape(label)}| {dst}'
                return
        # If not found (edge created differently), just add labeled edge
        self._add_edge(src, dst, label)

    def _synth_id(self, prefix: str) -> str:
        self._synth_counter += 1
        return f'{prefix}_{self._synth_counter}'

    def _escape(self, text: str) -> str:
        """Escape characters that break Mermaid labels."""
        return (text
                .replace('"', "'")
                .replace('{', '[')
                .replace('}', ']')
                .replace('>=', '≥')
                .replace('<=', '≤')
                .replace('>', '&gt;')
                .replace('<', '&lt;'))

    def _expr_label(self, node) -> str:
        if node is None:
            return ''
        if isinstance(node, NumberLiteral):
            return str(node.value)
        if isinstance(node, StringLiteral):
            return f'"{node.value}"'
        if isinstance(node, VariableReference):
            return node.name
        if isinstance(node, BinaryExpression):
            return f'{self._expr_label(node.left)} {node.operator} {self._expr_label(node.right)}'
        if isinstance(node, ComparisonExpression):
            return self._condition_label(node)
        return '?'

    def _condition_label(self, node: ComparisonExpression) -> str:
        left = self._expr_label(node.left)
        right = self._expr_label(node.right)
        return f'{left} {node.operator} {right}'
