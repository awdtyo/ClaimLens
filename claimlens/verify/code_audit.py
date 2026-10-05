"""Code audit stage: deterministic checks over generated experiment code.

Implemented for Part 2 (Tasks B/D); the pipeline's ``code_audit``
stage calls :func:`audit_code` between ``sandbox`` and ``verify``.
All findings here are deterministic (AST and text based, no model
calls) and carry ``advisory=False``. LLM review lives in
:mod:`claimlens.verify.code_review` and is advisory only.

Principle: blocking findings void a run, so they must be high
precision. When unsure, the rules below emit ``warning`` instead.
"""

from __future__ import annotations

import ast
import io
import logging
import math
import re
import tokenize
from dataclasses import dataclass, field
from pathlib import Path

from claimlens.claims.schema import Claim, CodeFinding, Evidence, Plan
from claimlens.config import RunContext

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 200_000
TRIVIAL_INTS = frozenset({0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100, 1000})
TEST_NAME_RE = re.compile(r"test", re.IGNORECASE)
EVAL_CALLS = frozenset(
    {
        "score",
        "predict",
        "predict_proba",
        "predict_log_proba",
        "evaluate",
        "accuracy_score",
        "f1_score",
        "precision_score",
        "recall_score",
        "confusion_matrix",
        "classification_report",
        "log_loss",
    }
)
RESULT_NAME_RE = re.compile(r"result|metric|score|measured|output|eval", re.IGNORECASE)
SEED_CALL_RE = re.compile(
    r"random\.seed\s*\(|np\.random\.seed\s*\(|manual_seed\s*\(|set_seed\s*\(|random_state\s*=|seed\s*="
)
RANDOM_USE_RE = re.compile(r"random\.|np\.random\.|shuffle\s*\(|train_test_split\s*\(|torch\.rand")
SAMPLE_NAME_RE = re.compile(r"^(n_samples|sample_size|num_samples|n_test|n_train)$", re.IGNORECASE)
DATASET_ASSIGN_RE = re.compile(r"""dataset\s*[:=]\s*['"]([^'"]+)['"]""", re.IGNORECASE)
DATASET_WORD_RE = re.compile(r"\b[Dd]ataset\s+([A-Za-z0-9_-]+)")
PIP_INSTALL_RE = re.compile(r"pip\s+install\s+([A-Za-z0-9_.\-\[\]]+)(?:\s|$)")
METRIC_ALIASES = {
    "accuracy": ("accuracy", "acc", "correct"),
    "speedup": ("speedup", "speed", "faster"),
}


@dataclass
class CodeFile:
    """One audited file: path relative to the run dir plus its text."""

    rel: str
    text: str

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines()

    @property
    def is_python(self) -> bool:
        return self.rel.endswith(".py")


@dataclass
class ClaimCode:
    """All generated files for one claim."""

    claim_id: str
    files: list[CodeFile] = field(default_factory=list)

    @property
    def python_files(self) -> list[CodeFile]:
        return [item for item in self.files if item.is_python]

    def all_text(self) -> str:
        return "\n".join(item.text for item in self.python_files)


def _read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()[:MAX_FILE_BYTES]
    except OSError:
        return None
    if b"\x00" in data[:8000]:
        return None
    return data.decode("utf-8", errors="replace")


def collect_claim_code(run_dir: Path, claim_id: str, evidence: list[Evidence]) -> ClaimCode:
    """Gather saved code iterations for one claim from the run directory."""
    code = ClaimCode(claim_id=claim_id)
    seen: set[str] = set()
    for item in evidence:
        if item.claim_id != claim_id:
            continue
        root = run_dir / (item.code_dir or f"code/{claim_id}")
        for number in range(1, max(item.iterations, 1) + 1):
            for path in sorted((root / f"iter_{number}").rglob("*")):
                if path.is_file() and str(path) not in seen:
                    seen.add(str(path))
                    text = _read_text(path)
                    if text is not None:
                        code.files.append(CodeFile(rel=str(path.relative_to(run_dir)), text=text))
    # Iterations saved beyond the recorded count still count as code.
    fallback = run_dir / f"code/{claim_id}"
    if fallback.is_dir():
        for path in sorted(fallback.rglob("*")):
            if path.is_file() and str(path) not in seen:
                seen.add(str(path))
                text = _read_text(path)
                if text is not None:
                    code.files.append(CodeFile(rel=str(path.relative_to(run_dir)), text=text))
    code.files.sort(key=lambda item: item.rel)
    return code


