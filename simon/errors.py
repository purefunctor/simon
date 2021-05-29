class SimonError(Exception):
    """Base exception for the library."""


class ParsingError(SimonError):
    """Exception raised during parsing."""

    def __init__(
        self, text: str, character: str, position: int, row_col: tuple[int, int]
    ) -> None:
        super().__init__(text, character, position, row_col)
        self.text = text
        self.character = character
        self.position = position
        self.row_col = row_col

    def __str__(self) -> str:
        return f"Invalid character {self.character} at position {self.position}"
