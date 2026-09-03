from app.resume.keyword_extractor import extract_known_technologies


def test_detects_known_languages_frameworks_databases_and_technologies():
    text = "Built with Python, FastAPI, MongoDB, and deployed on AWS using Docker."
    result = extract_known_technologies(text)
    assert "Python" in result["programming_languages"]
    assert "FastAPI" in result["frameworks"]
    assert "MongoDB" in result["databases"]
    assert "AWS" in result["technologies"]
    assert "Docker" in result["technologies"]


def test_is_case_insensitive():
    result = extract_known_technologies("built with python and mongodb")
    assert "Python" in result["programming_languages"]
    assert "MongoDB" in result["databases"]


def test_does_not_match_substrings_inside_unrelated_words():
    # "Java" must not match inside "JavaScript"
    result = extract_known_technologies("Experienced in JavaScript development.")
    assert "Java" not in result["programming_languages"]
    assert "JavaScript" in result["programming_languages"]


def test_matches_punctuation_heavy_terms():
    result = extract_known_technologies("Proficient in C++ and C#.")
    assert "C++" in result["programming_languages"]
    assert "C#" in result["programming_languages"]


def test_returns_empty_lists_for_text_with_no_known_technologies():
    result = extract_known_technologies("I am a highly motivated team player.")
    assert result == {
        "programming_languages": [],
        "frameworks": [],
        "databases": [],
        "technologies": [],
    }


def test_no_duplicate_entries_within_a_category():
    text = "Python Python Python developer with Python experience."
    result = extract_known_technologies(text)
    assert result["programming_languages"].count("Python") == 1
