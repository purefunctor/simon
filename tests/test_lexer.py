import re

import pytest

from simon.lexer import Lexer, LexingError, Token, TokenStream


RULES = {
    "WHITESPACE": re.compile(r"\s+"),
    "NAME": re.compile("[A-Za-z]+"),
    "INTEGER": re.compile(r"\d+"),
}


class TestTokenStream:
    def test_TokenStream_iter(self) -> None:
        token_stream = TokenStream("guido 1991", RULES)

        assert iter(token_stream) is token_stream

    def test_TokenStream_next(self) -> None:
        token_stream = TokenStream("guido 1991", RULES)

        assert next(token_stream) == Token("NAME", "guido")
        assert next(token_stream) == Token("WHITESPACE", " ")
        assert next(token_stream) == Token("INTEGER", "1991")
        with pytest.raises(StopIteration):
            next(token_stream)

    def test_invalid_character_raises_LexingError(self) -> None:
        token_stream = TokenStream("1 + 1", RULES)

        with pytest.raises(
            LexingError, match=r"Invalid character \+ at position 2"
        ) as excinfo:
            _ = list(token_stream)

        assert excinfo.value.text == "1 + 1"
        assert excinfo.value.character == "+"
        assert excinfo.value.position == 2
        assert excinfo.value.row_col == (1, 3)

    def test_row_col_shows_rich_line_information(self) -> None:
        text = "abcdef\n123456"
        token_stream = TokenStream(text, RULES)
        token_stream._text_idx = text.find("6")

        assert token_stream.row_col == (2, 6)


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

        assert lexer.next_token() is None

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
