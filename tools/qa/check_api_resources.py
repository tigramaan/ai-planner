"""Bounded, local-only API QA teardown verification. No Docker mutations."""

import json
import os
import select
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
PROBE = "services/api/tests/qa_lifecycle_probe.py"
DATABASE_FILES = (ROOT / "test-planner.db", ROOT / "services/api/test-planner.db")


def docker_resources(run):
    resources = {}
    for kind in ("volume", "container"):
        command = ["docker", kind, "ls", "-q"]
        if kind == "container":
            command.append("-a")
        result = subprocess.run(command, capture_output=True, timeout=10, check=True)
        resources[kind] = set(result.stdout.splitlines())
        owned = command + [
            "--filter", "label=qa.owner=aiplanner",
            "--filter", "label=qa.project=aiplanner",
            "--filter", f"label=qa.run={run}",
        ]
        result = subprocess.run(owned, capture_output=True, timeout=10, check=True)
        resources[f"owned_{kind}"] = set(result.stdout.splitlines())
    return resources


def group_exists(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False


def stop_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=3)


def interrupted(signum, frame):
    raise InterruptedError("QA checker interrupted")


def scenario(name, expected_rc, delivery_signal=None):
    run = uuid4().hex
    before = docker_resources(run)
    files_before = {path for path in DATABASE_FILES if path.exists()}
    expiry = (datetime.now(UTC) + timedelta(minutes=15)).isoformat()
    read_fd, write_fd = os.pipe()
    process = None
    try:
        environment = dict(os.environ)
        environment.update(
            QA_RESOURCE_RUN=run, QA_RESOURCE_EXPIRY=expiry, QA_PROBE_READY_FD=str(write_fd)
        )
        selection = "success" if name.startswith("success") else (
            "failure" if name == "failure" else "wait"
        )
        process = subprocess.Popen(
            [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", PROBE,
             "-k", selection],
            cwd=ROOT,
            env=environment,
            pass_fds=(write_fd,),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.close(write_fd)
        write_fd = None
        readable, _, _ = select.select([read_fd], [], [], 20)
        if not readable or os.read(read_fd, 5) != b"ready":
            raise RuntimeError("synthetic probe did not become ready")
        if name == "timeout":
            try:
                process.wait(timeout=0.25)
            except subprocess.TimeoutExpired:
                stop_group(process)
            else:
                raise RuntimeError("timeout probe exited early")
        elif delivery_signal is not None:
            os.killpg(process.pid, delivery_signal)
        rc = process.wait(timeout=10)
    finally:
        if process is not None:
            stop_group(process)
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
    after = docker_resources(run)
    # No child should remain; give the kernel a bounded scheduling grace period.
    deadline = time.monotonic() + 1
    while group_exists(process.pid) and time.monotonic() < deadline:
        time.sleep(0.02)
    evidence = {
        "scenario": name, "owner": "aiplanner", "project": "aiplanner", "run": run,
        "purpose": "api-tests", "expiry": expiry,
        "expected_rc": expected_rc, "actual_rc": rc,
        "volumes_before": len(before["volume"]), "volumes_after": len(after["volume"]),
        "inventory_new_volumes": len(after["volume"] - before["volume"]),
        "owned_volumes_before": len(before["owned_volume"]),
        "owned_volumes_after": len(after["owned_volume"]),
        "new_volumes": len(after["owned_volume"] - before["owned_volume"]),
        "containers_before": len(before["container"]),
        "containers_after": len(after["container"]),
        "inventory_new_containers": len(after["container"] - before["container"]),
        "owned_containers_before": len(before["owned_container"]),
        "owned_containers_after": len(after["owned_container"]),
        "new_containers": len(after["owned_container"] - before["owned_container"]),
        "orphan_process_groups": int(group_exists(process.pid)),
        "new_disposable_files": len(
            {path for path in DATABASE_FILES if path.exists()} - files_before
        ),
    }
    print(json.dumps(evidence), flush=True)
    return rc == expected_rc and all(evidence[key] == 0 for key in (
        "new_volumes", "new_containers", "orphan_process_groups", "new_disposable_files",
        "owned_volumes_after", "owned_containers_after",
    ))


def main():
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, interrupted)
    scenarios = (
        ("success", 0, None), ("failure", 1, None), ("timeout", -15, None),
        ("sigint", 2, signal.SIGINT), ("sigterm", -15, signal.SIGTERM),
        ("sigkill", -9, signal.SIGKILL), ("success_after_crash", 0, None),
    )
    passed = [scenario(*value) for value in scenarios]
    return 0 if all(passed) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (InterruptedError, RuntimeError, subprocess.SubprocessError):
        print("QA check incomplete; child cleanup attempted; no raw logs emitted.", file=sys.stderr)
        sys.exit(1)
