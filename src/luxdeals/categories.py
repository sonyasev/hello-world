from __future__ import annotations

import re

# order matters: first match wins
_RULES: list[tuple[str, str]] = [
    ("shoes", r"sneaker|boot|pump|sandal|loafer|heel|mule|ballerina|ballet flat|slingback|espadrille|shoe|trainer|slide"),
    ("bags", r"\bbag\b|tote|clutch|purse|satchel|crossbody|backpack|handbag|wallet|pouch"),
    ("dresses", r"dress|gown|jumpsuit|playsuit|romper"),
    ("outerwear", r"coat|jacket|blazer|trench|parka|puffer|cape|poncho|gilet|vest|bomber|anorak"),
    ("bottoms", r"trouser|pant|jean|skirt|short|legging|denim|culotte|chino|jogger"),
    ("tops", r"top\b|shirt|blouse|sweater|jumper|knit|cardigan|tee\b|t-shirt|hoodie|sweatshirt|bodysuit|tank|camisole|polo|turtleneck|pullover"),
]


def infer_category(title: str, hint: str | None = None) -> str | None:
    text = f"{hint or ''} {title}".lower()
    for cat, pattern in _RULES:
        if re.search(pattern, text):
            return cat
    return None
