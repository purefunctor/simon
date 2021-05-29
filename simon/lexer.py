import typing as t

import attr


@attr.s(frozen=True, slots=True)
class Token:
    """Key-value pair of a `type_` and a `value`."""
    type_: str = attr.ib()
    value: str = attr.ib()


@attr.s
class Lexer:
    """Provides an API for stateful on-demand lexing."""

    text: str = attr.ib(on_setattr=attr.setters.frozen)
    rules: dict[str, t.Pattern[str]] = attr.ib(on_setattr=attr.setters.frozen)

    _position: int = attr.ib(init=False, default=0)

    def next_token(self) -> t.Optional[Token]:
        if self._position >= len(self.text):
            return None
        for rule, pattern in self.rules.items():
            if match := pattern.match(self.text, self._position):
                self._position = match.end(0)
                return Token(rule, match.group(0))
        else:
            raise LexingError(
                self.text, self.current, self._position, self.row_col
            )

    def iter_until_eof(self) -> t.Iterable[Token]:
        while (token := self.next_token()) is not None:
            yield token

    @property
    def current(self) -> str:
        return self.text[self.position]

    def reset(self) -> None:
        self._position = 0

    @property
    def position(self) -> int:
        return self._position

    @property
    def row_col(self) -> tuple[int, int]:
        row = 1
        col = 1
        current = 0
        while current != self.position:
            if self.text[current] == "\n":
                row += 1
                col = 0
            col += 1
            current += 1
        return (row, col)


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
