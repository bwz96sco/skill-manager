from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Iterable


TOKEN_RE = re.compile(r"[A-Za-z0-9_.+#-]+|[\u4e00-\u9fff]{1,3}", re.UNICODE)


def normalize(text: object) -> str:
    return str(text or "").strip().casefold()


def tokens(text: object) -> list[str]:
    return [match.group(0).casefold() for match in TOKEN_RE.finditer(str(text or ""))]


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cosine(left: Iterable[str], right: Iterable[str]) -> float:
    a = Counter(left)
    b = Counter(right)
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    numerator = sum(a[key] * b[key] for key in common)
    left_norm = math.sqrt(sum(value * value for value in a.values()))
    right_norm = math.sqrt(sum(value * value for value in b.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def keyword_hits(query: str, values: Iterable[str]) -> list[str]:
    haystack = normalize(query)
    hits: list[str] = []
    for value in values:
        needle = normalize(value)
        if needle and needle in haystack:
            hits.append(str(value))
    return hits
