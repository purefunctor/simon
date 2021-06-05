import typing as t

import attr


_C = t.TypeVar("_C")


@attr.s(slots=True)
class Node(t.Generic[_C]):
    children: list[_C] = attr.ib()
    start: int = attr.ib()
    end: int = attr.ib()
    tag: str = attr.ib(default="")


def _node_id(node: Node) -> Node:
    return node
