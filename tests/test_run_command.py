import os
import subprocess
import time
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from AlfTools import Permissions, RunCommand
from AlfTools.RunCommand import run_command


def docker_ready():
    try:
        return subprocess.run(["docker", "image", "inspect", "alf-sandbox"],
                              capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


real_docker = pytest.mark.skipif(not docker_ready(), reason="alf-sandbox image unavailable")


@pytest.fixture
def allowed(tmp_path, monkeypatch):
    """A tmp allowed dir with a .git folder, used as cwd."""
    (tmp_path / ".git").mkdir()
    saved = Permissions.ALLOWED_DIRS[:]
    Permissions.ALLOWED_DIRS[:] = [str(tmp_path)]
    monkeypatch.chdir(tmp_path)
    yield tmp_path
    Permissions.ALLOWED_DIRS[:] = saved


@pytest.fixture
def calls(monkeypatch):
    """Record every run() call; docker succeeds."""
    recorded = []

    def fake(argv, **kw):
        recorded.append((argv, kw))
        return SimpleNamespace(returncode=0, stdout="o", stderr="")

    monkeypatch.setattr(RunCommand, "run", fake)
    return recorded


def test_argv(allowed, calls):
    """The container is started with all the isolation flags."""
    assert "exit code 0" in run_command("echo hi")
    argv, kw = calls[1]
    d = str(allowed.resolve())
    for flag in ["--rm", "--network", "none", "--read-only", "--tmpfs", "--memory", "512m", "--cpus",
                 "--pids-limit", "--cap-drop", "ALL", "no-new-privileges", "HOME=/tmp"]:
        assert flag in argv
    assert f"{os.getuid()}:{os.getgid()}" in argv
    assert argv.count("-v") == 2
    assert f"{d}:{d}" in argv
    assert f"{d}/.git:{d}/.git:ro" in argv
    assert argv.index(f"{d}/.git:{d}/.git:ro") > argv.index(f"{d}:{d}")
    assert argv[argv.index("-w") + 1] == d
    assert argv[-8:] == ["alf-sandbox", "timeout", "-s", "KILL", "13", "sh", "-c", "echo hi"]
    assert argv[argv.index("--name") + 1].startswith("alf-")
    assert not kw.get("shell")
    assert kw["timeout"] == 12


def test_workdir_fallback(allowed, calls, monkeypatch, tmp_path_factory):
    """Outside the allowed dirs, the first allowed dir is the workdir."""
    monkeypatch.chdir(tmp_path_factory.mktemp("elsewhere"))
    run_command("pwd")
    argv = calls[1][0]
    assert argv[argv.index("-w") + 1] == str(allowed.resolve())


def test_refused_docker_missing(allowed, monkeypatch):
    """No docker binary: refused, nothing else run."""
    seen = []

    def fake(argv, **kw):
        seen.append(argv)
        raise FileNotFoundError("docker")

    monkeypatch.setattr(RunCommand, "run", fake)
    out = run_command("ls")
    assert "refused: sandbox unavailable, nothing was run" in out
    assert "docker build -t alf-sandbox ." in out
    assert len(seen) == 1


def test_refused_inspect_fails(allowed, monkeypatch):
    """Image missing: refused, nothing else run."""
    seen = []

    def fake(argv, **kw):
        seen.append(argv)
        return SimpleNamespace(returncode=1, stdout="", stderr="no such image")

    monkeypatch.setattr(RunCommand, "run", fake)
    out = run_command("ls")
    assert "refused: sandbox unavailable" in out and "no such image" in out
    assert len(seen) == 1


def test_refused_inspect_timeout(allowed, monkeypatch):
    """Inspect timeout: refused, nothing else run."""
    seen = []

    def fake(argv, **kw):
        seen.append(argv)
        raise subprocess.TimeoutExpired(argv, 5)

    monkeypatch.setattr(RunCommand, "run", fake)
    assert "refused: sandbox unavailable" in run_command("ls")
    assert len(seen) == 1


def test_timeout_kills_container(allowed, monkeypatch):
    """On timeout, docker kill targets the same container name."""
    seen = []

    def fake(argv, **kw):
        seen.append(argv)
        if argv[:2] == ["docker", "run"]:
            raise subprocess.TimeoutExpired(argv, 12)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(RunCommand, "run", fake)
    assert run_command("sleep 60") == "sleep 60:\ntimeout after 12s"
    name = seen[1][seen[1].index("--name") + 1]
    assert seen[2] == ["docker", "kill", name]


@real_docker
def test_real_output(allowed):
    """Output and exit code come back."""
    out = run_command("echo hi; echo err >&2; exit 3")
    assert out == "echo hi; echo err >&2; exit 3:\nexit code 3\nstdout:\nhi\n\nstderr:\nerr\n"


@real_docker
def test_real_write_in_allowed_dir(allowed):
    """A file written in the allowed dir appears on the host."""
    run_command("echo data > out.txt")
    assert (allowed / "out.txt").read_text() == "data\n"


@real_docker
def test_real_no_network(allowed):
    """The network is unreachable."""
    assert "exit code 0" not in run_command("wget -T 3 -qO- http://1.1.1.1 || nc -w 3 1.1.1.1 80 </dev/null")


@real_docker
def test_real_write_outside_mount_fails(allowed):
    """The root filesystem is read-only."""
    assert "exit code 0" not in run_command("echo x > /usr/x")


@real_docker
def test_real_git_read_only(allowed):
    """Writing into .git fails."""
    assert "exit code 0" not in run_command("echo x > .git/x")
    assert not (allowed / ".git" / "x").exists()


def tree(root):
    """A tree with secrets, nested .git dir and .git file, a symlink."""
    (root / "sub" / ".git" / "hooks").mkdir(parents=True)
    (root / "wt").mkdir()
    (root / "wt" / ".git").write_text("gitdir: x")
    (root / ".env").write_text("SECRET=topsecret")
    (root / "sub" / ".env").write_text("SECRET=topsecret")
    (root / ".env.example").write_text("A=1")
    (root / "key.pem").write_text("SECRET=topsecret")
    (root / "normal.txt").write_text("hello")
    (root / "link").symlink_to(root / ".env")
    (root / "gitlink").symlink_to(root / "sub")
    (root / "sub" / "sublink").symlink_to(root / "normal.txt")


def test_mounts_secrets_and_git(allowed, calls):
    """Secrets are overlaid by /dev/null, every .git is ro, after the parent mount."""
    tree(allowed)
    run_command("ls")
    argv = calls[1][0]
    d = str(allowed.resolve())
    mounts = [argv[i + 1] for i, a in enumerate(argv) if a == "-v"]
    assert mounts[0] == f"{d}:{d}"
    for f in [".env", "sub/.env", "key.pem"]:
        assert f"/dev/null:{d}/{f}:ro" in mounts
    for f in [".env.example", "normal.txt", "link", "sub/sublink", "gitlink"]:
        assert not any(m.endswith(f"{d}/{f}:ro") or m.endswith(f":{d}/{f}") for m in mounts[1:])
    for g in [".git", "sub/.git", "wt/.git"]:
        assert f"{d}/{g}:{d}/{g}:ro" in mounts
    assert not any("sub/.git/" in m for m in mounts)
    assert len(mounts) == 1 + 3 + 3


def test_mounts_ignore_symlinked_git(allowed, calls):
    """A .git symlink is not mounted."""
    (allowed / "real").mkdir()
    (allowed / "x").mkdir()
    (allowed / "x" / ".git").symlink_to(allowed / "real")
    run_command("ls")
    assert not any("x/.git" in a for a in calls[1][0])


@real_docker
def test_real_secrets_hidden_and_git_protected(allowed):
    """Bulk readers never see secrets; nested .git is not writable; host is untouched."""
    tree(allowed)
    for cmd in ["grep -r . .", "tar cf - . | tar xOf - ", "find . -type f -exec cat {} +"]:
        out = run_command(cmd)
        assert "topsecret" not in out
        assert "hello" in out
    assert "exit code 0" not in run_command("echo x > sub/.git/hooks/pre-commit")
    assert "exit code 0" not in run_command("echo x > wt/.git")
    assert not (allowed / "sub/.git/hooks/pre-commit").exists()
    assert (allowed / "wt/.git").read_text() == "gitdir: x"
    for f in [".env", "sub/.env", "key.pem"]:
        assert (allowed / f).read_text() == "SECRET=topsecret"


@real_docker
def test_real_memory_hog_killed(allowed):
    """A process exceeding 512m is killed."""
    assert "exit code 0" not in run_command("tail /dev/zero")


@real_docker
def test_real_host_files_not_visible(allowed):
    """The container has its own filesystem."""
    host = open("/etc/hostname").read()
    out = run_command("cat /etc/hostname; ls /home")
    assert host not in out.split("stdout:\n", 1)[1] or host.strip() == ""
    assert os.path.basename(os.path.expanduser("~")) not in out.split("stdout:\n", 1)[1]


@real_docker
def test_real_no_container_left_after_timeout(allowed):
    """After a timeout, no alf-* container remains."""
    assert run_command("sleep 60").endswith("timeout after 12s")
    ps = subprocess.run(["docker", "ps", "-q", "--filter", "name=^alf-"], capture_output=True, text=True)
    assert ps.stdout.strip() == ""


@real_docker
def test_real_container_ends_when_client_killed(allowed, calls):
    """If the docker client dies, the container stops itself (timeout 13s)."""
    run_command("sleep 60")
    argv = calls[1][0]
    name = argv[argv.index("--name") + 1]
    client = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    client.kill()
    client.wait()
    deadline = time.time() + 16
    while time.time() < deadline:
        ps = subprocess.run(["docker", "ps", "-q", "--filter", f"name=^{name}$"], capture_output=True, text=True)
        if not ps.stdout.strip():
            return
        time.sleep(0.5)
    subprocess.run(["docker", "kill", name], capture_output=True)
    pytest.fail("container still running")


def test_sandbox_default_true():
    """The sandbox is on by default."""
    assert RunCommand.SANDBOX is True


def test_no_sandbox_uses_host_shell(allowed, calls, monkeypatch):
    """Without sandbox: one shell=True call, no docker argv."""
    monkeypatch.setattr(RunCommand, "SANDBOX", False)
    out = run_command("ls")
    assert len(calls) == 1
    assert calls[0][0] == "ls"
    assert calls[0][1]["shell"] is True
    assert out == "ls:\nexit code 0\nstdout:\no\nstderr:\n"


def test_no_sandbox_real_run(allowed, monkeypatch):
    """A real host command returns exit code 0 and its output."""
    monkeypatch.setattr(RunCommand, "SANDBOX", False)
    out = run_command("echo hi")
    assert "exit code 0" in out and "hi" in out


def test_no_sandbox_timeout(allowed, monkeypatch):
    """Host timeout gives the same message."""
    def fake(argv, **kw):
        raise subprocess.TimeoutExpired(argv, 12)

    monkeypatch.setattr(RunCommand, "SANDBOX", False)
    monkeypatch.setattr(RunCommand, "run", fake)
    assert run_command("sleep 60") == "sleep 60:\ntimeout after 12s"


def test_args_no_sandbox():
    """--no-sandbox is accepted and defaults to False."""
    from CliTools.Args import parseArgs
    assert parseArgs([]).no_sandbox is False
    assert parseArgs(["--no-sandbox"]).no_sandbox is True
