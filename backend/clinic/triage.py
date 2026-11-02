import heapq
import time
from collections import defaultdict
from dataclasses import dataclass

TTL = 30
_c = {"t": 0.0, "m": None}
TREE = (lambda m: m >= 3, 1, (lambda m: m >= 2, 2, (lambda m: m >= 1, 3, 4)))


@dataclass(frozen=True, slots=True)
class Sym:
    severity: int
    category: str
    rules: tuple


@dataclass(frozen=True, slots=True)
class Result:
    dept: str
    category: str
    priority: int | None
    escalate: bool


def invalidate():
    _c["m"] = None


def symmap():
    if _c["m"] is None or time.monotonic() - _c["t"] > TTL:
        from .models import Symptom

        qs = Symptom.objects.filter(is_active=True).prefetch_related("rules__department")
        _c["m"] = {s.key: Sym(s.severity, s.emergency_category,
                              tuple((r.department.code, r.weight) for r in s.rules.all())) for s in qs}
        _c["t"] = time.monotonic()
    return _c["m"]


def run(kind, keys, age):
    m = symmap()
    try:
        syms = [m[k] for k in dict.fromkeys(keys)]
    except KeyError:
        raise ValueError
    top = max((s.severity for s in syms if s.category), default=0)
    if kind == "emergency":
        tot = defaultdict(int)
        for s in syms:
            if s.category:
                tot[s.category] += s.severity
        cat = max(("medical", "surgical"), key=lambda c: (tot[c], c == "medical"))
        node = TREE
        while isinstance(node, tuple):
            f, y, n = node
            node = y if f(top) else n
        return Result("EMERG_MED" if cat == "medical" else "EMERG_SURG", cat, node, False)
    sc = defaultdict(int)
    for s in syms:
        for d, w in s.rules:
            sc[d] += w
    if age < 14:
        sc["PAED"] += 3
    dept = max(sc, key=lambda d: (sc[d], d == "GENMED", d)) if sc else "GENMED"
    return Result(dept, "", None, top >= 3)


def ordered(rows):
    h = [(r.priority, r.triaged_at, r.pk, r) for r in rows]
    heapq.heapify(h)
    return [heapq.heappop(h)[3] for _ in range(len(h))]
