import typing as t

import attr


class SimonError(Exception):
    """Base exception for the library."""


@attr.s(frozen=True, slots=True)
class TextError(SimonError):
    """Contains extra failture metadata."""

    text: str = attr.ib()
    character: str = attr.ib()
    position: int = attr.ib()
    row_col: tuple[int, int] = attr.ib()

    def __attrs_post_init__(self, *arguments: t.Any) -> None:
        super().__init__(*arguments)

    def __str__(self) -> str:
        return f"Invalid character {self.character} at position {self.position}"


class UnknownTokenError(TextError):
    """Raised during lexical analysis on unrecognized tokens."""
