"""Source-only coding critique for Odin's isolated, receipt-validated proposals.

Never execute model-generated code, call inference, edit project source, or
train/promote weights. Preserve a metadata-only, non-overwriting critique.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

try:
    from ai.agent import pipeline
except ModuleNotFoundError:
    # The background worker is launched as scripts/odin_worker.py; keep
    # the existing direct-script runtime compatible without network imports.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai" / "agent"))
    import pipeline

ROOT = Path(__file__).resolve().parents[1]
MAX_FEEDBACK_CODES = 25
RISK_CALLS = frozenset({
    "eval", "exec", "compile", "__import__",
    "os.system", "os.popen", "os.remove", "os.unlink",
    "shutil.rmtree", "subprocess.Popen", "subprocess.run",
    "subprocess.call", "subprocess.check_output", "ctypes.CDLL",
    "socket.socket", "pickle.loads",
})
GUIDANCE = {
    "syntax_invalid": "Return a complete, parseable Python module.",
    "no_semantic_change": "Produce an actual implementation change; a formatting-only edit is not enough.",
    "public_symbols_removed": "Restore the original public functions or classes unless a reviewed contract explicitly approves breaking the API.",
    "public_signatures_changed": "Preserve public call signatures unless an approved contract and updated tests permit the change.",
    "sensitive_calls_added": "Explain and independently review any newly introduced sensitive API calls before accepting the proposal.",
}


def _public(tree: ast.Module) -> dict[str, tuple]:
    result = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name.startswith("_"):
            continue
        if isinstance(node, ast.ClassDef):
            result[node.name] = ("class",)
            continue
        args = node.args
        positional = args.posonlyargs + args.args
        signature = (
            type(node).__name__,
            tuple(x.arg for x in positional),
            len(args.posonlyargs),
            tuple(x.arg for x in args.kwonlyargs),
            args.vararg.arg if args.vararg else None,
            args.kwarg.arg if args.kwarg else None,
            len(args.defaults),
            tuple(x is not None for x in args.kw_defaults),
        )
        result[node.name] = signature
    return result


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id + "." + node.attr
    return None


def _sensitive_calls(tree: ast.Module) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            value = _call_name(node.func)
            if value in RISK_CALLS:
                names.add(value)
    return names


def critique(original: str, candidate: str) -> dict:
    """Static source critique only, not a correctness or security PASS."""
    if not isinstance(original, str) or not isinstance(candidate, str):
        raise ValueError("Expected Python source strings")
    if len(original.encode("utf-8")) > 30000 or not 0 < len(candidate.encode("utf-8")) <= pipeline.MAX_SOURCE:
        raise ValueError("Source exceeds approved proposal bounds")
    existing = ast.parse(original)
    try:
        proposed = ast.parse(candidate)
    except SyntaxError:
        return {
            "status": "revision_required",
            "codes": ["syntax_invalid"],
            "guidance": [GUIDANCE["syntax_invalid"]],
            "public_removed": [],
            "public_signatures_changed": [],
            "new_sensitive_calls": [],
            "functional_tests_verified": False,
            "security_review_verified": False,
        }
    codes = []
    previous_api, next_api = _public(existing), _public(proposed)
    missing = sorted(set(previous_api) - set(next_api))
    changed = sorted(
        name for name in set(previous_api) & set(next_api)
        if previous_api[name] != next_api[name]
    )
    sensitive = sorted(_sensitive_calls(proposed) - _sensitive_calls(existing))
    if ast.dump(existing, include_attributes=False) == ast.dump(proposed, include_attributes=False):
        codes.append("no_semantic_change")
    if missing:
        codes.append("public_symbols_removed")
    if changed:
        codes.append("public_signatures_changed")
    if sensitive:
        codes.append("sensitive_calls_added")
    if len(codes) > MAX_FEEDBACK_CODES:
        raise ValueError("Too many critique conditions")
    return {
        "status": "revision_required" if codes else "candidate_needs_verified_tests",
        "codes": codes,
        "guidance": [GUIDANCE[name] for name in codes],
        "public_removed": missing[:30],
        "public_signatures_changed": changed[:30],
        "new_sensitive_calls": sensitive,
        "functional_tests_verified": False,
        "security_review_verified": False,
    }


def _lesson_parts(name: str) -> tuple[str, ...]:
    pipeline.target_parts(name)
    ident = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return ("state", "coder-coach", "lessons", ident + ".json")


def lesson_for(root: Path, name: str) -> str:
    """Read only fixed advisory guidance from earlier static critiques."""
    relative = _lesson_parts(name)
    try:
        saved = pipeline.read(root, relative, 3000)
    except FileNotFoundError:
        return ""
    raw = json.loads(saved)
    if not isinstance(raw, dict) or set(raw) != {"schema", "target_sha256", "codes", "guidance"}:
        raise ValueError("Invalid coding lesson schema")
    if raw["schema"] != 1 or raw["target_sha256"] != hashlib.sha256(name.encode()).hexdigest():
        raise ValueError("Stale or cross-target coding lesson")
    codes = raw["codes"]
    if (not isinstance(codes, list) or not 1 <= len(codes) <= 4
            or any(not isinstance(code, str) or code not in GUIDANCE for code in codes)
            or len(set(codes)) != len(codes)
            or raw["guidance"] != [GUIDANCE[code] for code in codes]):
        raise ValueError("Untrusted coding lesson content")
    return "Previous unverified coding attempt raised: " + ", ".join(codes) + ". " + " ".join(raw["guidance"])


def _remember_lesson(root: Path, name: str, report: dict) -> None:
    if report["status"] != "revision_required":
        return
    lesson = {
        "schema": 1,
        "target_sha256": hashlib.sha256(name.encode("utf-8")).hexdigest(),
        "codes": report["codes"],
        "guidance": report["guidance"],
    }
    pipeline.publish(root, _lesson_parts(name), pipeline.json_bytes(lesson), replace=True)


def review_proposal(root: Path, name: str, task: str, owner: str | None,
                    invocation: str) -> dict:
    """Read an existing immutable proposal and record a metadata-only critique."""
    root = Path(root)
    payload, evidence = pipeline.receipt(root, name, task, owner, invocation)
    baseline_hash, original = pipeline.baseline(root, name)
    if evidence["baseline_sha256"] != baseline_hash:
        raise ValueError("Original source changed since proposal")
    result = critique(original, payload.decode("utf-8"))
    report = {
        "schema": 1,
        "scope": "static_candidate_critique",
        "proposal_invocation_id": invocation,
        "proposal_task_id": owner,
        "target": name,
        "candidate_sha256": hashlib.sha256(payload).hexdigest(),
        "baseline_sha256": baseline_hash,
        "task_sha256": hashlib.sha256(task.encode("utf-8")).hexdigest(),
        **result,
        "model_weights_updated": False,
        "training_example_approved": False,
        "candidate_deployed": False,
    }
    relative = (*pipeline.proposal_parts(owner, invocation), "critique.json")
    raw = pipeline.json_bytes(report)
    try:
        pipeline.publish(root, relative, raw)
    except FileExistsError:
        # Legitimate repeated verification reads the same immutable critique.
        # A conflicting review must never overwrite the first record.
        if pipeline.read(root, relative, 20000) != raw:
            raise ValueError("Conflicting previously published critique") from None
    _remember_lesson(root, name, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--task-id")
    parser.add_argument("--invocation-id", required=True)
    args = parser.parse_args()
    try:
        report = review_proposal(ROOT, args.target, args.task,
                                 args.task_id, args.invocation_id)
    except (OSError, ValueError, TypeError, UnicodeError, SyntaxError) as exc:
        print(json.dumps({"status": "BLOCKED", "error_type": type(exc).__name__}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "candidate_needs_verified_tests" else 1


if __name__ == "__main__":
    raise SystemExit(main())
