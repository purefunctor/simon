from __future__ import annotations

import typing as t

import attr


@attr.s(frozen=True, slots=True)
class Token:
    """Key-value pair of a `type_` and a `value`."""

    type_: str = attr.ib()
    value: str = attr.ib()


@attr.s
class TokenGenerator:
    """Generates tokens from text and parsing rules."""

    text: str = attr.ib(on_setattr=attr.setters.frozen)
    rules: dict[str, t.Pattern[str]] = attr.ib(on_setattr=attr.setters.frozen)

    _text_idx: int = attr.ib(init=False, default=0)

    def _generate_token(self) -> t.Optional[Token]:
        if self._text_idx >= len(self.text):
            return None
        for rule, pattern in self.rules.items():
            if match := pattern.match(self.text, self._text_idx):
                self._text_idx = match.end(0)
                return Token(rule, match.group(0))
        else:
            raise LexingError(
                self.text, self.text[self._text_idx], self._text_idx, self.row_col
            )

    def __iter__(self) -> TokenGenerator:
        return self

    def __next__(self) -> Token:
        if (token := self._generate_token()) is None:
            raise StopIteration
        return token

    @property
    def row_col(self) -> tuple[int, int]:
        row = 1
        col = 1
        current = 0
        while current != self._text_idx:
            if self.text[current] == "\n":
                row += 1
                col = 0
            col += 1
            current += 1
        return (row, col)


@attr.s
class Lexer:
    """Provides an API for stateful on-demand lexing."""

    text: str = attr.ib(on_setattr=attr.setters.frozen)
    rules: dict[str, t.Pattern[str]] = attr.ib(on_setattr=attr.setters.frozen)

    _tokens: list[Token] = attr.ib(init=False, factory=list)
    _token_idx: int = attr.ib(init=False, default=0)

    _token_generator: TokenGenerator = attr.ib(
        init=False,
        default=attr.Factory(
            lambda self: TokenGenerator(self.text, self.rules), takes_self=True
        ),
    )

    def peek_token(self) -> Token:
        if self._token_idx == len(self._tokens):
            self._tokens.append(next(self._token_generator))
        return self._tokens[self._token_idx]

    def next_token(self) -> Token:
        token = self.peek_token()
        self._token_idx += 1
        return token

    def mark(self) -> int:
        return self._token_idx

    def rewind(self, idx: int) -> None:
        self._token_idx = idx


class LexingError(Exception):
    """Raised during lexing, containing error metadata."""

    def __init__(
        self, text: str, character: str, position: int, row_col: tuple[int, int]
    ) -> None:
        self.text = text
        self.character = character
        self.position = position
        self.row_col = row_col

    def __str__(self) -> str:
        return f"Invalid character {self.character} at position {self.position}"
