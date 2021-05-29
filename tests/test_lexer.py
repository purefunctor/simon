import re

import pytest

from simon.lexer import Lexer, LexingError, Token


class TestLexer:
    RULES = {
        "WHITESPACE": re.compile(r"\s+"),
        "NAME": re.compile("[A-Za-z]+"),
        "INTEGER": re.compile(r"\d+"),
    }

    def test_next_token(self) -> None:
        lexer = Lexer("guido 1991", self.RULES)

        assert lexer.next_token() == Token("NAME", "guido")
        assert lexer.next_token() == Token("WHITESPACE", " ")
        assert lexer.next_token() == Token("INTEGER", "1991")
        assert lexer.next_token() is None

    def test_iter_until_eof(self) -> None:
        lexer = Lexer("guido 1991", self.RULES)
        expected = [
            Token("NAME", "guido"),
            Token("WHITESPACE", " "),
            Token("INTEGER", "1991"),
        ]

        result = list(lexer.iter_until_eof())

        assert result == expected

    def test_reset_goes_to_zero(self) -> None:
        lexer = Lexer("guido 1991", self.RULES)
        _ = list(lexer.iter_until_eof())

        lexer.reset()

        assert lexer.position == 0
        assert lexer.row_col == (1, 1)

    def test_invalid_character_raises_LexingError(self) -> None:
        lexer = Lexer("1 + 1", self.RULES)

        with pytest.raises(
            LexingError, match=r"Invalid character \+ at position 2"
        ) as excinfo:
            _ = list(lexer.iter_until_eof())

        assert excinfo.value.text == "1 + 1"
        assert excinfo.value.character == "+"
        assert excinfo.value.position == 2
        assert excinfo.value.row_col == (1, 3)

    def test_row_col_shows_rich_line_information(self) -> None:
        text = "abcdef\n123456"
        lexer = Lexer(text, self.RULES)
        lexer._position = text.find("6")

        assert lexer.row_col == (2, 6)
