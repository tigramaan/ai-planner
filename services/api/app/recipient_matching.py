import re
import unicodedata
from email.utils import parseaddr

TRANSLITERATION = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ы": "y", "э": "e", "ю": "yu", "я": "ya", "ь": "", "ъ": "",
    }
)
TECHNICAL_LOCAL_PART = re.compile(
    r"(^|[._+\-])(no-?reply|noreply|mailer|notifications?|redmine|support|sales)([._+\-]|$)",
    re.IGNORECASE,
)


def words(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold().replace("ё", "е")
    return re.findall(r"[^\W_]+", normalized, re.UNICODE)


def canonical_latin(token: str) -> str:
    if token.endswith("iya"):
        return token[:-3] + "ia"
    if token.endswith("iy"):
        return token[:-2] + "y"
    return token


def variants(value: str) -> list[list[str]]:
    direct = words(value)
    latin = [canonical_latin(token.translate(TRANSLITERATION)) for token in direct]
    return [direct, latin]


def name_score(query: str, candidate: str) -> int:
    best = 0
    for query_words in variants(query):
        for candidate_words in variants(candidate):
            if not query_words or not candidate_words:
                continue
            query_set, candidate_set = set(query_words), set(candidate_words)
            if query_set == candidate_set:
                best = max(best, 100)
            elif query_set <= candidate_set:
                best = max(best, 92)
            else:
                best = max(best, round(70 * len(query_set & candidate_set) / len(query_set)))
    return best


def address_score(query: str, email: str) -> int:
    local = parseaddr(email)[1].partition("@")[0]
    compact = "".join(words(local.translate(TRANSLITERATION)))
    query_words = variants(query)[1]
    if not compact or not query_words:
        return 0
    surname = query_words[-1]
    initial_match = len(query_words) > 1 and compact.startswith(query_words[0][:1])
    if surname in compact and (len(query_words) == 1 or initial_match):
        return 78
    return 45 if any(len(token) >= 3 and token in compact for token in query_words) else 0


def technical_address(email: str) -> bool:
    local = parseaddr(email)[1].partition("@")[0]
    return bool(TECHNICAL_LOCAL_PART.search(local))


def ranked_addresses(query: str, contacts: list[dict], messages: list[dict]) -> list[str]:
    candidates: dict[str, tuple[int, int]] = {}
    rows = [
        ("contact", row.get("name", ""), row.get("email", "")) for row in contacts
    ] + [
        ("mail", *parseaddr(row.get("from", ""))) for row in messages
    ]
    for source, name, email in rows:
        address = parseaddr(email)[1].casefold()
        if not address or "@" not in address or technical_address(address):
            continue
        score = max(name_score(query, name), address_score(query, address))
        if score < 90:
            continue
        source_rank = 1 if source == "contact" else 0
        previous = candidates.get(address)
        if previous is None or (score, source_rank) > previous:
            candidates[address] = (score, source_rank)
    ordered = sorted(candidates.items(), key=lambda row: (-row[1][0], -row[1][1], row[0]))
    return [address for address, _ in ordered[:3]]
