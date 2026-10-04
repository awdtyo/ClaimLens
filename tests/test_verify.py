"""Verification tests (Part 2): deterministic, no Docker, no model calls."""

from __future__ import annotations

from pathlib import Path

import pytest

from claimlens.claims.schema import Assumption, Claim, Evidence, Plan, PlanItem
from claimlens.verify import code_audit as code_audit_mod
from claimlens.verify import code_review as code_review_mod
from claimlens.verify import compare as compare_mod
from claimlens.verify import sensitivity as sensitivity_mod
from claimlens.verify import verify_claims


def _claim(**overrides) -> Claim:  # type: ignore[no-untyped-def]
    base = {
        "id": "c1",
        "text": "Method X reaches 91.2% accuracy.",
        "source_ref": "t1",
        "metric": "accuracy",
        "reported_value": 0.912,
        "tolerance": 0.01,
    }
    base.update(overrides)
    return Claim(**base)  # type: ignore[arg-type]


def _evidence(measured: float | None, claim_id: str = "c1", eid: str = "e1") -> Evidence:
    return Evidence(
        id=eid,
        claim_id=claim_id,
        method="docker",
        measured_value=measured,
        scale_factor=1.0,
    )


def test_match_is_replicated() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.912)])
    assert outcome.status == "replicated"
    assert outcome.evidence_ids == ["e1"]
    assert outcome.scaled is False


def test_near_match_is_partially_replicated() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.925)])
    assert outcome.status == "partially replicated"


def test_mismatch_is_not_replicated() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.85)])
    assert outcome.status == "not replicated"


def test_scaled_match_is_partially_replicated_with_scale_note() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.908)], scale_factor=0.1)
    assert outcome.status == "partially replicated"
    assert outcome.scaled is True
    assert "scale" in outcome.rationale


def test_scaled_mismatch_cannot_refute() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.70)], scale_factor=0.1)
    assert outcome.status == "partially replicated"
    assert outcome.status != "not replicated"
    assert "cannot refute" in outcome.rationale


def test_scaled_run_never_fully_replicates() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.912)], scale_factor=0.1)
    assert outcome.status == "partially replicated"


def test_missing_evidence_is_untestable() -> None:
    outcome = compare_mod.compare_claim(_claim(), [])
    assert outcome.status == "untestable"
    assert outcome.reason


def test_missing_evidence_at_scale_is_untestable_at_this_scale() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(None)], scale_factor=0.1)
    assert outcome.status == "untestable at this scale"


def test_missing_reported_value_is_untestable() -> None:
    outcome = compare_mod.compare_claim(_claim(reported_value=None), [_evidence(0.9)])
    assert outcome.status == "untestable"


def test_untestable_claim_stays_untestable() -> None:
    outcome = compare_mod.compare_claim(_claim(testable=False), [_evidence(0.912)])
    assert outcome.status == "untestable"


def test_raw_percent_values_are_normalized() -> None:
    claim = _claim(reported_value=91.2)
    outcome = compare_mod.compare_claim(claim, [_evidence(91.1)])
    assert outcome.status == "replicated"
    assert "91.1%" in outcome.rationale


def test_speedup_ratio_is_not_treated_as_percent() -> None:
    claim = _claim(metric="speedup", reported_value=2.0, tolerance=0.1)
    assert compare_mod.compare_claim(claim, [_evidence(1.95)]).status == "replicated"
    assert compare_mod.compare_claim(claim, [_evidence(1.2)]).status == "not replicated"


def test_evidence_for_other_claims_is_ignored() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.912, claim_id="c2", eid="e2")])
    assert outcome.status == "untestable"
    assert outcome.evidence_ids == []


def test_compare_module_makes_no_model_calls() -> None:
    source = Path(compare_mod.__file__).read_text(encoding="utf-8").lower()
    assert "llm" not in source
    assert "complete(" not in source


# -- sensitivity (fake runner, no Docker) --------------------------------------


