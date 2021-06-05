from __future__ import annotations

import re
import typing as t

import attr

from simon.node import Node


@attr.s(slots=True, cmp=False)
class ParserState:
    text: str = attr.ib()
    position: int = attr.ib()
    cache: dict = attr.ib(factory=dict)

    def mark(self) -> int:
        return self.position

    def move(self, position: int) -> None:
        self.position = position


_R = t.TypeVar("_R")


class _Expression(t.Protocol[_R]):
    action: t.Callable[..., _R]

    def parse(self, state: ParserState) -> t.Optional[_R]:
        cache_key = id(self), state.position
        try:
            return state.cache[cache_key]
        except KeyError:
            if (result := self._parse(state)) is not None:
                _result = self.action(result)
                state.cache[cache_key] = _result
                return _result
            else:
                state.cache[cache_key] = None
                return None

    def _parse(self, state: ParserState) -> t.Any:
        raise NotImplementedError


@attr.s(slots=True, cmp=False)
class Expression(_Expression[_R]):
    action: t.Callable[..., _R] = attr.ib(kw_only=True)


class _Pattern(Expression[_R]):
    _pattern: t.Pattern[str]

    def _parse(self, state: ParserState) -> t.Any:
        position = state.mark()
        if (result := self._pattern.match(state.text, state.position)) is not None:
            state.move(result.end(0))
            return Node([result.group(0)], position, state.position)
        return None


@attr.s(slots=True, cmp=False)
class Literal(_Pattern[_R]):
    literal: str = attr.ib()
    _pattern: t.Pattern[str] = attr.ib(
        init=False,
        repr=False,
        default=attr.Factory(
            lambda self: re.compile(re.escape(self.literal)), takes_self=True
        ),
    )


@attr.s(slots=True, cmp=False)
class RegEx(_Pattern[_R]):
    pattern: str = attr.ib()
    _pattern: t.Pattern[str] = attr.ib(
        init=False,
        repr=False,
        default=attr.Factory(lambda self: re.compile(self.pattern), takes_self=True),
    )


_I = t.TypeVar("_I")


@attr.s(slots=True, cmp=False)
class _Compound(t.Generic[_I, _R], Expression[_R]):
    inner: _I = attr.ib()


@attr.s(slots=True, cmp=False)
class Optional(_Compound[Expression, _R]):
    def _parse(self, state: ParserState) -> t.Any:
        position = state.mark()
        if (result := self.inner.parse(state)) is not None:
            return result
        state.move(position)
        return Node([], position, position)


@attr.s(slots=True, cmp=False)
class Some(_Compound[Expression, _R]):
    def _parse(self, state: ParserState) -> t.Any:
        results = []
        start = current = state.mark()
        while (result := self.inner.parse(state)) is not None:
            if state.position - current == 0:
                break
            results.append(result)
            current = state.mark()
        return Node(results, start, current)


@attr.s(slots=True, cmp=False)
class Many(_Compound[Expression, _R]):
    def _parse(self, state: ParserState) -> t.Any:
        start = state.mark()
        child = self.inner.parse(state)
        if child is None:
            state.move(start)
            return None

        results = [child]
        current = state.mark()
        while (result := self.inner.parse(state)) is not None:
            if state.position - current == 0:
                break
            results.append(result)
            current = state.mark()
        return Node(results, start, current)


@attr.s(slots=True, cmp=False)
class PositiveLookahead(_Compound[Expression, _R]):
    def _parse(self, state: ParserState) -> t.Any:
        position = state.mark()
        if self.inner.parse(state) is not None:
            state.move(position)
            return None
        return Node([], position, position)


@attr.s(slots=True, cmp=False)
class NegativeLookahead(_Compound[Expression, _R]):
    def _parse(self, state: ParserState) -> t.Any:
        position = state.mark()
        if self.inner.parse(state) is not None:
            state.move(position)
            return Node([], position, position)
        return None


@attr.s(slots=True, cmp=False)
class Sequence(_Compound[list[Expression], _R]):
    def _parse(self, state: ParserState) -> t.Any:
        results = []
        position = state.mark()
        for expression in self.inner:
            if (result := expression.parse(state)) is not None:
                results.append(result)
            else:
                state.move(position)
                return None
        else:
            return Node(results, position, state.position)


@attr.s(slots=True, cmp=False)
class Alternatives(_Compound[list[Expression], _R]):
    def _parse(self, state: ParserState) -> t.Any:
        position = state.mark()
        for alternative in self.inner:
            if (result := alternative.parse(state)) is not None:
                return result
            else:
                state.move(position)
        else:
            return None


_S = t.TypeVar("_S")


@attr.s(slots=True, cmp=False)
class Rule(t.Generic[_R, _S], Expression[_R]):
    name: str = attr.ib()
    expr: Expression[_S] = attr.ib()

    def _parse(self, state: ParserState) -> t.Any:
        if (result := self.expr.parse(state)) is not None:
            if isinstance(result, Node):
                result.tag = self.name
            return result
        return None
