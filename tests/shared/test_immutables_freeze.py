from types import MappingProxyType
from decimal import Decimal
from enum import Enum, auto

from app.shared.utils.immutables import freeze, is_frozen_mapping

class E(Enum):
    A = auto()

def test_freeze_scalars():
    assert freeze(None) is None
    assert freeze(1) == 1
    assert freeze(Decimal("1.0")) == Decimal("1.0")
    assert freeze(E.A) is E.A
    assert freeze("x") == "x"
    assert freeze(b"x") == b"x"

def test_freeze_dict_nested():
    src = {"a": {"b": [1, 2], "c": {"d": 3}}, "s": {1, 2}}
    frozen = freeze(src)
    assert isinstance(frozen, MappingProxyType)
    assert is_frozen_mapping(frozen)
    assert isinstance(frozen["a"], MappingProxyType)
    assert tuple == type(frozen["a"]["b"])
    assert isinstance(frozen["a"]["c"], MappingProxyType)
    assert frozenset == type(frozen["s"])

def test_freeze_list_tuple_set():
    assert freeze([1, 2, 3]) == (1, 2, 3)
    assert freeze((1, 2, 3)) == (1, 2, 3)
    assert freeze({1, 2, 3}) == frozenset({1, 2, 3})

def test_freeze_immutability_enforced():
    frozen = freeze({"a": 1, "b": [2, 3]})
    try:
        frozen["a"] = 2  # type: ignore[index]
        assert False, "MappingProxyType must be immutable"
    except TypeError:
        pass
    try:
        frozen["b"][0] = 9  # type: ignore[index]
        assert False, "Nested tuple must be immutable"
    except TypeError:
        pass