def _sensitivity_plan() -> Plan:
    return Plan(
        items=[
            PlanItem(claim_id="c3", steps=["Train under noise"], scale_factor=1.0, config={}),
        ],
        assumptions=[
            Assumption(
                id="a1",
                detail="Random seed",
                value_chosen="0",
                reason="Fixed seed in the paper.",
                confidence="high",
            ),
            Assumption(
                id="a2",
                detail="Label noise rate",
                value_chosen="0.1",
                reason="Paper says 10% of labels flip.",
                confidence="medium",
            ),
        ],
    )


def _sensitivity_claim() -> Claim:
    return Claim(
        id="c3",
        text="Method X keeps accuracy under noise.",
        source_ref="s4",
        metric="accuracy_noisy",
        reported_value=0.895,
        tolerance=0.01,
    )


def _sensitivity_runner(plan: Plan, run: object) -> list[Evidence]:
    values = {assumption.value_chosen for assumption in plan.assumptions}
    if "1" in values:
        measured = 0.824
    elif "0.05" in values:
        measured = 0.84
    else:  # pragma: no cover - variants always change one assumption.
        measured = 0.821
    return [
        Evidence(id="e3", claim_id="c3", method="fake", measured_value=measured),
    ]


def test_alternate_values_are_deterministic() -> None:
    assert sensitivity_mod.alternate_value(_sensitivity_plan().assumptions[0]) == "1"
    assert sensitivity_mod.alternate_value(_sensitivity_plan().assumptions[1]) == "0.05"


