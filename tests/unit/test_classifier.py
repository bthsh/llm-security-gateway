from app.guard_a.classifier import InjectionClassifier


def test_classifier_sha256_caching():
    cls = InjectionClassifier()
    # Populate cache manually to test caching mechanism
    text = "Unique test sentence for caching"
    import hashlib
    key = hashlib.sha256(text.encode("utf-8")).hexdigest()
    cls._cache[key] = 0.95

    score = cls.predict_single(text)
    assert score == 0.95


def test_classifier_predict_batch_caching():
    cls = InjectionClassifier()
    import hashlib
    
    t1 = "Sentence number one"
    t2 = "Sentence number two"
    
    k1 = hashlib.sha256(t1.encode("utf-8")).hexdigest()
    k2 = hashlib.sha256(t2.encode("utf-8")).hexdigest()
    
    cls._cache[k1] = 0.88
    cls._cache[k2] = 0.12

    scores = cls.predict_batch([t1, t2])
    assert scores == [0.88, 0.12]


def test_classifier_graceful_fallback_on_error():
    # Unload pipeline and pass invalid model ID to test fallback
    cls = InjectionClassifier(model_id="invalid/nonexistent-model-id-xyz")
    score = cls.predict_single("Some text")
    assert score == 0.0  # Returns 0.0 without crashing


def test_classifier_empty_input_handling():
    cls = InjectionClassifier()
    assert cls.predict_single("") == 0.0
    assert cls.predict_batch([]) == []


def test_detect_with_classifier_layer_disabled():
    from app.models import RequestContext, Segment, LayerSettings, Chunk
    from app.guard_a.detect import run as run_detect

    ctx = RequestContext(
        request_id="req_nocls",
        session_id="sess_nocls",
        profile="customer_support",
        layers=LayerSettings(classifier=False),
        segments=[
            Segment(id="s1", source="user", trust="trusted", text="Normal text")
        ],
        chunks=[
            Chunk(id="c1", segment_id="s1", text="Normal text", is_hidden=False)
        ],
    )
    result = run_detect(ctx)
    assert result.status == "PASSED"
    # Ensure no classifier finding was appended
    assert not any(f.rule_id == "classifier" for f in result.findings)

