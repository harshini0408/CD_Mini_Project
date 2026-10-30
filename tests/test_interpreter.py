"""
Interpreter Tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.interpreter import Interpreter


def run(src, inputs=None):
    toks = Lexer(src).tokenize()
    prog = Parser(toks).parse()
    interp = Interpreter(inputs=inputs or [])
    return interp.execute(prog)


class TestArithmetic(unittest.TestCase):
    def test_addition(self):
        r = run('PRINT 2 + 3\n')
        self.assertEqual(r['output'], ['5'])

    def test_subtraction(self):
        r = run('PRINT 10 - 4\n')
        self.assertEqual(r['output'], ['6'])

    def test_multiplication(self):
        r = run('PRINT 3 * 4\n')
        self.assertEqual(r['output'], ['12'])

    def test_division(self):
        r = run('PRINT 10 / 2\n')
        self.assertEqual(r['output'], ['5'])

    def test_precedence(self):
        r = run('SET r TO 10 + 5 * 2\nPRINT r\n')
        self.assertEqual(r['output'], ['20'])

    def test_parentheses(self):
        r = run('SET r TO (10 + 5) * 2\nPRINT r\n')
        self.assertEqual(r['output'], ['30'])

    def test_modulo(self):
        r = run('PRINT 10 % 3\n')
        self.assertEqual(r['output'], ['1'])


class TestConditionals(unittest.TestCase):
    def test_true_branch(self):
        src = 'IF 5 IS GREATER THAN 3\n    PRINT "yes"\nELSE\n    PRINT "no"\nEND IF\n'
        r = run(src)
        self.assertEqual(r['output'], ['yes'])

    def test_false_branch(self):
        src = 'IF 1 IS GREATER THAN 3\n    PRINT "yes"\nELSE\n    PRINT "no"\nEND IF\n'
        r = run(src)
        self.assertEqual(r['output'], ['no'])

    def test_nested(self):
        src = (
            'SET age TO 25\n'
            'IF age IS GREATER THAN OR EQUAL TO 18\n'
            '    IF age IS GREATER THAN OR EQUAL TO 60\n'
            '        PRINT "Senior"\n'
            '    ELSE\n'
            '        PRINT "Adult"\n'
            '    END IF\n'
            'ELSE\n'
            '    PRINT "Minor"\n'
            'END IF\n'
        )
        r = run(src)
        self.assertEqual(r['output'], ['Adult'])


class TestLoop(unittest.TestCase):
    def test_repeat(self):
        r = run('REPEAT 3 TIMES\n    PRINT "hi"\nEND REPEAT\n')
        self.assertEqual(r['output'], ['hi', 'hi', 'hi'])

    def test_accumulator(self):
        src = 'SET total TO 0\nREPEAT 5 TIMES\n    SET total TO total + 10\nEND REPEAT\nPRINT total\n'
        r = run(src)
        self.assertEqual(r['output'], ['50'])

    def test_zero_repeat(self):
        r = run('REPEAT 0 TIMES\n    PRINT "x"\nEND REPEAT\nPRINT "done"\n')
        self.assertEqual(r['output'], ['done'])


class TestInput(unittest.TestCase):
    def test_ask_for(self):
        src = 'ASK FOR marks\nPRINT marks\n'
        r = run(src, inputs=['75'])
        self.assertEqual(r['output'], ['75'])

    def test_input_as_number(self):
        src = 'ASK FOR n\nPRINT n + 5\n'
        r = run(src, inputs=['10'])
        self.assertEqual(r['output'], ['15'])

    def test_missing_input(self):
        src = 'ASK FOR x\nPRINT x\n'
        r = run(src, inputs=[])
        self.assertEqual(r['status'], 'waiting_input')
        self.assertEqual(r['waiting_for'], 'x')


class TestPassFail(unittest.TestCase):
    def test_pass(self):
        src = (
            'ASK FOR marks\n'
            'IF marks IS GREATER THAN OR EQUAL TO 50\n'
            '    PRINT "Pass"\n'
            'ELSE\n'
            '    PRINT "Fail"\n'
            'END IF\n'
        )
        r = run(src, inputs=['75'])
        self.assertEqual(r['output'], ['Pass'])

    def test_fail(self):
        src = (
            'ASK FOR marks\n'
            'IF marks IS GREATER THAN OR EQUAL TO 50\n'
            '    PRINT "Pass"\n'
            'ELSE\n'
            '    PRINT "Fail"\n'
            'END IF\n'
        )
        r = run(src, inputs=['30'])
        self.assertEqual(r['output'], ['Fail'])


class TestRuntimeErrors(unittest.TestCase):
    def test_division_by_zero(self):
        r = run('PRINT 5 / 0\n')
        self.assertEqual(r['status'], 'error')


if __name__ == '__main__':
    unittest.main()
