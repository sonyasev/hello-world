"""Size parsing and matching against the user's size profile.

Sizes are normalised to (system, value) tuples, e.g. ("UK", 10), ("IT", 42),
("INTL", "M"), ("EU", 38.5), ("W", 29). Only explicitly labelled sizes are
trusted, except bare numbers, which are resolved per category through the
`bare_numbers` config (shoes: always EU; bottoms: e.g. {"40": "EU", "29": "W"}).
"""
from __future__ import annotations

import re

Size = tuple[str, float | str]

_INTL = {"XXS", "XS", "S", "M", "L", "XL", "XXL"}
_INTL_WORDS = {"SMALL": "S", "MEDIUM": "M", "LARGE": "L"}
_NUM = r"(\d{1,2}(?:[.,]5)?)"


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def parse_size(raw: str, category: str | None = None, bare_numbers: dict | None = None) -> Size | None:
    s = re.sub(r"\s+", " ", raw.strip().upper().replace("½", ".5"))
    if not s:
        return None
    if s in _INTL:
        return ("INTL", s)
    if s in _INTL_WORDS:
        return ("INTL", _INTL_WORDS[s])
    for system in ("UK", "IT", "EU", "DE"):
        m = re.fullmatch(rf"{system}[ :]?{_NUM}", s) or re.fullmatch(rf"{_NUM} ?{system}", s)
        if m:
            return ("EU" if system == "DE" else system, _num(m.group(1)))
    m = re.fullmatch(rf"(?:W|WAIST)[ :]?{_NUM}(?:\s*[xX/]\s*L?\d+)?", s) or re.fullmatch(r"(\d{2})\s*[/xX]\s*\d{2}", s)
    if m:  # waist, e.g. W29, W29/L32, 29/32
        return ("W", _num(m.group(1)))
    m = re.fullmatch(_NUM, s)
    if m and category:
        v = _num(m.group(1))
        if category == "shoes":
            return ("EU", v)
        system = (bare_numbers or {}).get(category, {}).get(m.group(1).replace(",", "."))
        if system:
            return (system, v)
    return None


class SizeProfile:
    def __init__(self, cfg: dict):
        self.bare = cfg.get("bare_numbers", {})
        self.wanted: dict[str, set[Size]] = {}
        for group, entries in cfg.items():
            if group == "bare_numbers":
                continue
            parsed = set()
            for e in entries:
                p = parse_size(str(e), category="shoes" if group == "shoes" else None)
                if p is None:
                    raise ValueError(f"cannot parse configured size {e!r} in {group!r}")
                parsed.add(p)
            self.wanted[group] = parsed

    def group_for(self, category: str | None) -> str | None:
        return {
            "tops": "upper", "dresses": "upper", "outerwear": "upper",
            "bottoms": "bottoms", "shoes": "shoes",
        }.get(category or "")

    def matches(self, category: str | None, raw_sizes: list[str]) -> list[str]:
        """Return the raw sizes (from the store) that fit the profile."""
        if category == "bags":
            return ["one size"]
        group = self.group_for(category)
        if group is None or group not in self.wanted:
            return []
        out = []
        for raw in raw_sizes:
            p = parse_size(raw, category, self.bare)
            if p is not None and p in self.wanted[group]:
                out.append(raw)
        return out
