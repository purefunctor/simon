import typing as t

import attr

from simon.utils import _compute_row_col


class SimonError(Exception):
    """Base exception for the library."""


@attr.s(frozen=True, slots=True)
class TextError(SimonError):
    """Contains extra failture metadata."""

    text: str = attr.ib()
    position: int = attr.ib()

    def __attrs_post_init__(self, *arguments: t.Any) -> None:
        super().__init__(*arguments)

    def __str__(self) -> str:
        return f"Text error at position {self.position}"

    @property
    def character(self) -> str:
        return self.text[self.position]

    @property
    def row_col(self) -> tuple[int, int]:
        return _compute_row_col(self.text, self.position)


class UnknownTokenError(TextError):
    """Raised during lexical analysis on unrecognized tokens."""

    def __str__(self) -> str:
        return f"Invalid character {self.character} at position {self.position}"
