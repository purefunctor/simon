from __future__ import annotations

import re
import typing as t

import attr


@attr.s(frozen=True, slots=True)
class Parser:
    grammar: Grammar = attr.ib()
    _caches: dict = attr.ib(init=False, repr=False, factory=dict)

    def parse(self, text: str, position: int = 0) -> t.Optional[Node]:
        if text not in self._caches:
            self._caches[text] = {}
        return self.grammar.parse(text, position, self._caches[text])


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

    def parse(
        self, text: str, position: int = 0, _cache: dict = None
    ) -> t.Optional[Node]:
        cache = {} if _cache is None else _cache
        return self.rules[self.start].match(text, position, self, cache)


class Expression:
    """Abstract base class for expressions"""

    def match(
        self,
        text: str,
        position: int,
        grammar: Grammar,
        cache: dict,
    ) -> t.Optional[Node]:
        key = (id(self), self.__class__.__name__, position)
        if key not in cache:
            if result := self._match(text, position, grammar, cache):
                cache[key] = result
                return result
        else:
            return cache[key]
        cache[key] = None
        return None

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        raise NotImplementedError


@attr.s(slots=True)
class Rule(Expression):
    """Represents a rule definition in the PEG"""

    name: str = attr.ib()
    expr: Expression = attr.ib()

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        if result := self.expr.match(text, position, grammar, cache):
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

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        if result := self._pattern.match(text, position):
            return Node([result.group(0)], position, result.end(0))
        return None


@attr.s(slots=True)
class RegEx(Expression):
    """Represents an arbitrary regular expression"""

    pattern: str = attr.ib()

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        pattern = re.compile(self.pattern)
        if result := pattern.match(text, position):
            return Node([result.group(0)], position, result.end(0))
        return None


@attr.s(slots=True)
class Alts(Expression):
    """Represents ordered choice of expressions"""

    alts: list[Expression] = attr.ib()

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        for alt in self.alts:
            if result := alt.match(text, position, grammar, cache):
                return result
        else:
            return None


@attr.s(slots=True)
class Sequence(Expression):
    """Represents a sequence of parsing expressions"""

    expressions: list[Expression] = attr.ib()

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        results = []
        _position = position
        for expression in self.expressions:
            if result := expression.match(text, _position, grammar, cache):
                results.append(result)
                _position = result.end
            else:
                return None
        else:
            return Node(results, position, _position)


@attr.s(slots=True)
class Optional(Expression):
    """Represents an expression that may not be present"""

    optional: Expression = attr.ib()

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        if result := self.optional.match(text, position, grammar, cache):
            return result
        return Node([], position, position)


@attr.s(slots=True)
class Some(Expression):
    """Represents zero or more expressions"""

    expression: Expression = attr.ib()

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        results = []
        _position = position
        while result := self.expression.match(text, _position, grammar, cache):
            if result.end - result.start == 0:
                break
            results.append(result)
            _position = result.end
        return Node(results, position, _position)


@attr.s(slots=True)
class Many(Expression):
    """Represents one or more expressions"""

    expression: Expression = attr.ib()

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        _position = position
        head = self.expression.match(text, position, grammar, cache)
        if head is None:
            return None
        _position = head.end
        results = [head]
        while result := self.expression.match(text, _position, grammar, cache):
            if result.end - result.start == 0:
                break
            results.append(result)
            _position = result.end
        return Node(results, position, _position)


@attr.s(slots=True)
class PositiveLookahead(Expression):
    """Represents a positive lookahead

    Returns an empty node if an expression matches, fails otherwise.
    """

    expression: Expression = attr.ib()

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        if self.expression.match(text, position, grammar, cache):
            return Node([], position, position)
        return None


@attr.s(slots=True)
class NegativeLookahead(Expression):
    """Represents a negative lookahead

    Fails if a given expression matches, an empty Node is returned otherwise.
    """

    expression: Expression = attr.ib()

    def _match(
        self, text: str, position: int, grammar: Grammar, cache: dict
    ) -> t.Optional[Node]:
        if self.expression.match(text, position, grammar, cache):
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
