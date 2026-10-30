"""
Flowchart Generator Tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.flowchart_generator import FlowchartGenerator


def generate(src):
    toks = Lexer(src).tokenize()
    prog = Parser(toks).parse()
    gen = FlowchartGenerator()
    return gen.generate(prog)


class TestFlowchartNodes(unittest.TestCase):
    def test_start_end_present(self):
        fc = generate('PRINT "hi"\n')
        self.assertIn('node_start', fc['nodes'])
        self.assertIn('node_end', fc['nodes'])

    def test_print_node(self):
        fc = generate('PRINT "hello"\n')
        nodes = fc['nodes']
        io_nodes = [n for n, m in nodes.items() if m['shape_class'] == 'io']
        self.assertTrue(len(io_nodes) > 0)

    def test_assignment_node(self):
        fc = generate('SET x TO 5\n')
        nodes = fc['nodes']
        proc_nodes = [n for n, m in nodes.items() if m['shape_class'] == 'process']
        # Should have at least the assignment process node
        self.assertTrue(len(proc_nodes) > 0)

    def test_decision_node(self):
        src = 'IF x IS GREATER THAN 5\n    PRINT "big"\nELSE\n    PRINT "small"\nEND IF\n'
        fc = generate(src)
        nodes = fc['nodes']
        decision_nodes = [n for n, m in nodes.items() if m['shape_class'] == 'decision']
        self.assertTrue(len(decision_nodes) > 0)

    def test_loop_node(self):
        src = 'REPEAT 3 TIMES\n    PRINT "hi"\nEND REPEAT\n'
        fc = generate(src)
        nodes = fc['nodes']
        loop_nodes = [n for n, m in nodes.items() if m['shape_class'] == 'loop']
        self.assertTrue(len(loop_nodes) > 0)

    def test_input_node(self):
        fc = generate('ASK FOR x\n')
        nodes = fc['nodes']
        io_nodes = [n for n, m in nodes.items() if 'INPUT' in m['label']]
        self.assertTrue(len(io_nodes) > 0)

    def test_mermaid_starts_with_flowchart(self):
        fc = generate('PRINT "hi"\n')
        self.assertTrue(fc['mermaid'].startswith('flowchart TD'))

    def test_stable_node_ids(self):
        src = 'PRINT "hello"\n'
        fc1 = generate(src)
        fc2 = generate(src)
        self.assertEqual(set(fc1['nodes'].keys()), set(fc2['nodes'].keys()))

    def test_nested_if_has_multiple_decisions(self):
        src = (
            'IF a IS GREATER THAN 0\n'
            '    IF b IS LESS THAN 10\n'
            '        PRINT "ok"\n'
            '    END IF\n'
            'END IF\n'
        )
        fc = generate(src)
        nodes = fc['nodes']
        decision_nodes = [n for n, m in nodes.items() if m['shape_class'] == 'decision']
        self.assertGreaterEqual(len(decision_nodes), 2)


if __name__ == '__main__':
    unittest.main()
