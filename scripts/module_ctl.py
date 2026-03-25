#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / ".runtime"

MODULES = {
    "ingest_registry": {
        "path": PROJECT_ROOT / "modules" / "ingest_registry",
        "env_host": "INGEST_REGISTRY_HOST",
        "env_port": "INGEST_REGISTRY_PORT",
        "default_port": 8101,
    },
    "doc_classifier": {
        "path": PROJECT_ROOT / "modules" / "doc_classifier",
        "env_host": "DOC_CLASSIFIER_HOST",
        "env_port": "DOC_CLASSIFIER_PORT",
        "default_port": 8102,
    },
    "project_builder": {
        "path": PROJECT_ROOT / "modules" / "project_builder",
        "env_host": "PROJECT_BUILDER_HOST",
        "env_port": "PROJECT_BUILDER_PORT",
        "default_port": 8103,
    },
}


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key] = value
    return env


def get_meta(module_name: str) -> dict[str, object]:
    if module_name not in MODULES:
        raise ValueError(f"Unknown module '{module_name}'.")
    meta = dict(MODULES[module_name])
    meta["pid_file"] = RUNTIME_DIR / f"{module_name}.pid"
    meta["log_file"] = RUNTIME_DIR / f"{module_name}.log"
    return meta


def get_port(meta: dict[str, object], env: dict[str, str]) -> int:
    env_port = str(meta["env_port"])
    return int(env.get(env_port, str(meta["default_port"])))


def get_host(meta: dict[str, object], env: dict[str, str]) -> str:
    env_host = str(meta["env_host"])
    return env.get(env_host, "127.0.0.1")


def read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text().strip())
    except ValueError:
        return None


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def port_open(host: str, port: int) -> bool:
    result = subprocess.run(
        ["ss", "-ltn"],
        capture_output=True,
        text=True,
        check=False,
    )
    needle = f":{port} "
    return needle in result.stdout or result.returncode == 0 and f":{port}\n" in result.stdout


def cleanup_stale_pid(pid_file: Path) -> None:
    pid = read_pid(pid_file)
    if pid is not None and not pid_alive(pid):
        pid_file.unlink(missing_ok=True)


def start_module(module_name: str) -> int:
    env = load_env()
    meta = get_meta(module_name)
    module_path = Path(meta["path"])
    pid_file = Path(meta["pid_file"])
    log_file = Path(meta["log_file"])
    host = get_host(meta, env)
    port = get_port(meta, env)

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_stale_pid(pid_file)

    pid = read_pid(pid_file)
    if pid_alive(pid):
        print(f"status=already_running pid={pid} module={module_name} host={host} port={port}")
        return 0

    if port_open("127.0.0.1", port):
        print(f"error=port_in_use module={module_name} port={port}", file=sys.stderr)
        return 1

    log_handle = log_file.open("ab")
    process = subprocess.Popen(
        [str(PROJECT_ROOT / "venv" / "bin" / "python"), "main.py"],
        cwd=module_path,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=env,
    )
    pid_file.write_text(str(process.pid))

    for _ in range(20):
        if port_open("127.0.0.1", port):
            print(f"status=started pid={process.pid} module={module_name} host={host} port={port}")
            return 0
        if process.poll() is not None:
            print(f"error=process_exited module={module_name} exit_code={process.returncode}", file=sys.stderr)
            return 1
        time.sleep(0.25)

    print(f"error=start_timeout module={module_name} pid={process.pid} port={port}", file=sys.stderr)
    return 1


def stop_module(module_name: str) -> int:
    meta = get_meta(module_name)
    pid_file = Path(meta["pid_file"])
    pid = read_pid(pid_file)
    if not pid_alive(pid):
        pid_file.unlink(missing_ok=True)
        print(f"status=not_running module={module_name}")
        return 0

    os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        if not pid_alive(pid):
            pid_file.unlink(missing_ok=True)
            print(f"status=stopped module={module_name} pid={pid}")
            return 0
        time.sleep(0.25)

    os.kill(pid, signal.SIGKILL)
    pid_file.unlink(missing_ok=True)
    print(f"status=killed module={module_name} pid={pid}")
    return 0


def status_module(module_name: str) -> int:
    env = load_env()
    meta = get_meta(module_name)
    pid_file = Path(meta["pid_file"])
    pid = read_pid(pid_file)
    host = get_host(meta, env)
    port = get_port(meta, env)
    alive = pid_alive(pid)
    listening = port_open("127.0.0.1", port)
    state = "running" if alive else "stopped"
    print(
        f"status={state} module={module_name} pid={pid or ''} host={host} port={port} listening={'yes' if listening else 'no'}"
    )
    return 0 if alive else 1


def health_module(module_name: str) -> int:
    env = load_env()
    meta = get_meta(module_name)
    port = get_port(meta, env)
    listening = port_open("127.0.0.1", port)
    print(f"module={module_name} port={port} healthy={'yes' if listening else 'no'}")
    return 0 if listening else 1


def restart_module(module_name: str) -> int:
    stop_module(module_name)
    return start_module(module_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Module process controller")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "health"])
    parser.add_argument("module", choices=sorted(MODULES.keys()))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    command = args.command
    if command == "start":
        return start_module(args.module)
    if command == "stop":
        return stop_module(args.module)
    if command == "restart":
        return restart_module(args.module)
    if command == "status":
        return status_module(args.module)
    if command == "health":
        return health_module(args.module)
    raise ValueError(f"Unsupported command '{command}'")


if __name__ == "__main__":
    raise SystemExit(main())
