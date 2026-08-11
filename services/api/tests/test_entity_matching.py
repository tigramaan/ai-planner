from app.entity_matching import best_text_match, text_relevance


def test_flexible_title_match_accepts_fragments_inflection_and_word_order():
    title = "Отправить техзадание Роману в самолёт"

    assert text_relevance(title, "Роману техзадание") >= 0.9
    assert text_relevance(title, "техзадание в самолете") >= 0.9


def test_match_rejects_weak_guess_and_reports_close_candidates():
    rows = ["Позвонить Роману", "Отправить отчёт Роману", "Купить молоко"]

    ambiguous = best_text_match(rows, "Роману", lambda row: row)
    weak = best_text_match(rows, "Анастасии", lambda row: row)

    assert ambiguous.match is None
    assert ambiguous.alternatives == rows[:2]
    assert weak.match is None
    assert weak.alternatives == []
