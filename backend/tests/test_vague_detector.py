from app.interview.vague_detector import detect_vague_flags


def test_flags_unexplained_scalability_claim():
    flags = detect_vague_flags("I used MongoDB because it's scalable.")
    assert any("scalable" in f for f in flags)


def test_flags_unexplained_speed_claim():
    flags = detect_vague_flags("We picked Redis because it is faster.")
    assert any("faster" in f for f in flags)


def test_does_not_flag_an_explained_claim():
    # Says "scalable" but actually explains the mechanism - the spec's own
    # example of what a *good* answer looks like (section 12).
    flags = detect_vague_flags(
        "MongoDB's horizontal sharding lets us partition the collection "
        "across nodes by a shard key, so write throughput scales roughly "
        "linearly as we add shards - that's what I mean by scalable here."
    )
    assert flags == []


def test_flags_very_short_answers():
    flags = detect_vague_flags("It works well.")
    assert any("short" in f for f in flags)


def test_empty_answer_is_not_double_flagged_as_short():
    # An empty answer is a completeness problem, not "vague" - the length
    # check should skip whitespace-only input rather than flag it as short.
    assert detect_vague_flags("   ") == []
