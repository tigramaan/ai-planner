import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher

IGNORED_WORDS = {
    "задача", "задачу", "задаче", "напоминание", "напоминания", "мероприятие",
    "встреча", "встречу", "встречи", "событие", "события", "созвон", "созвона",
    "поменяй", "измени", "изменить", "перенеси", "перенести", "удали", "удалить",
    "заверши", "выполни", "отмени", "отменить", "сегодня", "завтра", "пожалуйста",
    "task", "reminder", "meeting", "event", "call", "change", "move", "delete",
    "добавь", "сегодняшнюю", "complete", "cancel", "add", "today", "tomorrow",
    "please", "with",
}


def text_words(value: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[\w@.+-]+", value.casefold().replace("ё", "е"))
        if len(token) > 1 and token not in IGNORED_WORDS
    ]


def word_similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    prefix = min(5, len(left), len(right))
    if prefix >= 4 and left[:prefix] == right[:prefix]:
        return 0.92
    return SequenceMatcher(None, left, right).ratio()


def text_relevance(candidate: str, query: str) -> float:
    query_words = text_words(query)
    candidate_words = text_words(candidate)
    if not query_words or not candidate_words:
        return 0.0
    matches = [
        max(word_similarity(query_word, candidate_word) for candidate_word in candidate_words)
        for query_word in query_words
    ]
    return sum(matches) / len(matches)


@dataclass(frozen=True)
class MatchResult[T]:
    match: T | None
    alternatives: list[T]


def best_text_match[T](
    rows: Iterable[T], query: str, text: Callable[[T], str]
) -> MatchResult[T]:
    ranked = sorted(
        ((row, text_relevance(text(row), query)) for row in rows),
        key=lambda item: item[1],
        reverse=True,
    )
    strong = [(row, score) for row, score in ranked if score >= 0.72]
    if not strong:
        return MatchResult(None, [])
    top_score = strong[0][1]
    close = [row for row, score in strong if top_score - score < 0.18]
    if len(close) > 1:
        return MatchResult(None, close[:5])
    return MatchResult(strong[0][0], [])
