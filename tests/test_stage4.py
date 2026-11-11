"""Offline Stage 4 regressions; every project write uses a disposable root."""
import base64
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "ai/agent"))
import healthcheck
import orchestrator
import pipeline
import proposal_builder

spec = importlib.util.spec_from_file_location("stage4_worker_tests", PROJECT / "scripts/odin_worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class Stage4Tests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        temporary = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(temporary) / "root"
        self.root.mkdir()
        self.base = self.root / "state/task-queue"
        self.stack.enter_context(patch.multiple(worker, ROOT=self.root, BASE=self.base,
            PENDING=self.base / "pending", RUNNING=self.base / "running", DONE=self.base / "done"))
        self.stack.enter_context(patch.object(orchestrator, "ROOT", self.root))
        self.stack.enter_context(patch.object(orchestrator, "bridge_event", return_value=None))
        self.stack.enter_context(patch.multiple(proposal_builder, ROOT=self.root,
            PROPOSALS=self.root / "state/proposals"))
        self.original_ask = orchestrator.ask
        self.ask = self.stack.enter_context(patch.object(orchestrator, "ask",
            side_effect=AssertionError("Unexpected inference")))
        self.run = self.stack.enter_context(patch.object(subprocess, "run",
            side_effect=AssertionError("Unexpected external command")))
        self.stack.enter_context(patch.object(subprocess, "Popen",
            side_effect=AssertionError("Unexpected process")))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        worker.setup()

    def record(self, ident, goal="git status", folder=None, value=None):
        path = (folder or worker.PENDING) / (ident + ".json")
        path.write_text(json.dumps(value if value is not None else {"id": ident, "goal": goal}))
        return path

    def done(self, ident):
        return json.loads((worker.DONE / (ident + ".json")).read_text())

    def successful_runner(self, argv, **kwargs):
        if argv[0] == "ruff":
            return subprocess.CompletedProcess(argv, 0, "", "")
        if len(argv) > 1 and argv[1].endswith("proposal_builder.py"):
            proposal_builder.build(argv[2], argv[3], task_id=argv[5], invocation_id=argv[7])
            return subprocess.CompletedProcess(argv, 0, "fixture builder finished\n", "")
        if argv[:2] == ["git", "status"]:
            return subprocess.CompletedProcess(argv, 0, "?? fixture.py\n", "")
        raise AssertionError("Unexpected command")

    def build(self, *, owner="012345abcdef", invocation="1" * 32, source="value = 1\n"):
        self.ask.side_effect = None
        self.ask.return_value = source
        self.run.side_effect = self.successful_runner
        return proposal_builder.build("ai/example.py", "example", task_id=owner,
                                      invocation_id=invocation)

    def test_publication_without_python_link(self):
        with patch.object(os, "link", None, create=True):
            pipeline.publish(self.root, ("state", "portable"), b"complete")
        self.assertEqual(pipeline.read(self.root, ("state", "portable")), b"complete")

    def test_publication_collision_without_python_link(self):
        with patch.object(os, "link", None, create=True):
            pipeline.publish(self.root, ("state", "portable"), b"original")
            with self.assertRaises(FileExistsError):
                pipeline.publish(self.root, ("state", "portable"), b"replacement")
        self.assertEqual(pipeline.read(self.root, ("state", "portable")), b"original")

    def test_move_collision_without_python_link(self):
        source = ("state", "source")
        destination = ("state", "destination")
        with patch.object(os, "link", None, create=True):
            pipeline.publish(self.root, source, b"source evidence")
            pipeline.publish(self.root, destination, b"previous evidence")
            with self.assertRaises(FileExistsError):
                pipeline.move_new(self.root, source, destination)
        self.assertEqual(pipeline.read(self.root, source), b"source evidence")
        self.assertEqual(pipeline.read(self.root, destination), b"previous evidence")

    def test_task_ids(self):
        self.assertEqual(worker.task_session_path("012345abcdef"), orchestrator.task_session_path("012345abcdef"))
        for value in ("../bad", "ABCDEF123456", 1, "123"):
            with self.assertRaises((TypeError, ValueError)):
                pipeline.task_id(value)

    def test_real_controller_import_and_interfaces(self):
        sys.path.insert(0, str(PROJECT))
        from ai.agent import dev_controller

        with patch.object(dev_controller, "build_proposal", return_value={"artifact": "fixture"}), patch.object(dev_controller, "run_all_checks", return_value=[{"ok": True}]):
            controller = dev_controller.get_dev_controller()
            self.assertEqual(controller.handle_request({"action": "proposal", "name": "ai/x.py", "task": "example"}), {"artifact": "fixture"})
            self.assertEqual(controller.handle_request({"action": "healthcheck"}), [{"ok": True}])

    def test_checkpoint_isolation(self):
        for ident in ("000000000001", "000000000002"):
            orchestrator.checkpoint([{"role": "user", "content": ident}], 1, "running", ident)
        for ident in ("000000000001", "000000000002"):
            saved = json.loads(worker.task_session_path(ident).read_text())
            self.assertEqual(saved["messages"][0]["content"], ident)
            self.assertEqual(saved["task_id"], ident)

    def test_interrupted_recovery_does_not_replay(self):
        ident = "000000000001"
        self.record(ident, "private goal", worker.RUNNING)
        worker.recover()
        result = self.done(ident)
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(result["goal"], "private goal")
        self.assertIs(result["recovery"]["replayed"], False)
        self.run.assert_not_called()
        self.ask.assert_not_called()

    def test_recovery_collision_preserved(self):
        ident = "000000000001"
        running = self.record(ident, folder=worker.RUNNING)
        done = self.record(ident, folder=worker.DONE, value={"original": True})
        original = done.read_bytes()
        worker.recover()
        self.assertEqual(done.read_bytes(), original)
        self.assertTrue(running.exists())


    def test_recovery_dangling_symlink_preserved(self):
        ident = "000000000001"
        running = self.record(ident, folder=worker.RUNNING)
        destination = worker.DONE / (ident + ".json")
        destination.symlink_to(self.root / "missing-target")
        worker.recover()
        self.assertTrue(destination.is_symlink())
        self.assertTrue(running.exists())
        self.assertFalse((self.root / "missing-target").exists())

    def test_recovery_source_change_preserved(self):
        ident = "000000000001"
        running = self.record(ident, folder=worker.RUNNING)
        original_read = pipeline.read
        calls = 0

        def changing_read(root, parts, limit):
            nonlocal calls
            result = original_read(root, parts, limit)
            if tuple(parts) == running.relative_to(self.root).parts:
                calls += 1
                if calls == 2:
                    running.write_text('{"changed":true}')
                    return original_read(root, parts, limit)
            return result

        with patch.object(pipeline, "read", side_effect=changing_read):
            worker.recover()

        self.assertTrue(running.exists())
        self.assertEqual(running.read_text(), '{"changed":true}')

    def test_success_collision_preserved_and_next_job_runs(self):
        ident = "000000000001"
        previous = self.record(ident, folder=worker.DONE, value={"original": True})
        log = worker.DONE / (ident + ".log")
        log.write_text("original evidence")
        self.record(ident)
        self.record("000000000002")
        self.run.side_effect = self.successful_runner
        worker.cycle()
        self.assertEqual(previous.read_text(), '{"original": true}')
        self.assertEqual(log.read_text(), "original evidence")
        self.assertEqual(self.done("000000000002")["status"], "complete")
        self.assertEqual(len(list((self.base / "quarantine").glob("*.json"))), 1)

    def test_claim_race_preserves_existing_running(self):
        ident = "000000000001"
        self.record(ident)
        destination = worker.RUNNING / (ident + ".json")
        def collision(*args):
            destination.write_text('{"preexisting":true}')
            raise FileExistsError("simulated claim collision")
        with patch.object(pipeline, "move_new", side_effect=collision):
            worker.cycle()
        self.assertEqual(destination.read_text(), '{"preexisting":true}')
        self.assertFalse((worker.DONE / destination.name).exists())

    def test_malformed_queue_continues(self):
        self.record("000000000001", value=[])
        self.record("000000000002")
        self.run.side_effect = self.successful_runner
        worker.cycle()
        self.assertEqual(self.done("000000000001")["status"], "failed")
        self.assertEqual(base64.b64decode(self.done("000000000001")["original_record_b64"]), b"[]")
        self.assertEqual(self.done("000000000002")["status"], "complete")

    def test_deep_json_is_recorded_and_next_job_runs(self):
        path = worker.PENDING / "000000000001.json"
        path.write_text("[" * 5000 + "]" * 5000)
        self.record("000000000002")
        self.run.side_effect = self.successful_runner
        worker.cycle()
        self.assertEqual(self.done("000000000001")["status"], "failed")
        self.assertEqual(self.done("000000000002")["status"], "complete")

    def test_timeout_preserves_goal_and_continues(self):
        goal = 'PROPOSE ai/example.py "example"'
        self.record("000000000001", goal)
        self.record("000000000002")
        def runner(argv, **kwargs):
            if argv[0] != "git":
                raise subprocess.TimeoutExpired(argv, 180)
            return self.successful_runner(argv, **kwargs)
        self.run.side_effect = runner
        worker.cycle()
        failed = self.done("000000000001")
        self.assertEqual(failed["goal"], goal)
        self.assertEqual(failed["failure"]["kind"], "timeout")
        self.assertIs(failed["failure"]["retryable"], False)
        self.assertEqual(self.done("000000000002")["status"], "complete")

    def test_real_builder_worker_round_trip(self):
        self.ask.side_effect = None
        self.ask.return_value = "value = 1\n"
        self.run.side_effect = self.successful_runner
        self.record("012345abcdef", 'PROPOSE ai/example.py "example"')
        worker.cycle()
        done = self.done("012345abcdef")
        self.assertEqual(done["status"], "proposal_ready")
        self.assertEqual(done["verification"]["task_id"], "012345abcdef")
        self.assertFalse((self.root / "ai/example.py").exists())

    def test_distinct_invocations_preserve_same_target(self):
        first = self.build()
        second = self.build(invocation="2" * 32, source="value = 2\n")
        self.assertNotEqual(first["artifact"], second["artifact"])
        self.assertEqual(Path(first["artifact"]).read_text(), "value = 1\n")
        worker.verify_proposal("ai/example.py", "example", "1" * 32, "012345abcdef")

    def test_invocation_reuse_rejected(self):
        first = self.build()
        before = Path(first["artifact"]).read_bytes()
        with self.assertRaises(FileExistsError):
            self.build(source="value = 2\n")
        self.assertEqual(Path(first["artifact"]).read_bytes(), before)

    def test_tampered_candidate_rejected(self):
        result = self.build()
        Path(result["artifact"]).write_text("value = 2\n")
        with self.assertRaises(ValueError):
            worker.verify_proposal("ai/example.py", "example", "1" * 32, "012345abcdef")

    def test_wrong_task_or_invocation_rejected(self):
        self.build()
        for ident, invocation in (("fedcba543210", "1" * 32), ("012345abcdef", "2" * 32)):
            with self.assertRaises((OSError, ValueError)):
                worker.verify_proposal("ai/example.py", "example", invocation, ident)
        with self.assertRaises(ValueError):
            worker.verify_proposal("ai/example.py", "wrong task", "1" * 32, "012345abcdef")

    def test_timestamp_rounding_does_not_reject_bound_candidate(self):
        result = self.build()
        for name in ("artifact", "metadata"):
            os.utime(result[name], ns=(1, 1))
        checked = worker.verify_proposal("ai/example.py", "example", "1" * 32, "012345abcdef")
        self.assertTrue(checked["verified"])

    def test_target_change_after_generation_rejected(self):
        self.build()
        target = self.root / "ai/example.py"
        target.parent.mkdir(parents=True)
        target.write_text("changed = True\n")
        with self.assertRaises(ValueError):
            worker.verify_proposal("ai/example.py", "example", "1" * 32, "012345abcdef")

    def test_independent_lint_rejects(self):
        self.build()
        self.run.side_effect = lambda argv, **kwargs: subprocess.CompletedProcess(argv, 1, "lint error", "")
        with self.assertRaisesRegex(ValueError, "Independent Ruff"):
            worker.verify_proposal("ai/example.py", "example", "1" * 32, "012345abcdef")

    def test_parent_symlink_rejected_before_model_call(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        state = self.root / "state/proposals"
        state.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            self.build()
        self.ask.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])

    def test_metadata_symlink_cannot_overwrite_target(self):
        outside = self.root.parent / "victim"
        outside.write_text("original")
        original = pipeline.reserve
        def reserve(*args):
            relative = original(*args)
            self.root.joinpath(*relative, "metadata.json").symlink_to(outside)
            return relative
        with patch.object(pipeline, "reserve", side_effect=reserve), self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(outside.read_text(), "original")

    def test_atomic_publication_never_overwrites(self):
        path = ("state", "test.json")
        pipeline.publish(self.root, path, b"original")
        with self.assertRaises(FileExistsError):
            pipeline.publish(self.root, path, b"replacement")
        self.assertEqual(pipeline.read(self.root, path), b"original")

    def test_syntax_error_is_recorded_and_next_job_runs(self):
        self.record("000000000001", 'PROPOSE ai/example.py "example"')
        self.record("000000000002")
        self.run.side_effect = self.successful_runner
        with patch.object(worker, "verify_proposal", side_effect=SyntaxError("invalid fixture")):
            self.ask.side_effect = None
            self.ask.return_value = "value = 1\n"
            worker.cycle()
        self.assertEqual(self.done("000000000001")["failure"]["type"], "SyntaxError")
        self.assertEqual(self.done("000000000002")["status"], "complete")

    def conversation(self, code=1, marker=False, mixed=False, malformed=False):
        ident = "012345abcdef"
        path = self.record(ident, "Run lint and report whether every check passed.", worker.RUNNING)
        replies = [json.dumps({"action": "exec", "arg": "ruff check ai/agent/"})]
        if mixed:
            replies.append(json.dumps({"action": "exec", "arg": "git status --short"}))
        replies.append(json.dumps({"action": "finish", "answer": "Both passed."}))
        self.ask.side_effect = ["[]"] if malformed else replies
        def run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, code if argv[0] == "ruff" else 0,
                "EXIT CODE: 0" if marker else "fixture output", "")
        self.run.side_effect = run
        worker.execute(path)
        return self.done(ident)

    def test_stdout_cannot_spoof_success(self):
        done = self.conversation(marker=True)
        self.assertEqual(done["status"], "unverified")
        state = json.loads(Path(done["checkpoint"]).read_text())
        self.assertEqual(state["execution"][0]["returncode"], 1)
        self.assertNotIn("Both passed.", Path(done["log"]).read_text())

    def test_partial_success_remains_unverified(self):
        done = self.conversation(mixed=True)
        self.assertEqual(done["status"], "unverified")
        self.assertNotIn("Both passed.", Path(done["log"]).read_text())

    def test_generic_success_has_no_invented_acceptance_contract(self):
        done = self.conversation(code=0)
        self.assertEqual(done["status"], "unverified")
        self.assertIs(done["verification"]["task_outcome_verified"], False)

    def test_model_array_is_handled_as_task_failure(self):
        self.record("012345abcdef", "Inspect files")
        self.record("fedcba543210")
        self.ask.side_effect = ["[]"]
        self.run.side_effect = self.successful_runner
        worker.cycle()
        self.assertEqual(self.done("012345abcdef")["status"], "failed")
        self.assertEqual(self.done("fedcba543210")["status"], "complete")

    def test_down_service_is_not_healthy(self):
        self.run.side_effect = None
        self.run.return_value = subprocess.CompletedProcess([], 0, b"down: odin-task-worker: 1s", b"")
        self.assertIs(healthcheck.check_worker(healthcheck.HealthCheckConfig())["ok"], False)


    def test_negated_write_request_classification(self):
        cases = {
            "Do not modify files.": False,
            "Modify project files.": True,
            "Do not modify files, but delete logs.": True,
            "Reply with exactly ODIN_STAGE4_LIVE_OK.": False,
            "Never delete files.": False,
            "Never delete files; commit changes.": True,
        }

        warning = "Conversational tools cannot apply project changes"

        for index, (request, expected) in enumerate(cases.items()):
            with self.subTest(request=request):
                self.ask.side_effect = None
                self.ask.return_value = json.dumps({
                    "action": "finish",
                    "answer": "ODIN_STAGE4_LIVE_OK",
                })

                task_id = f"{index + 1:012x}"
                output = io.StringIO()

                with contextlib.redirect_stdout(output):
                    orchestrator.respond(request, task_id=task_id)

                self.assertEqual(warning in output.getvalue(), expected)

                checkpoint = json.loads(
                    orchestrator.task_session_path(task_id).read_text()
                )
                self.assertEqual(checkpoint["status"], "unverified")

    def test_unverified_answer_does_not_emit_failure(self):
        self.ask.side_effect = None
        self.ask.return_value = json.dumps({
            "action": "finish",
            "answer": "323"
        })
        with patch.object(orchestrator, "bridge_event") as events:
            orchestrator.respond(
                "What is 19 multiplied by 17?",
                task_id="012345abcdef"
            )
        sent = [c.args[0] for c in events.call_args_list]
        self.assertEqual(sent, ["task-started"])
        checkpoint = json.loads(
            orchestrator.task_session_path(
                "012345abcdef"
            ).read_text()
        )
        self.assertEqual(checkpoint["status"], "unverified")


    def test_legacy_cli_key_not_in_process_argv(self):
        import agent as legacy_agent

        fixture_key = "fixture-key-not-a-real-credential"

        def runner(argv, **kwargs):
            if argv[:2] == ["git", "-C"]:
                return subprocess.CompletedProcess(
                    argv, 0, "", ""
                )

            if argv[0] == "curl":
                self.assertEqual(
                    argv, ["curl", "--config", "-"]
                )
                self.assertNotIn(
                    fixture_key, " ".join(argv)
                )

                config = kwargs.get("input", "")
                self.assertIn(
                    "Authorization: Bearer " + fixture_key,
                    config
                )

                line = next(
                    (
                        item for item in config.splitlines()
                        if item.startswith("data-binary = ")
                    ),
                    None
                )
                self.assertIsNotNone(line)

                argument = json.loads(
                    line.split(" = ", 1)[1]
                )
                self.assertTrue(argument.startswith("@"))

                payload_path = Path(argument[1:])
                self.assertTrue(payload_path.is_file())
                self.assertEqual(
                    payload_path.stat().st_mode & 0o777,
                    0o600
                )

                payload = json.loads(
                    payload_path.read_text()
                )
                self.assertIn(
                    "safe fixture",
                    payload["messages"][-1]["content"]
                )

                response = {
                    "choices": [
                        {"message": {"content": "fixture answer"}}
                    ]
                }
                return subprocess.CompletedProcess(
                    argv, 0, json.dumps(response), ""
                )

            raise AssertionError("Unexpected subprocess")

        self.run.side_effect = runner

        with patch.object(
            legacy_agent, "ROOT", self.root
        ), patch.dict(
            os.environ, {"GROQ_API_KEY": fixture_key}
        ):
            legacy_agent.ask("safe fixture")


    def test_legacy_propose_key_not_in_process_argv(self):
        import propose as legacy_propose

        fixture_key = "fixture-propose-key"
        document = self.root / "docs/architecture.md"
        document.parent.mkdir(parents=True, exist_ok=True)
        original = "# Fixture architecture\n" + "Safe test content.\n" * 8
        document.write_text(original)
        observed = []

        def runner(argv, **kwargs):
            if argv[:2] == ["git", "status"]:
                return subprocess.CompletedProcess(argv, 0, "", "")

            if argv[0] == "curl":
                observed.append(True)
                self.assertEqual(argv, ["curl", "--config", "-"])
                self.assertNotIn(fixture_key, repr(argv))

                config = kwargs["input"]
                self.assertIn(
                    "Authorization: Bearer " + fixture_key,
                    config
                )

                arg = json.loads(next(
                    line.split(" = ", 1)[1]
                    for line in config.splitlines()
                    if line.startswith("data-binary = ")
                ))

                self.assertTrue(arg.startswith("@"))
                payload_path = Path(arg[1:])
                self.assertEqual(
                    payload_path.stat().st_mode & 0o777,
                    0o600
                )

                payload = json.loads(payload_path.read_text())
                self.assertEqual(
                    payload["model"], "openai/gpt-oss-120b"
                )
                self.assertIn(
                    "Improve clarity.",
                    payload["messages"][-1]["content"]
                )

                reply = {
                    "choices": [{
                        "message": {"content": original}
                    }]
                }
                return subprocess.CompletedProcess(
                    argv, 0, json.dumps(reply), ""
                )

            raise AssertionError("Unexpected subprocess")

        self.run.side_effect = runner

        with patch.object(
            legacy_propose, "ROOT", self.root
        ), patch.dict(
            os.environ, {"GROQ_API_KEY": fixture_key}
        ), patch.object(sys, "argv", ["propose.py"]):
            self.assertEqual(legacy_propose.main(), 0)

        self.assertEqual(len(observed), 1)
        self.assertEqual(document.read_text(), original)

    def test_api_nonobject_is_bounded_error(self):
        self.run.side_effect = None
        self.run.return_value = subprocess.CompletedProcess([], 0, "[]", "")
        with patch.dict(os.environ, {"GROQ_API_KEY": "offline-fixture-only"}), self.assertRaises(RuntimeError):
            self.original_ask([])

    def test_multibyte_byte_limit_prevents_publication(self):
        with self.assertRaises(ValueError):
            self.build(source="#" + "é" * 26000 + "\n")
        self.assertFalse(list((self.root / "state/proposals").rglob("candidate.py")))


if __name__ == "__main__":
    unittest.main()
