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