def test_sensitivity_ranks_effects_by_absolute_delta(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("sensitivity", runs_root=tmp_path / "runs")
    base = [Evidence(id="e3", claim_id="c3", method="fake", measured_value=0.821)]
    effects = sensitivity_mod.run_sensitivity(
        _sensitivity_claim(), _sensitivity_plan(), base, run, _sensitivity_runner
    )
    assert [effect.assumption_id for effect in effects] == ["a2", "a1"]
    assert effects[0].alt_value == "0.05"
    assert effects[0].measured_value == pytest.approx(0.84)
    assert effects[0].delta == pytest.approx(0.019)
    assert effects[1].delta == pytest.approx(0.003)


def test_sensitivity_respects_max_reruns(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("sensitivity-cap", runs_root=tmp_path / "runs")
    base = [Evidence(id="e3", claim_id="c3", method="fake", measured_value=0.821)]
    effects = sensitivity_mod.run_sensitivity(
        _sensitivity_claim(), _sensitivity_plan(), base, run, _sensitivity_runner, max_reruns=1
    )
    assert [effect.assumption_id for effect in effects] == ["a1"]


def test_sensitivity_skips_reruns_without_measurements(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("sensitivity-empty", runs_root=tmp_path / "runs")
    base = [Evidence(id="e3", claim_id="c3", method="fake", measured_value=0.821)]
    effects = sensitivity_mod.run_sensitivity(
        _sensitivity_claim(), _sensitivity_plan(), base, run, lambda plan, run: []
    )
    assert effects == []


def test_sensitivity_needs_a_baseline_measurement(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("sensitivity-nobase", runs_root=tmp_path / "runs")
    calls: list[Plan] = []
    effects = sensitivity_mod.run_sensitivity(
        _sensitivity_claim(),
        _sensitivity_plan(),
        [],
        run,
        lambda plan, run: calls.append(plan) or [],
    )
    assert effects == []
    assert calls == []


def test_sensitivity_module_makes_no_model_calls() -> None:
    source = Path(sensitivity_mod.__file__).read_text(encoding="utf-8").lower()
    assert "llm" not in source


# -- verify_claims (fake runner, no Docker) --------------------------------------


def _toy_inputs(fixtures_dir: Path) -> tuple[list[Claim], Plan, list[Evidence]]:
    import json

    claims = [
        Claim.model_validate(item)
        for item in json.loads((fixtures_dir / "sample_claims.json").read_text(encoding="utf-8"))
    ]
    plan = Plan.model_validate(
        json.loads((fixtures_dir / "sample_plan.json").read_text(encoding="utf-8"))
    )
    evidence = [
        Evidence.model_validate(item)
        for item in json.loads((fixtures_dir / "sample_evidence.json").read_text(encoding="utf-8"))
    ]
    return claims, plan, evidence


def test_verify_claims_matches_contract_shape(tmp_path: Path, fixtures_dir: Path) -> None:
    """Toy paper: c1/c2 partially replicated (scaled), c3 untestable at this scale."""
    from claimlens.pipeline import make_run_context

    run = make_run_context("verify-toy", runs_root=tmp_path / "runs")
    claims, plan, evidence = _toy_inputs(fixtures_dir)
    run_dir = Path(run.run_dir)
    for cid in ("c1", "c2", "c3"):
        _write_claim_code(run_dir, cid)
    evidence = [
        evidence[0].model_copy(update={"code_dir": "code/c1", "iterations": 1}),
        evidence[1].model_copy(update={"code_dir": "code/c2", "iterations": 1}),
        Evidence(
            id="e_c3",
            claim_id="c3",
            method="docker",
            measured_value=None,
            code_dir="code/c3",
            iterations=1,
        ),
    ]
    verdicts = verify_claims(claims, plan, evidence, run)
    by_claim = {verdict.claim_id: verdict for verdict in verdicts}
    assert [verdict.claim_id for verdict in verdicts] == ["c1", "c2", "c3"]
    assert by_claim["c1"].status == "partially replicated"
    assert by_claim["c2"].status == "partially replicated"
    assert by_claim["c3"].status == "untestable at this scale"
    assert all(verdict.scaled for verdict in verdicts)
    assert by_claim["c1"].evidence_ids == ["e1"]
    assert by_claim["c3"].evidence_ids == []


def _write_claim_code(run_dir: Path, cid: str, snippet: str | None = None) -> None:
    dest = run_dir / "code" / cid / "iter_1" / "train.py"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(snippet if snippet is not None else BENIGN_TRAIN, encoding="utf-8")


def _coded(cid: str, measured: float | None, eid: str | None = None) -> Evidence:
    return Evidence(
        id=eid or f"e_{cid}",
        claim_id=cid,
        method="docker",
        measured_value=measured,
        code_dir=f"code/{cid}",
        iterations=1,
    )


def test_verify_claims_triggers_sensitivity_on_full_scale_mismatch(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("verify-sens", runs_root=tmp_path / "runs")
    _write_claim_code(Path(run.run_dir), "c3")
    verdicts = verify_claims(
        [_sensitivity_claim()],
        _sensitivity_plan(),
        [_coded("c3", 0.821, "e3")],
        run,
        _sensitivity_runner,
    )
    assert verdicts[0].status == "not replicated"
    assert [effect.assumption_id for effect in verdicts[0].assumption_effects] == ["a2", "a1"]


def test_verify_claims_without_runner_has_no_effects(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("verify-norunner", runs_root=tmp_path / "runs")
    _write_claim_code(Path(run.run_dir), "c3")
    verdicts = verify_claims(
        [_sensitivity_claim()],
        _sensitivity_plan(),
        [_coded("c3", 0.821, "e3")],
        run,
    )
    assert verdicts[0].status == "not replicated"
    assert verdicts[0].assumption_effects == []


def test_verify_claims_scaled_mismatch_skips_sensitivity(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("verify-scaled", runs_root=tmp_path / "runs")
    _write_claim_code(Path(run.run_dir), "c3")
    plan = _sensitivity_plan().model_copy(update={"items": []})
    plan.items = [PlanItem(claim_id="c3", steps=["Train under noise"], scale_factor=0.1, config={})]
    verdicts = verify_claims(
        [_sensitivity_claim()],
        plan,
        [_coded("c3", 0.70, "e3")],
        run,
        _sensitivity_runner,
    )
    assert verdicts[0].status == "partially replicated"
    assert verdicts[0].assumption_effects == []


def test_verify_claims_emits_one_event_per_claim(tmp_path: Path, fixtures_dir: Path) -> None:
    import json

    from claimlens.pipeline import make_run_context

    run = make_run_context("verify-events", runs_root=tmp_path / "runs")
    claims, plan, evidence = _toy_inputs(fixtures_dir)
    verify_claims(claims, plan, evidence, run)
    events = [
        json.loads(line)
        for line in (Path(run.run_dir) / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    verify_events = [event for event in events if event["stage"] == "verify"]
    assert verify_events[0]["status"] == "started"
    assert verify_events[-1]["status"] == "done"
    per_claim = [event for event in verify_events if event["status"] == "progress"]
    assert {event["data"]["claim_id"] for event in per_claim} == {"c1", "c2", "c3"}


def test_verify_claims_resolves_every_claim_without_evidence(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("verify-empty", runs_root=tmp_path / "runs")
    verdicts = verify_claims([_claim(), _claim(id="c2")], Plan(), [], run)
    assert [verdict.status for verdict in verdicts] == ["untestable", "untestable"]


# -- code audit: deterministic checks over generated code -----------------------

BENIGN_TRAIN = """import numpy as np
from sklearn.metrics import accuracy_score

np.random.seed(0)
EPOCHS = 10


def train(rows):
    weights = [0.0] * 4
    for _ in range(EPOCHS):
        for row in rows:
            features = [float(value) for value in row[:-1]]
            label = int(row[-1])
            score = sum(w * f for w, f in zip(weights, features))
            for i in range(len(weights)):
                weights[i] += 0.01 * (label - (1 if score > 0 else 0)) * features[i]
    return weights


model.fit(X_train, y_train)
acc = accuracy_score(y_test, model.predict(X_test))
print(f"MEASURED {acc}")
"""


def _run_claim_audit(  # type: ignore[no-untyped-def]
    tmp_path: Path,
    snippets: dict[str, str],
    claim_kwargs: dict | None = None,
    config: dict | None = None,
    cid: str = "c1",
):
    from claimlens.pipeline import make_run_context

    run = make_run_context(f"audit-{cid}", runs_root=tmp_path / "runs")
    run_dir = Path(run.run_dir)
    for name, content in snippets.items():
        dest = run_dir / "code" / cid / "iter_1" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    base_claim = {
        "id": cid,
        "text": "Method X reaches 91.2% accuracy.",
        "source_ref": "t1",
        "metric": "accuracy",
        "dataset": "D",
        "reported_value": 0.912,
        "tolerance": 0.01,
    }
    base_claim.update(claim_kwargs or {})
    claim = Claim(**base_claim)  # type: ignore[arg-type]
    plan = Plan(
        items=[
            PlanItem(
                claim_id=cid,
                steps=["Train and evaluate"],
                scale_factor=1.0,
                config=config or {"epochs": 10},
            )
        ]
    )
    evidence = [
        Evidence(id=f"e_{cid}", claim_id=cid, method="docker", code_dir=f"code/{cid}", iterations=1)
    ]
    return code_audit_mod.audit_code([claim], evidence, plan, run), run


def _rules(findings) -> set:  # type: ignore[no-untyped-def]
    return {(item.rule, item.severity) for item in findings}


def test_benign_code_has_no_blocking_findings(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(tmp_path, {"train.py": BENIGN_TRAIN})
    assert not [item for item in findings if item.severity == "blocking"]
    assert all(item.advisory is False for item in findings)


def test_hardcoded_numeric_literal_is_blocking(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(tmp_path, {"train.py": BENIGN_TRAIN + "\naccuracy = 0.912\n"})
    blocking = [item for item in findings if item.rule == "hardcoded-result"]
    assert len(blocking) == 1 and blocking[0].severity == "blocking"
    assert blocking[0].file == "code/c1/iter_1/train.py"
    assert blocking[0].line == BENIGN_TRAIN.count("\n") + 2


def test_hardcoded_percent_forms_are_blocking(tmp_path: Path) -> None:
    for snippet in ('print("accuracy 91.2%")\n', "TARGET = 91.20\n"):
        findings, _ = _run_claim_audit(tmp_path, {"train.py": BENIGN_TRAIN + snippet})
        assert ("hardcoded-result", "blocking") in _rules(findings), snippet


def test_hardcoded_value_in_output_file_is_blocking(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(
        tmp_path, {"train.py": BENIGN_TRAIN, "metrics.txt": "accuracy: 91.2\n"}
    )
    assert ("hardcoded-result", "blocking") in _rules(findings)


def test_comment_and_trivial_values_do_not_trigger(tmp_path: Path) -> None:
    snippets = {
        "train.py": (
            "# The paper reports 0.912 accuracy; we must reproduce it.\n" + BENIGN_TRAIN + "x = 1\n"
        )
    }
    findings, _ = _run_claim_audit(tmp_path, snippets)
    assert ("hardcoded-result", "blocking") not in _rules(findings)


def test_trivial_reported_value_needs_metric_context(tmp_path: Path) -> None:
    plain, _ = _run_claim_audit(
        tmp_path,
        {"train.py": "folds = 2\n"},
        claim_kwargs={"metric": "speedup", "reported_value": 2.0},
    )
    assert ("hardcoded-result", "blocking") not in _rules(plain)
    exact, _ = _run_claim_audit(
        tmp_path,
        {"train.py": "speedup = 2.0\n"},
        claim_kwargs={"metric": "speedup", "reported_value": 2.0},
    )
    assert ("hardcoded-result", "blocking") in _rules(exact)


def test_fit_on_test_split_is_blocking(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(
        tmp_path, {"train.py": BENIGN_TRAIN + "\nmodel.fit(X_test, y_test)\n"}
    )
    assert ("train-test-overlap", "blocking") in _rules(findings)


def test_same_object_for_fit_and_score_is_blocking(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(
        tmp_path, {"train.py": "model.fit(X, y)\nprint(model.score(X, y))\n"}
    )
    assert ("train-test-overlap", "blocking") in _rules(findings)


def test_same_file_for_train_and_eval_is_blocking(tmp_path: Path) -> None:
    snippet = (
        "train = load_csv('data.csv')\n"
        "model.fit(train)\n"
        "test = load_csv('data.csv')\n"
        "print(model.score(test))\n"
    )
    findings, _ = _run_claim_audit(tmp_path, {"train.py": snippet})
    assert ("train-test-overlap", "blocking") in _rules(findings)
    clean = snippet.replace("load_csv('data.csv')\nprint", "load_csv('test.csv')\nprint")
    clean = clean.replace("train = load_csv('data.csv')", "train = load_csv('train.csv')")
    findings, _ = _run_claim_audit(tmp_path, {"train.py": clean})
    assert ("train-test-overlap", "blocking") not in _rules(findings)


def test_results_read_from_unwritten_file_warns(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(
        tmp_path, {"train.py": BENIGN_TRAIN + '\nresults = pd.read_csv("results.csv")\n'}
    )
    assert ("results-from-file", "warning") in _rules(findings)
    findings, _ = _run_claim_audit(
        tmp_path, {"train.py": BENIGN_TRAIN + '\nframe = pd.read_csv("train.csv")\n'}
    )
    assert ("results-from-file", "warning") not in _rules(findings)


def test_missing_seed_warns_only_when_randomness_is_used(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(
        tmp_path, {"train.py": "import numpy as np\nnp.random.shuffle(rows)\n"}
    )
    assert ("seed-not-set", "warning") in _rules(findings)
    assert ("seed-not-set", "warning") not in _rules(
        _run_claim_audit(tmp_path, {"train.py": BENIGN_TRAIN})[0]
    )
    assert ("seed-not-set", "warning") not in _rules(
        _run_claim_audit(tmp_path, {"train.py": "print('deterministic')\n"})[0]
    )


def test_missing_hyperparameters_warn(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(
        tmp_path, {"train.py": "EPOCHS = 10\n"}, config={"epochs": 10, "learning_rate": 0.01}
    )
    missing = [item for item in findings if item.rule == "missing-hyperparameter"]
    assert len(missing) == 1 and "learning_rate" in missing[0].message
    findings, _ = _run_claim_audit(
        tmp_path,
        {"train.py": "EPOCHS = 10\nLR = 0.01\n"},
        config={"epochs": 10, "learning_rate": 0.01},
    )
    assert ("missing-hyperparameter", "warning") not in _rules(findings)


def test_dataset_mismatch_warns(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(tmp_path, {"train.py": 'DATASET = "E"\n'})
    assert ("dataset-mismatch", "warning") in _rules(findings)
    findings, _ = _run_claim_audit(tmp_path, {"train.py": 'DATASET = "D"\n'})
    assert ("dataset-mismatch", "warning") not in _rules(findings)


def test_metric_mismatch_warns(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(tmp_path, {"train.py": "print('done')\n"})
    assert ("metric-mismatch", "warning") in _rules(findings)
    assert ("metric-mismatch", "warning") not in _rules(
        _run_claim_audit(tmp_path, {"train.py": BENIGN_TRAIN})[0]
    )


def test_unpinned_dependencies_are_info(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(
        tmp_path, {"train.py": BENIGN_TRAIN, "requirements.txt": "numpy\nscikit-learn==1.3.0\n"}
    )
    info = [item for item in findings if item.rule == "unpinned-dependency"]
    assert len(info) == 1 and info[0].severity == "info" and "numpy" in info[0].message


def test_small_sample_size_is_info(tmp_path: Path) -> None:
    findings, _ = _run_claim_audit(tmp_path, {"train.py": "subset = rows[:20]\n"})
    assert ("small-sample", "info") in _rules(findings)
    findings, _ = _run_claim_audit(tmp_path, {"train.py": "subset = rows[:200]\n"})
    assert ("small-sample", "info") not in _rules(findings)


def test_missing_code_is_a_blocking_finding(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("audit-nocode", runs_root=tmp_path / "runs")
    claim = Claim(id="c4", text="Generalizes.", source_ref="s3", reported_value=None)
    plan = Plan()
    findings = code_audit_mod.audit_code([claim], [], plan, run)
    assert len(findings) == 1
    assert findings[0].rule == "code-present"
    assert findings[0].severity == "blocking" and findings[0].advisory is False


def test_audit_emits_code_audit_events_per_claim(tmp_path: Path) -> None:
    import json

    _, run = _run_claim_audit(tmp_path, {"train.py": BENIGN_TRAIN})
    events = [
        json.loads(line)
        for line in (Path(run.run_dir) / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    audit_events = [event for event in events if event["stage"] == "code_audit"]
    assert audit_events[0]["status"] == "started"
    assert audit_events[-1]["status"] == "done"
    assert {
        event["data"]["claim_id"] for event in audit_events if event["status"] == "progress"
    } == {"c1"}


def test_audit_module_makes_no_model_calls() -> None:
    source = Path(code_audit_mod.__file__).read_text(encoding="utf-8").lower()
    assert "llmgateway" not in source
    assert "complete(" not in source
    assert "gemini" not in source and "openrouter" not in source


# -- code review: advisory LLM findings ------------------------------------------


def _review_setup(tmp_path: Path, cid: str = "c1"):  # type: ignore[no-untyped-def]
    from claimlens.pipeline import make_run_context

    run = make_run_context(f"review-{cid}", runs_root=tmp_path / "runs")
    dest = Path(run.run_dir) / "code" / cid / "iter_1" / "train.py"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(BENIGN_TRAIN, encoding="utf-8")
    claim = Claim(
        id=cid,
        text="Method X reaches 91.2% accuracy.",
        source_ref="t1",
        metric="accuracy",
        reported_value=0.912,
        tolerance=0.01,
    )
    plan = Plan(
        items=[PlanItem(claim_id=cid, steps=["Train and evaluate"], scale_factor=1.0, config={})]
    )
    evidence = [
        Evidence(id=f"e_{cid}", claim_id=cid, method="docker", code_dir=f"code/{cid}", iterations=1)
    ]
    return run, [claim], evidence, plan


def test_review_with_fake_provider_returns_advisory_findings(tmp_path: Path) -> None:
    run, claims, evidence, plan = _review_setup(tmp_path)
    findings = code_review_mod.review_code(claims, evidence, plan, run)
    assert len(findings) == 1
    assert findings[0].advisory is True
    assert findings[0].severity == "warning"
    assert findings[0].rule == "review-seed-review"
    assert findings[0].file == "code/c1/iter_1/train.py"


def test_review_handles_invalid_model_output_without_crashing(tmp_path: Path) -> None:
    from claimlens.config import RunContext

    run, claims, evidence, plan = _review_setup(tmp_path)

    class StubLLM:
        def __init__(self, replies: list) -> None:  # type: ignore[no-untyped-def]
            self.replies = list(replies)

        def complete(self, task: str, messages, schema=None, tools=None, role: str = "agent"):  # type: ignore[no-untyped-def]
            assert task == "code_review"
            reply = self.replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply

    bad_replies: list = [
        {"text": "looks fine to me"},
        {"findings": "oops"},
        None,
        {"findings": [{"rule": "", "message": ""}]},
        {"findings": [{"rule": "x", "message": "y", "file": "elsewhere.py"}]},
        RuntimeError("model blew up"),
    ]
    run_stub = RunContext(
        run_id=run.run_id, run_dir=run.run_dir, config=run.config, llm=StubLLM(bad_replies)
    )
    # One reply per call: garbage yields nothing, the unknown file falls
    # back to the first known file, the exception yields nothing.
    for want in ([], [], [], [], "fallback", []):
        got = code_review_mod.review_code(claims, evidence, plan, run_stub)
        if want == "fallback":
            assert len(got) == 1 and got[0].advisory is True
        else:
            assert got == []
    assert code_review_mod.review_code(claims, [], plan, run_stub) == []


def test_review_coerces_severity_and_unknown_files(tmp_path: Path) -> None:
    from claimlens.config import RunContext

    run, claims, evidence, plan = _review_setup(tmp_path)

    class StubLLM:
        def complete(self, task: str, messages, schema=None, tools=None, role: str = "agent"):  # type: ignore[no-untyped-def]
            return {
                "findings": [
                    {
                        "rule": "hard",
                        "severity": "blocking",
                        "file": "invented.py",
                        "line": -3,
                        "message": "bad",
                    }
                ]
            }

    run_stub = RunContext(run_id=run.run_id, run_dir=run.run_dir, config=run.config, llm=StubLLM())
    findings = code_review_mod.review_code(claims, evidence, plan, run_stub)
    assert len(findings) == 1
    assert findings[0].advisory is True
    assert findings[0].severity == "warning"
    assert findings[0].file == "code/c1/iter_1/train.py"
    assert findings[0].line is None


def test_review_without_gateway_returns_no_findings(tmp_path: Path) -> None:
    from claimlens.config import RunContext

    run, claims, evidence, plan = _review_setup(tmp_path)
    run_nollm = RunContext(run_id=run.run_id, run_dir=run.run_dir, config=run.config, llm=None)
    assert code_review_mod.review_code(claims, evidence, plan, run_nollm) == []


# -- verify_claims: blocking findings override the numeric verdict -----------


def _full_scale_match_claim(cid: str = "c1") -> tuple[Claim, Plan]:
    claim = Claim(
        id=cid,
        text="Method X reaches 91.2% accuracy.",
        source_ref="t1",
        metric="accuracy",
        reported_value=0.912,
        tolerance=0.01,
    )
    plan = Plan(
        items=[PlanItem(claim_id=cid, steps=["Train and evaluate"], scale_factor=1.0, config={})]
    )
    return claim, plan


def test_blocking_finding_overrides_a_numeric_match(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context
    from claimlens.verify import verify_claims as verify_mod

    run = make_run_context("verify-blocked", runs_root=tmp_path / "runs")
    _write_claim_code(Path(run.run_dir), "c1", BENIGN_TRAIN + "\naccuracy = 0.912\n")
    claim, plan = _full_scale_match_claim()
    verdicts = verify_mod([claim], plan, [_coded("c1", 0.912)], run)
    assert len(verdicts) == 1
    verdict = verdicts[0]
    assert verdict.status == "untestable"
    assert verdict.status != "replicated"
    assert verdict.reason and "hardcoded-result" in verdict.reason
    assert verdict.evidence_ids == ["e_c1"]
    assert any(
        item.rule == "hardcoded-result" and item.severity == "blocking"
        for item in verdict.code_findings
    )


def test_warnings_do_not_change_the_status(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context
    from claimlens.verify import verify_claims as verify_mod

    run = make_run_context("verify-warned", runs_root=tmp_path / "runs")
    _write_claim_code(
        Path(run.run_dir),
        "c1",
        "import numpy as np\n"
        "from sklearn.metrics import accuracy_score\n"
        "np.random.shuffle([1, 2, 3])\n"
        "acc = accuracy_score(y_test, model.predict(X_test))\n"
        "print(acc)\n",
    )
    claim, plan = _full_scale_match_claim()
    verdicts = verify_mod([claim], plan, [_coded("c1", 0.912)], run)
    assert verdicts[0].status == "replicated"
    assert verdicts[0].code_findings
    assert all(item.severity != "blocking" for item in verdicts[0].code_findings)


def test_blocked_claim_skips_sensitivity_reruns(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context
    from claimlens.verify import verify_claims as verify_mod

    run = make_run_context("verify-blocked-sens", runs_root=tmp_path / "runs")
    _write_claim_code(Path(run.run_dir), "c1", BENIGN_TRAIN + "\naccuracy = 0.912\n")
    claim, plan = _full_scale_match_claim()
    calls: list = []

    def runner(plan: Plan, run) -> list[Evidence]:  # type: ignore[no-untyped-def]
        calls.append(plan)
        return []

    verdicts = verify_mod([claim], plan, [_coded("c1", 0.5)], run, runner)
    assert verdicts[0].status == "untestable"
    assert verdicts[0].assumption_effects == []
    assert calls == []


def test_apply_blocking_override_unit() -> None:
    from claimlens.claims.schema import CodeFinding
    from claimlens.verify import apply_blocking_override
    from claimlens.verify.compare import Comparison

    comparison = Comparison(status="replicated", rationale="close", scaled=False)
    assert apply_blocking_override(comparison, []) == ("replicated", None)
    advisory = [
        CodeFinding(
            rule="review-x",
            severity="blocking",
            file="code/c1/iter_1/a.py",
            message="m",
            advisory=True,
        )
    ]
    assert apply_blocking_override(comparison, advisory) == ("replicated", None)
    blocking = [
        CodeFinding(
            rule="hardcoded-result",
            severity="blocking",
            file="code/c1/iter_1/a.py",
            line=3,
            message="literal 0.912",
            advisory=False,
        )
    ]
    status, reason = apply_blocking_override(comparison, blocking)
    assert status == "untestable"
    assert reason and "hardcoded-result" in reason