def _sig_digits(value: float) -> int:
    text = f"{abs(value):g}"
    mantissa = text.split("e")[0].replace(".", "").replace("-", "").lstrip("0")
    return len(mantissa or "0")


def _is_trivial(value: float) -> bool:
    return value == int(value) and abs(int(value)) in TRIVIAL_INTS


def _reported_forms(reported: float) -> tuple[set[float], set[str]]:
    """Numeric and string surface forms of a normalized reported value."""
    numbers = {reported, reported * 100.0}
    strings = {
        f"{reported:g}",
        f"{reported * 100.0:g}",
        f"{reported * 100.0:.2f}",
        f"{reported * 100.0:g}%",
    }
    return numbers, strings


def _metric_keywords(claim: Claim) -> set[str]:
    keywords = {"metric", "score", "result", "measured", "value", "eval"}
    if claim.metric:
        keywords.add(claim.metric.lower())
        keywords.update(METRIC_ALIASES.get(claim.metric.lower(), ()))
    return keywords


def _number_string_tokens(text: str) -> list[tuple[str, float | None, str | None, int]]:
    """Yield (kind, number, string, line) for literal tokens, never comments."""
    found: list[tuple[str, float | None, str | None, int]] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for tok in tokens:
            if tok.type == tokenize.NUMBER:
                try:
                    found.append(("number", float(tok.string), None, tok.start[0]))
                except ValueError:
                    continue
            elif tok.type == tokenize.STRING:
                try:
                    value = ast.literal_eval(tok.string)
                except (SyntaxError, ValueError):
                    continue
                if isinstance(value, str):
                    found.append(("string", None, value, tok.start[0]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        logger.debug("Tokenize failed; falling back to regex scan.")
        for number, line in _regex_numbers(text):
            found.append(("number", number, None, line))
    return found


def _regex_numbers(text: str) -> list[tuple[float, int]]:
    pattern = re.compile(r"(?<![\w.])([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:\s*%)?")
    found = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.split("#", 1)[0]
        for match in pattern.finditer(stripped):
            try:
                found.append((float(match.group(1)), lineno))
            except ValueError:
                continue
    return found


def check_hardcoded_result(claim: Claim, code: ClaimCode) -> list[CodeFinding]:
    """Blocking: a reported value appears as a literal in code or outputs."""
    if claim.reported_value is None or not math.isfinite(claim.reported_value):
        return []
    reported = claim.reported_value
    numbers, strings = _reported_forms(reported)
    precise = _sig_digits(reported) >= 3 and not _is_trivial(reported)
    keywords = _metric_keywords(claim)
    findings: list[CodeFinding] = []
    for item in code.files:
        if item.is_python:
            tokens = _number_string_tokens(item.text)
        else:
            tokens = [("number", value, None, line) for value, line in _regex_numbers(item.text)]
        for kind, number, string, line in tokens:
            if kind == "number" and number is not None:
                hit = number in numbers
            else:
                hit = bool(string) and (
                    string in strings
                    or any(
                        form.endswith("%") and form in string
                        for form in strings
                        if form.endswith("%")
                    )
                )
            if not hit:
                continue
            if precise:
                if number is not None and _is_trivial(number):
                    continue
                shown = string if string is not None else f"{number:g}"
                findings.append(
                    CodeFinding(
                        rule="hardcoded-result",
                        severity="blocking",
                        file=item.rel,
                        line=line,
                        message=(
                            f"Claim {claim.id} reports {reported:g} but the value "
                            f"appears as a literal ({shown}); "
                            "the run may not measure anything."
                        ),
                        advisory=False,
                    )
                )
            else:
                context = item.lines[line - 1].lower() if 0 < line <= len(item.lines) else ""
                if number in numbers and any(word in context for word in keywords):
                    findings.append(
                        CodeFinding(
                            rule="hardcoded-result",
                            severity="blocking",
                            file=item.rel,
                            line=line,
                            message=(
                                f"Claim {claim.id} reports {reported:g} and the exact "
                                "value is assigned in a metric context; "
                                "the run may not measure anything."
                            ),
                            advisory=False,
                        )
                    )
    return findings


def _root_name(node: ast.AST) -> str | None:
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value if isinstance(node, ast.Attribute) else node.slice
    if isinstance(node, ast.Tuple):
        return None
    return node.id if isinstance(node, ast.Name) else None


def check_train_test_overlap(code: ClaimCode) -> list[CodeFinding]:
    """Blocking: training on the test split, or evaluating the train split as new."""
    findings: list[CodeFinding] = []
    for item in code.python_files:
        try:
            tree = ast.parse(item.text)
        except SyntaxError:
            continue
        fit_names: dict[str, int] = {}
        file_of: dict[str, set[str]] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            paths = {
                str(arg.value)
                for arg in node.value.args
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
            } | {
                str(keyword.value.value)
                for keyword in node.value.keywords
                if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str)
            }
            for target in node.targets:
                name = _root_name(target)
                if name and paths:
                    file_of.setdefault(name, set()).update(paths)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            if node.func.attr == "fit":
                for arg in node.args:
                    name = _root_name(arg)
                    if name and TEST_NAME_RE.search(name):
                        findings.append(
                            CodeFinding(
                                rule="train-test-overlap",
                                severity="blocking",
                                file=item.rel,
                                line=node.lineno,
                                message=(
                                    f".fit() is called on {name!r}, data loaded from "
                                    "the test split."
                                ),
                                advisory=False,
                            )
                        )
                    if name:
                        fit_names.setdefault(name, node.lineno)
            elif node.func.attr in EVAL_CALLS:
                for arg in node.args:
                    name = _root_name(arg)
                    if name and name in fit_names:
                        findings.append(
                            CodeFinding(
                                rule="train-test-overlap",
                                severity="blocking",
                                file=item.rel,
                                line=node.lineno,
                                message=(
                                    f"{name!r} is used both for .fit() and for "
                                    f".{node.func.attr}(); the evaluation data is "
                                    "the training data."
                                ),
                                advisory=False,
                            )
                        )
        fit_files = {path for name in fit_names for path in file_of.get(name, set())}
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            if node.func.attr not in EVAL_CALLS:
                continue
            for arg in node.args:
                name = _root_name(arg)
                if name and (file_of.get(name, set()) & fit_files):
                    findings.append(
                        CodeFinding(
                            rule="train-test-overlap",
                            severity="blocking",
                            file=item.rel,
                            line=node.lineno,
                            message=(
                                f".{node.func.attr}() evaluates data loaded from the "
                                "same file used for training."
                            ),
                            advisory=False,
                        )
                    )
    return findings


def check_results_file(code: ClaimCode) -> list[CodeFinding]:
    """Warning: results read from a file the code never generates."""
    findings: list[CodeFinding] = []
    for item in code.python_files:
        reads: dict[str, int] = {}
        writes: set[str] = set()
        for match in re.finditer(
            r"""open\s*\(\s*['"]([^'"]+)['"]\s*(?:,\s*['"]([rwab+]+)['"])?""", item.text
        ):
            path, mode = match.group(1), match.group(2) or "r"
            line = item.text.count("\n", 0, match.start()) + 1
            if "r" in mode and "+" not in mode and "w" not in mode and "a" not in mode:
                reads.setdefault(path, line)
            else:
                writes.add(path)
        for match in re.finditer(
            r"""read_csv\s*\(\s*['"]([^'"]+)['"]|read_json\s*\(\s*['"]([^'"]+)['"]|loadtxt\s*\(\s*['"]([^'"]+)['"]""",
            item.text,
        ):
            path = next(group for group in match.groups() if group)
            reads.setdefault(path, item.text.count("\n", 0, match.start()) + 1)
        for match in re.finditer(
            r"""to_csv\s*\(\s*['"]([^'"]+)['"]|to_json\s*\(\s*['"]([^'"]+)['"]|dump\s*\([^,]+,\s*open\s*\(\s*['"]([^'"]+)['"]""",
            item.text,
        ):
            writes.update(group for group in match.groups() if group)
        for path, line in reads.items():
            if RESULT_NAME_RE.search(path) and path not in writes:
                findings.append(
                    CodeFinding(
                        rule="results-from-file",
                        severity="warning",
                        file=item.rel,
                        line=line,
                        message=(
                            f"Results are read from {path!r}, which the code never "
                            "writes; the numbers may not come from the experiment."
                        ),
                        advisory=False,
                    )
                )
    return findings


def check_seed(code: ClaimCode) -> list[CodeFinding]:
    """Warning: randomness is used without any seed being set."""
    findings: list[CodeFinding] = []
    for item in code.python_files:
        if not RANDOM_USE_RE.search(item.text):
            continue
        if SEED_CALL_RE.search(item.text):
            continue
        line = next(
            (lineno for lineno, text in enumerate(item.lines, 1) if RANDOM_USE_RE.search(text)),
            1,
        )
        findings.append(
            CodeFinding(
                rule="seed-not-set",
                severity="warning",
                file=item.rel,
                line=line,
                message="Randomness is used but no seed is set; reruns may not reproduce.",
                advisory=False,
            )
        )
    return findings


def check_hyperparameters(claim: Claim, plan: Plan, code: ClaimCode) -> list[CodeFinding]:
    """Warning: planned hyperparameters are missing from the code."""
    config: dict = {}
    for plan_item in plan.items:
        if plan_item.claim_id == claim.id:
            config = plan_item.config
            break
    if not config or not code.python_files:
        return []
    blob = code.all_text().lower()
    first = code.python_files[0].rel
    findings: list[CodeFinding] = []
    for key, value in config.items():
        if key.lower() in blob:
            continue
        if isinstance(value, (int, float, str)) and str(value).lower() in blob:
            continue
        findings.append(
            CodeFinding(
                rule="missing-hyperparameter",
                severity="warning",
                file=first,
                line=None,
                message=(
                    f"Plan config {key}={value!r} for claim {claim.id} "
                    "appears nowhere in the generated code."
                ),
                advisory=False,
            )
        )
    return findings


def check_dataset(claim: Claim, code: ClaimCode) -> list[CodeFinding]:
    """Warning: the dataset named in code differs from the claim's dataset."""
    if not claim.dataset:
        return []
    findings: list[CodeFinding] = []
    for item in code.python_files:
        for lineno, line in enumerate(item.lines, 1):
            mentioned = DATASET_ASSIGN_RE.findall(line) + DATASET_WORD_RE.findall(line)
            for name in mentioned:
                if name != claim.dataset:
                    findings.append(
                        CodeFinding(
                            rule="dataset-mismatch",
                            severity="warning",
                            file=item.rel,
                            line=lineno,
                            message=(
                                f"Code names dataset {name!r} but claim {claim.id} "
                                f"is about dataset {claim.dataset!r}."
                            ),
                            advisory=False,
                        )
                    )
    return findings


def check_metric(claim: Claim, code: ClaimCode) -> list[CodeFinding]:
    """Warning: the plan's metric is computed differently or not at all."""
    if not claim.metric or not code.python_files:
        return []
    blob = code.all_text().lower()
    keywords = {claim.metric.lower(), *METRIC_ALIASES.get(claim.metric.lower(), ())}
    if any(word in blob for word in keywords):
        return []
    return [
        CodeFinding(
            rule="metric-mismatch",
            severity="warning",
            file=code.python_files[0].rel,
            line=None,
            message=(
                f"Claim {claim.id} measures {claim.metric!r} but the generated "
                "code never mentions it."
            ),
            advisory=False,
        )
    ]


def check_dependencies(code: ClaimCode) -> list[CodeFinding]:
    """Info: unpinned dependencies."""
    findings: list[CodeFinding] = []
    for item in code.files:
        if item.rel.endswith(("requirements.txt", "requirements.in")):
            for lineno, line in enumerate(item.lines, 1):
                name = line.strip()
                if name and not name.startswith("#") and not re.search(r"[=<>~!]", name):
                    findings.append(
                        CodeFinding(
                            rule="unpinned-dependency",
                            severity="info",
                            file=item.rel,
                            line=lineno,
                            message=f"Dependency {name!r} has no pinned version.",
                            advisory=False,
                        )
                    )
        if item.is_python:
            for match in PIP_INSTALL_RE.finditer(item.text):
                spec = match.group(1)
                pinned = item.text[match.end() : match.end() + 16].lstrip().startswith("==")
                if not pinned:
                    findings.append(
                        CodeFinding(
                            rule="unpinned-dependency",
                            severity="info",
                            file=item.rel,
                            line=item.text.count("\n", 0, match.start()) + 1,
                            message=f"Package {spec!r} is installed without a pinned version.",
                            advisory=False,
                        )
                    )
    return findings


def check_sample_size(code: ClaimCode) -> list[CodeFinding]:
    """Info: very small sample sizes."""
    findings: list[CodeFinding] = []
    for item in code.python_files:
        try:
            tree = ast.parse(item.text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and SAMPLE_NAME_RE.match(node.targets[0].id)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, int)
                and node.value.value < 100
            ):
                findings.append(
                    CodeFinding(
                        rule="small-sample",
                        severity="info",
                        file=item.rel,
                        line=node.lineno,
                        message=(
                            f"Sample size {node.targets[0].id}={node.value.value} "
                            "is very small; treat the measurement as noisy."
                        ),
                        advisory=False,
                    )
                )
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Slice)
                and isinstance(node.slice.upper, ast.Constant)
                and isinstance(node.slice.upper.value, int)
                and node.slice.upper.value <= 50
            ):
                findings.append(
                    CodeFinding(
                        rule="small-sample",
                        severity="info",
                        file=item.rel,
                        line=node.lineno,
                        message=(
                            f"Slice takes only {node.slice.upper.value} rows; "
                            "treat the measurement as noisy."
                        ),
                        advisory=False,
                    )
                )
    return findings


