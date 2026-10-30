"""
Lexer Tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from compiler.lexer import Lexer
from compiler.tokens import TokenType


def lex(src):
    return Lexer(src).tokenize()


def types(src):
    return [t.type for t in lex(src) if t.type not in (TokenType.NEWLINE, TokenType.EOF)]


class TestKeywords(unittest.TestCase):
    def test_ask_for(self):
        toks = types('ASK FOR age')
        self.assertIn(TokenType.KW_ASK_FOR, toks)

    def test_set_to(self):
        toks = types('SET x TO 5')
        self.assertIn(TokenType.SET, toks)
        self.assertIn(TokenType.TO, toks)

    def test_end_if(self):
        toks = types('END IF')
        self.assertIn(TokenType.KW_END_IF, toks)

    def test_end_repeat(self):
        toks = types('END REPEAT')
        self.assertIn(TokenType.KW_END_REPEAT, toks)


class TestComparisons(unittest.TestCase):
    def test_is_equal_to(self):
        self.assertIn(TokenType.KW_IS_EQUAL_TO, types('x IS EQUAL TO y'))

    def test_is_not_equal_to(self):
        self.assertIn(TokenType.KW_IS_NOT_EQUAL_TO, types('x IS NOT EQUAL TO y'))

    def test_is_greater_than(self):
        self.assertIn(TokenType.KW_IS_GREATER_THAN, types('x IS GREATER THAN y'))

    def test_is_less_than(self):
        self.assertIn(TokenType.KW_IS_LESS_THAN, types('x IS LESS THAN y'))

    def test_is_gte(self):
        self.assertIn(TokenType.KW_IS_GREATER_THAN_OR_EQUAL_TO, types('x IS GREATER THAN OR EQUAL TO y'))

    def test_is_lte(self):
        self.assertIn(TokenType.KW_IS_LESS_THAN_OR_EQUAL_TO, types('x IS LESS THAN OR EQUAL TO y'))


class TestLiterals(unittest.TestCase):
    def test_integer(self):
        toks = lex('42')
        self.assertEqual(toks[0].type, TokenType.NUMBER)
        self.assertEqual(toks[0].value, '42')

    def test_float(self):
        toks = lex('3.14')
        self.assertEqual(toks[0].type, TokenType.NUMBER)

    def test_string(self):
        toks = lex('"hello world"')
        self.assertEqual(toks[0].type, TokenType.STRING)
        self.assertEqual(toks[0].value, 'hello world')

    def test_identifier(self):
        toks = lex('myVar')
        self.assertEqual(toks[0].type, TokenType.IDENTIFIER)

    def test_operators(self):
        t = types('+ - * / %')
        self.assertIn(TokenType.PLUS, t)
        self.assertIn(TokenType.MINUS, t)
        self.assertIn(TokenType.STAR, t)
        self.assertIn(TokenType.SLASH, t)
        self.assertIn(TokenType.PERCENT, t)


class TestComments(unittest.TestCase):
    def test_comment_skipped_in_types(self):
        # Comment token should be in raw list but filtered in types()
        raw = lex('# this is a comment\nPRINT x')
        comment_types = [t.type for t in raw]
        self.assertIn(TokenType.COMMENT, comment_types)

    def test_code_after_comment(self):
        t = types('# comment\nPRINT x')
        self.assertIn(TokenType.PRINT, t)


class TestLineColumn(unittest.TestCase):
    def test_line_number(self):
        toks = lex('SET x TO 1\nPRINT x')
        print_tok = next(t for t in toks if t.type == TokenType.PRINT)
        self.assertEqual(print_tok.line, 2)

    def test_column_number(self):
        toks = lex('SET x TO 1')
        set_tok = next(t for t in toks if t.type == TokenType.SET)
        self.assertEqual(set_tok.column, 1)


class TestErrors(unittest.TestCase):
    def test_unterminated_string(self):
        lexer = Lexer('"unterminated')
        lexer.tokenize()
        self.assertTrue(len(lexer.errors) > 0)

    def test_unknown_char(self):
        lexer = Lexer('@unknown')
        lexer.tokenize()
        self.assertTrue(len(lexer.errors) > 0)


if __name__ == '__main__':
    unittest.main()
