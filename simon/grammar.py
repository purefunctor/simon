from __future__ import annotations

import re
import typing as t

import attr


@attr.s(frozen=True, slots=True)
class Parser:
    grammar: Grammar = attr.ib()
    _states: dict = attr.ib(init=False, repr=False, factory=dict)

    def parse(self, text: str, position: int = 0) -> t.Any:
        state = ParserState(text, position, {})
        if text not in self._states:
            self._states[text] = state
        return self.grammar.parse(state)


@attr.s(slots=True)
class ParserState:
    text: str = attr.ib()
    position: int = attr.ib()
    cache: dict = attr.ib(factory=dict)

    def mark(self) -> int:
        return self.position

    def move(self, position: int) -> None:
        self.position = position


@attr.s(frozen=True, slots=True)
class Grammar:
    """Represents the Parsing Expression Grammar

    PEGs are defined as the following:

    Σ : a finite set of terminals

    N : a finite set of nonterminals

    P : a finite set of parsing rules
      | where
        : A ← e, A ∈ N, e is a parsing expression

    e_s : the "starting" expression
    """

    rules: dict[str, Rule] = attr.ib()
    start: str = attr.ib(default="start")

    @classmethod
    def from_list(cls, *rules: Rule, start: str = "start") -> Grammar:
        return cls({rule.name: rule for rule in rules}, start)

    def parse(self, state: ParserState) -> t.Any:
        return self.rules[self.start].parse(state, self)


_E = t.TypeVar("_E", bound="Expression")


@attr.s
class Expression:
    """Abstract base class for expressions"""

    _action: t.Callable[[Node], t.Any] = attr.ib(
        init=False, default=lambda n: n, repr=False
    )

    def parse(self, state: ParserState) -> t.Any:
        # TODO: Perhaps we can approach caching differently as
        # to not blow up memory when parsing larger text.
        key = id(self), state.position
        if key not in state.cache:
            if (result := self._parse(state)) is not None:
                _result = self._action(result)
                state.cache[key] = _result
                return _result
        else:
            return state.cache[key]
        state.cache[key] = None
        return None

    def _parse(self, state: ParserState) -> t.Any:
        raise NotImplementedError


@attr.s(slots=True)
class Rule(Expression):
    """Represents a rule definition in the PEG"""

    name: str = attr.ib()
    expr: Expression = attr.ib()

    def _parse(self, state: ParserState) -> t.Any:
        if (result := self.expr.parse(state)) is not None:
            if isinstance(result, Node):
                result.type_ = self.name
            return result
        return None


@attr.s(slots=True)
class Literal(Expression):
    """Represents a string literal or inline terminal"""

    literal: str = attr.ib()
    _pattern: t.Pattern[str] = attr.ib(
        init=False,
        repr=False,
        default=attr.Factory(
            lambda self: re.compile(re.escape(self.literal)), takes_self=True
        ),
    )

    def _parse(self, state: ParserState) -> t.Any:
        position = state.mark()
        if (result := self._pattern.match(state.text, state.position)) is not None:
            # `Literal`s and `RegEx`s are the smallest units of
            # expressions in the class hierarchy. As such, they
            # must advance the current position in the state.
            state.move(result.end(0))
            return Node([result.group(0)], position, state.position)
        return None


@attr.s(slots=True)
class RegEx(Expression):
    """Represents an arbitrary regular expression"""

    pattern: str = attr.ib()
    _pattern: t.Pattern[str] = attr.ib(
        init=False,
        repr=False,
        default=attr.Factory(
            lambda self: re.compile(re.escape(self.literal)), takes_self=True
        ),
    )

    def _parse(self, state: ParserState) -> t.Any:
        position = state.mark()
        if (result := self._pattern.match(state.text, state.position)) is not None:
            # `Literal`s and `RegEx`s are the smallest units of
            # expressions in the class hierarchy. As such, they
            # must advance the current position in the state.
            state.move(result.end(0))
            return Node([result.group(0)], position, state.position)
        return None


@attr.s(slots=True)
class Alts(Expression):
    """Represents ordered choice of expressions"""

    alts: list[Expression] = attr.ib()

    def _parse(self, state: ParserState) -> t.Any:
        position = state.mark()
        for alt in self.alts:
            if (result := alt.parse(state)) is not None:
                # Immediately return result if an alternative parses
                return result
            else:
                # Else, backtrack to the previous position
                state.move(position)
        else:
            # Fail if no alternatives are matched
            return None


@attr.s(slots=True)
class Sequence(Expression):
    """Represents a sequence of parsing expressions"""

    expressions: list[Expression] = attr.ib()

    def _parse(self, state: ParserState) -> t.Any:
        results = []
        position = state.mark()
        for expression in self.expressions:
            if (result := expression.parse(state)) is not None:
                # Append to `results` if an expression parses
                results.append(result)
            else:
                # Else, backtrack to previous position and fail
                state.move(position)
                return None
        else:
            # Return `results` if all expressions are matched
            return Node(results, position, state.position)


@attr.s(slots=True)
class Optional(Expression):
    """Represents an expression that may not be present"""

    optional: Expression = attr.ib()

    def _parse(self, state: ParserState) -> t.Any:
        position = state.mark()
        if (result := self.optional.parse(state)) is not None:
            # Immediately return result if an expression parses
            return result
        # Otherwise, backtrack to the previous position
        state.move(position)
        return Node([], position, position)


@attr.s(slots=True)
class Some(Expression):
    """Represents zero or more expressions"""

    expression: Expression = attr.ib()

    def _parse(self, state: ParserState) -> t.Any:
        results = []
        position = current = state.mark()
        while result := self.expression.parse(state):
            if state.position - current == 0:  # Guard against "empty" nodes
                break
            results.append(result)
            current = state.mark()  # Advance to the next position
        return Node(results, position, current)


@attr.s(slots=True)
class Many(Expression):
    """Represents one or more expressions"""

    expression: Expression = attr.ib()

    def _parse(self, state: ParserState) -> t.Any:
        # Ensure that at least one item is present
        position = state.mark()
        child = self.expression.parse(state)
        if child is None:
            state.move(position)
            return None

        # This block is functionally equivalent to `Some`,
        # with `results` being prefixed with `child`
        results = [child]
        position = current = state.mark()
        while result := self.expression.parse(state):
            if state.position - current == 0:
                break
            results.append(result)
            current = state.mark()
        return Node(results, position, current)


@attr.s(slots=True)
class PositiveLookahead(Expression):
    """Represents a positive lookahead"""

    expression: Expression = attr.ib()

    def _parse(self, state: ParserState) -> t.Any:
        # If an expression successfully parses, return an
        # empty node, failing the parse otherwise.
        position = state.mark()
        if self.expression.parse(state):
            state.move(position)
            return Node([], position, position)
        return None


@attr.s(slots=True)
class NegativeLookahead(Expression):
    """Represents a negative lookahead

    Fails if a given expression matches, an empty Node is returned otherwise.
    """

    expression: Expression = attr.ib()

    def _parse(self, state: ParserState) -> t.Any:
        # If an expression successfully parses, fail the
        # parse, returning an empty node otherwise.
        position = state.mark()
        if self.expression.parse(state):
            state.move(position)
            return None
        return Node([], position, position)


_T = t.TypeVar("_T")


@attr.s(slots=True)
class Node(t.Generic[_T]):
    """Represents an AST node in the resulting parse tree"""

    children: list[_T] = attr.ib()
    start: int = attr.ib()
    end: int = attr.ib()
    type_: str = attr.ib(default="")