def audit_claim(claim: Claim, plan: Plan, code: ClaimCode) -> list[CodeFinding]:
    """Run every deterministic check for one claim's code."""
    findings = [
        *check_hardcoded_result(claim, code),
        *check_train_test_overlap(code),
        *check_results_file(code),
        *check_seed(code),
        *check_hyperparameters(claim, plan, code),
        *check_dataset(claim, code),
        *check_metric(claim, code),
        *check_dependencies(code),
        *check_sample_size(code),
    ]
    findings.sort(key=lambda item: (item.file, item.line or 0, item.rule))
    return findings


def audit_code(
    claims: list[Claim],
    evidence: list[Evidence],
    plan: Plan,
    run: RunContext,
) -> list[CodeFinding]:
    """Audit generated code under ``runs/<run_id>/code/<claim_id>/iter_<n>/``.

    Args:
        claims: Extracted claims under audit.
        evidence: Measured results (carry ``code_dir`` and ``iterations``).
        plan: Reproduction plan (the unblinded original).
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        Findings, one per broken rule. All findings here are
        deterministic and carry ``advisory=False``; a non-advisory
        ``blocking`` finding later turns the claim's verdict
        ``untestable``. Also emits ``code_audit`` progress events per
        claim, the entry point the pipeline's ``code_audit`` stage uses.
    """
    run_dir = Path(run.run_dir)  # type: ignore[arg-type]
    run.emit(
        "code_audit",
        "started",
        f"auditing code for {len(claims)} claim(s)",
        {"claims": [claim.id for claim in claims]},
    )
    findings: list[CodeFinding] = []
    for claim in claims:
        run.emit("code_audit", "progress", f"{claim.id}: auditing", {"claim_id": claim.id})
        code = collect_claim_code(run_dir, claim.id, evidence)
        if not code.files:
            findings.append(
                CodeFinding(
                    rule="code-present",
                    severity="blocking",
                    file=f"code/{claim.id}",
                    line=None,
                    message=f"No experiment code was produced for {claim.id}; there is nothing to verify.",
                    advisory=False,
                )
            )
        else:
            findings.extend(audit_claim(claim, plan, code))
        run.emit(
            "code_audit",
            "progress",
            f"{claim.id}: audited",
            {"claim_id": claim.id},
        )
    run.emit(
        "code_audit",
        "done",
        f"audited {len(claims)} claim(s), {len(findings)} finding(s)",
        {"findings": len(findings)},
    )
    return findings
