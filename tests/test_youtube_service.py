from app.services.youtube_service import build_youtube_search_params


def test_build_youtube_search_params_uses_hebrew_locale():
    params = build_youtube_search_params("בנימין נתניהו podcast", language="he")

    assert params["search_query"] == "בנימין נתניהו podcast"
    assert params["hl"] == "he"
    assert params["gl"] == "IL"
    assert params["lr"] == "lang_he"


def test_build_youtube_search_params_defaults_to_english():
    params = build_youtube_search_params("politics podcast", language="en")

    assert params["search_query"] == "politics podcast"
    assert params["hl"] == "en"
    assert params["gl"] == "US"
