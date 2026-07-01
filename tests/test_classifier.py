from openprofile.classifier import IndustryClassifier


def test_viticulture_text_classifies_to_grape_growing():
    clf = IndustryClassifier()
    text = ("Family owned vineyard in the Barossa Valley. We grow shiraz and cabernet "
            "grapes and run a cellar door with estate wine tastings.")
    results = clf.classify(text, top_k=3)
    assert results, "expected at least one classification"
    codes = {r.code for r in results}
    # grape growing and/or wine manufacturing should surface
    assert "0131" in codes or "1214" in codes
    top = results[0]
    assert 0.0 < top.confidence <= 0.99
    assert top.matched_terms


def test_horticulture_vegetable_grower():
    clf = IndustryClassifier()
    text = "We are a market garden growing broccoli, carrots and leafy salad vegetables."
    results = clf.classify(text)
    assert results[0].code == "0123"
    assert results[0].sector == "Horticulture"


def test_empty_text_returns_nothing():
    assert IndustryClassifier().classify("") == []


def test_confidence_scales_with_evidence():
    clf = IndustryClassifier()
    weak = clf.classify("grapes")
    strong = clf.classify("vineyard grapes viticulture wine grapes vines shiraz chardonnay")
    assert strong[0].confidence >= weak[0].confidence
