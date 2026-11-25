"""The evaluation's baselines and its ablation code: no model, no network."""
import numpy as np

from evaluation import run_eval as ev

SENTS = ["Solar power is growing fast.", "Panels are getting cheaper every year.", "Many homes now use solar panels.",
         "Wind farms also produce clean energy.", "Batteries store energy for the night.", "Dogs are loyal pets."]


def test_cleaning_strips_datelines_and_bylines():
    assert ev.clean("(CNN)The court ruled.") == "The court ruled."
    assert ev.clean("By . Jane Roe . The court ruled.") == "The court ruled."
    assert ev.clean("Plain start.") == "Plain start."


def test_baselines_pick_k_sorted_distinct_sentences():
    assert ev.lead3(SENTS) == [0, 1, 2]
    for pick in (ev.random3(SENTS), ev.textrank_tfidf(SENTS)):
        assert len(pick) == 3 and pick == sorted(set(pick))
    assert ev.textrank_tfidf(SENTS[:2]) == [0, 1]  # fewer sentences than k: all of them


def test_ablation_weights_match_the_engine():
    ev._check_blend_matches_engine()  # raises if the evaluation's copy of the scoring drifted
