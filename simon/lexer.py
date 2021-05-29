from __future__ import annotations

import typing as t

import attr

from simon.errors import ParsingError


@attr.s(frozen=True, slots=True)
class Token:
    """Key-value pair of a `type_` and a `value`."""

    type_: str = attr.ib()
    value: str = attr.ib()


@attr.s
class TokenStream:
    """Generates tokens from text and patterns."""

    text: str = attr.ib(on_setattr=attr.setters.frozen)
    patterns: dict[str, t.Pattern[str]] = attr.ib(on_setattr=attr.setters.frozen)

    _text_idx: int = attr.ib(init=False, default=0)

    def _generate_token(self) -> t.Optional[Token]:
        if self._text_idx >= len(self.text):
            return None
        for terminal, pattern in self.patterns.items():
            if match := pattern.match(self.text, self._text_idx):
                self._text_idx = match.end(0)
                return Token(terminal, match.group(0))
        else:
            raise ParsingError(
                self.text, self.text[self._text_idx], self._text_idx, self.row_col
            )

    def __iter__(self) -> TokenStream:
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
    patterns: dict[str, t.Pattern[str]] = attr.ib(on_setattr=attr.setters.frozen)

    _tokens: list[Token] = attr.ib(init=False, factory=list)
    _token_idx: int = attr.ib(init=False, default=0)

    _token_stream: TokenStream = attr.ib(
        init=False,
        default=attr.Factory(
            lambda self: TokenStream(self.text, self.patterns), takes_self=True
        ),
    )

    def peek_token(self) -> t.Optional[Token]:
        if self._token_idx == len(self._tokens):
            token = next(self._token_stream, None)
            if token is not None:
                self._tokens.append(token)
            else:
                return None
        return self._tokens[self._token_idx]

    def next_token(self) -> t.Optional[Token]:
        token = self.peek_token()
        self._token_idx += 1
        return token

    def mark(self) -> int:
        return self._token_idx

    def rewind(self, idx: int) -> None:
        self._token_idx = idx
