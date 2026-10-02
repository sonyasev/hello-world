"""Top 30 luxury brands and alias normalisation."""
from __future__ import annotations

import re
import unicodedata

BRANDS: dict[str, list[str]] = {
    "Gucci": [],
    "Prada": [],
    "Saint Laurent": ["ysl", "yves saint laurent"],
    "Bottega Veneta": [],
    "Loro Piana": [],
    "Burberry": [],
    "Max Mara": ["maxmara", "'s max mara", "s max mara", "weekend max mara"],
    "Celine": ["céline"],
    "Balenciaga": [],
    "Fendi": [],
    "Chanel": [],
    "Dior": ["christian dior"],
    "Hermès": ["hermes"],
    "Louis Vuitton": ["lv"],
    "Valentino": ["valentino garavani", "red valentino"],
    "Givenchy": [],
    "Miu Miu": [],
    "Moncler": [],
    "Brunello Cucinelli": [],
    "Alexander McQueen": ["mcqueen"],
    "Stella McCartney": [],
    "Chloé": ["chloe", "see by chloe"],
    "Isabel Marant": ["isabel marant etoile", "isabel marant étoile"],
    "Jil Sander": [],
    "The Row": [],
    "Loewe": [],
    "Maison Margiela": ["margiela", "mm6 maison margiela"],
    "Versace": ["versace jeans couture"],
    "Dolce & Gabbana": ["dolce gabbana", "d&g", "dolce and gabbana"],
    "Marni": [],
}


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower().replace("’", "'")).strip()


_ALIASES: dict[str, str] = {}
for _canon, _aliases in BRANDS.items():
    for _a in [_canon, *_aliases]:
        _ALIASES[_fold(_a)] = _canon


def normalize_brand(raw: str | None) -> str | None:
    """Map a store's brand string to a canonical top-30 brand, else None."""
    if not raw:
        return None
    return _ALIASES.get(_fold(raw))


def find_brand_in_title(title: str) -> str | None:
    t = f" {_fold(title)} "
    # longest alias first so "saint laurent" beats shorter collisions
    for alias in sorted(_ALIASES, key=len, reverse=True):
        if len(alias) > 3 and f" {alias} " in t:
            return _ALIASES[alias]
    return None
