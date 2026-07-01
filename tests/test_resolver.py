from openprofile.models import Entity
from openprofile.resolver import name_similarity, pick_best, rank_candidates


def test_name_similarity_ignores_legal_suffixes():
    assert name_similarity("Yalumba Pty Ltd", "Yalumba") > 0.9


def test_ranking_orders_by_match():
    cands = [
        Entity(name="Barossa Grape Growers Co-op", abn="1"),
        Entity(name="Barossa Valley Estate Wines Pty Ltd", abn="2", state="SA"),
    ]
    ranked = rank_candidates("Barossa Valley Estate", cands, state="SA")
    assert ranked[0].name.startswith("Barossa Valley Estate")


def test_pick_best_flags_low_confidence():
    cands = [Entity(name="Totally Different Name")]
    ranked = rank_candidates("Sunny Citrus Orchards", cands)
    best, confident = pick_best(ranked)
    assert confident is False
