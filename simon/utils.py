def _compute_row_col(text: str, position: int) -> tuple[int, int]:
    row = 1
    col = 1
    current = 0
    while current != position:
        if text[current] == "\n":
            row += 1
            col = 0
        col += 1
        current += 1
    return (row, col)
