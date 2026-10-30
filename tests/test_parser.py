"""
Parser Tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.ast_nodes import (
    Program, Assignment, PrintStatement, InputStatement,
    IfStatement, RepeatStatement, BinaryExpression, NumberLiteral, VariableReference
)


def parse(src):
    toks = Lexer(src).tokenize()
    p = Parser(toks)
    prog = p.parse()
    return prog, p.errors


class TestAssignment(unittest.TestCase):
    def test_simple(self):
        prog, errs = parse('SET x TO 5\n')
        self.assertEqual(len(errs), 0)
        self.assertEqual(len(prog.body), 1)
        node = prog.body[0]
        self.assertIsInstance(node, Assignment)
        self.assertEqual(node.variable, 'x')

    def test_expression(self):
        prog, errs = parse('SET y TO x + 5\n')
        self.assertEqual(len(errs), 0)
        node = prog.body[0]
        self.assertIsInstance(node.expression, BinaryExpression)
        self.assertEqual(node.expression.operator, '+')

    def test_precedence(self):
        prog, errs = parse('SET r TO 10 + 5 * 2\n')
        self.assertEqual(len(errs), 0)
        expr = prog.body[0].expression
        # Should be 10 + (5 * 2) — top is +, right is *
        self.assertIsInstance(expr, BinaryExpression)
        self.assertEqual(expr.operator, '+')
        self.assertIsInstance(expr.right, BinaryExpression)
        self.assertEqual(expr.right.operator, '*')


class TestPrint(unittest.TestCase):
    def test_print_string(self):
        prog, errs = parse('PRINT "hello"\n')
        self.assertEqual(len(errs), 0)
        self.assertIsInstance(prog.body[0], PrintStatement)

    def test_print_variable(self):
        prog, errs = parse('PRINT x\n')
        self.assertEqual(len(errs), 0)


class TestInput(unittest.TestCase):
    def test_ask_for(self):
        prog, errs = parse('ASK FOR marks\n')
        self.assertEqual(len(errs), 0)
        self.assertIsInstance(prog.body[0], InputStatement)
        self.assertEqual(prog.body[0].variable, 'marks')


class TestIf(unittest.TestCase):
    def test_if_else(self):
        src = 'IF x IS GREATER THAN 5\n    PRINT "big"\nELSE\n    PRINT "small"\nEND IF\n'
        prog, errs = parse(src)
        self.assertEqual(len(errs), 0, errs)
        node = prog.body[0]
        self.assertIsInstance(node, IfStatement)
        self.assertEqual(len(node.then_body), 1)
        self.assertEqual(len(node.else_body), 1)

    def test_nested_if(self):
        src = (
            'IF a IS GREATER THAN 0\n'
            '    IF b IS LESS THAN 10\n'
            '        PRINT "ok"\n'
            '    END IF\n'
            'END IF\n'
        )
        prog, errs = parse(src)
        self.assertEqual(len(errs), 0, errs)
        outer = prog.body[0]
        inner = outer.then_body[0]
        self.assertIsInstance(inner, IfStatement)

    def test_missing_end_if(self):
        src = 'IF x IS EQUAL TO 1\n    PRINT "yes"\n'
        prog, errs = parse(src)
        self.assertTrue(len(errs) > 0)


class TestRepeat(unittest.TestCase):
    def test_repeat(self):
        src = 'REPEAT 3 TIMES\n    PRINT "hi"\nEND REPEAT\n'
        prog, errs = parse(src)
        self.assertEqual(len(errs), 0, errs)
        node = prog.body[0]
        self.assertIsInstance(node, RepeatStatement)
        self.assertIsInstance(node.count, NumberLiteral)
        self.assertEqual(node.count.value, 3)

    def test_missing_end_repeat(self):
        src = 'REPEAT 2 TIMES\n    PRINT "x"\n'
        prog, errs = parse(src)
        self.assertTrue(len(errs) > 0)


if __name__ == '__main__':
    unittest.main()
