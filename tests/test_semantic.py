"""
Semantic Analyzer Tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.semantic_analyzer import SemanticAnalyzer


def analyze(src):
    toks = Lexer(src).tokenize()
    prog = Parser(toks).parse()
    sa = SemanticAnalyzer()
    sa.analyze(prog)
    return sa.errors, sa.symbol_table


class TestSemanticAnalyzer(unittest.TestCase):
    def test_defined_variable(self):
        errs, _ = analyze('SET x TO 5\nPRINT x\n')
        self.assertEqual(len(errs), 0)

    def test_undefined_variable(self):
        errs, _ = analyze('PRINT missing\n')
        self.assertTrue(any('missing' in str(e) for e in errs))

    def test_reassignment(self):
        errs, sym = analyze('SET x TO 5\nSET x TO 10\nPRINT x\n')
        self.assertEqual(len(errs), 0)

    def test_ask_for_declares(self):
        errs, sym = analyze('ASK FOR name\nPRINT name\n')
        self.assertEqual(len(errs), 0)
        self.assertTrue(sym.is_defined('name'))

    def test_division_by_zero_literal(self):
        errs, _ = analyze('SET x TO 10 / 0\n')
        self.assertTrue(len(errs) > 0)
        self.assertTrue(any('zero' in str(e).lower() for e in errs))

    def test_negative_repeat_literal(self):
        errs, _ = analyze('REPEAT -3 TIMES\n    PRINT "x"\nEND REPEAT\n')
        self.assertTrue(len(errs) > 0)

    def test_undefined_in_expression(self):
        errs, _ = analyze('SET total TO missing + 10\nPRINT total\n')
        self.assertTrue(any('missing' in str(e) for e in errs))

    def test_symbol_types(self):
        _, sym = analyze('SET x TO 5\n')
        self.assertEqual(sym.lookup('x')['type'], 'number')

    def test_string_type(self):
        _, sym = analyze('SET s TO "hello"\n')
        self.assertEqual(sym.lookup('s')['type'], 'string')


if __name__ == '__main__':
    unittest.main()
