from app.services.blocs_service import build_ui_bloc_summary
from app.services.news_service import normalize_language


def test_normalize_language_defaults_to_hebrew():
    assert normalize_language(None) == "hebrew"
    assert normalize_language("") == "hebrew"
    assert normalize_language("he") == "hebrew"
    assert normalize_language("en") == "english"


def test_build_ui_bloc_summary_merges_arab_parties_into_opposition():
    parties = [
        {"name": "Likud", "seats": 32, "bloc": "coalition"},
        {"name": "Yesh Atid", "seats": 24, "bloc": "opposition"},
        {"name": "United Arab List (Ra'am)", "seats": 5, "bloc": "arab_parties"},
    ]

    summary = build_ui_bloc_summary(parties)

    assert set(summary.keys()) == {"coalition", "opposition"}
    assert summary["coalition"]["parties"][0]["name"] == "Likud"
    assert any(p["name"] == "United Arab List (Ra'am)" for p in summary["opposition"]["parties"])
