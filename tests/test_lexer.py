import re

import pytest

from simon.lexer import Lexer, LexingError, Token, TokenGenerator


RULES = {
    "WHITESPACE": re.compile(r"\s+"),
    "NAME": re.compile("[A-Za-z]+"),
    "INTEGER": re.compile(r"\d+"),
}


class TestTokenGenerator:
    def test_TokenGenerator_iter(self) -> None:
        token_generator = TokenGenerator("guido 1991", RULES)

        assert iter(token_generator) is token_generator

    def test_TokenGenerator_next(self) -> None:
        token_generator = TokenGenerator("guido 1991", RULES)

        assert next(token_generator) == Token("NAME", "guido")
        assert next(token_generator) == Token("WHITESPACE", " ")
        assert next(token_generator) == Token("INTEGER", "1991")
        with pytest.raises(StopIteration):
            next(token_generator)

    def test_invalid_character_raises_LexingError(self) -> None:
        token_generator = TokenGenerator("1 + 1", RULES)

        with pytest.raises(
            LexingError, match=r"Invalid character \+ at position 2"
        ) as excinfo:
            _ = list(token_generator)

        assert excinfo.value.text == "1 + 1"
        assert excinfo.value.character == "+"
        assert excinfo.value.position == 2
        assert excinfo.value.row_col == (1, 3)

    def test_row_col_shows_rich_line_information(self) -> None:
        text = "abcdef\n123456"
        token_generator = TokenGenerator(text, RULES)
        token_generator._text_idx = text.find("6")

        assert token_generator.row_col == (2, 6)


class TestLexer:
    def test_next_token(self) -> None:
        lexer = Lexer("guido 1991", RULES)
        tokens = [
            Token("NAME", "guido"),
            Token("WHITESPACE", " "),
            Token("INTEGER", "1991"),
        ]

        for token in tokens:
            assert lexer.next_token() == token

        assert lexer._tokens == tokens

    def test_peek_token(self) -> None:
        lexer = Lexer("guido 1991", RULES)
        pos = lexer.mark()
        lexer.next_token()
        lexer.next_token()
        lexer.rewind(pos)

        assert lexer.peek_token() == Token("NAME", "guido")
        assert lexer._token_idx == pos
        assert lexer._tokens == [
            Token("NAME", "guido"),
            Token("WHITESPACE", " "),
        ]

    def test_mark(self) -> None:
        lexer = Lexer("guido 1991", RULES)

        assert lexer.mark() == lexer._token_idx

    def test_rewind(self) -> None:
        lexer = Lexer("guido 1991", RULES)
        lexer.next_token()
        lexer.next_token()

        lexer.rewind(0)

        assert lexer._token_idx == 0
