#!/usr/bin/env python3
"""Find the ai-system data root, seed it, and pair it with maintenance worktrees.

The rules live in the "Data root" section of _core/CONVENTIONS.md. Python 3
standard library only.

  resolve                    print the data checkout this ai-system checkout uses
  checkout                   print this ai-system checkout (its top folder: main, clone or worktree)
  init                       create the data root when missing and seed it (setup runs this)
  commit -m MSG [PATH...]    commit in the data checkout, one commit at a time
  add BRANCH [--from REF]    ai-system worktree + data worktree on the same branch name
  merge BRANCH               commit the data worktree, merge data, then merge code
  remove BRANCH              remove both worktrees and both branches, after a confirmation
"""
import argparse
import fcntl
import fnmatch
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

LAYOUT_VERSION = 1
DEFAULT_ROOT = "~/.config/ai-system"
ENV_VAR = "AI_SYSTEM_HOME"
POINTER = ".data-root"
WORKTREES = ".worktrees"
HERE = Path(__file__).resolve().parent
SEED = HERE / "seed"
SEED_FILES = (("LAYOUT", "LAYOUT"), ("gitignore", ".gitignore"),
              ("gitattributes", ".gitattributes"), ("README.md", "README.md"))
KEEP_DIRS = ("workspaces", "log/briefs", "archive")
SECRET_NAMES = (".env", ".env.*", "*.env", "*.pem", "*.key", "*.secret", "id_rsa*", "id_ed25519*")
LOCK_NAME = "ai-system-commit.lock"
LOCK_TIMEOUT = 60


class Stop(Exception):
    """A check failed. The message says what to do next."""


def git(cwd, *args, check=True, stdin=None):
    r = subprocess.run(["git", "-C", str(cwd), *args], input=stdin,
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        detail = (r.stderr.strip() or r.stdout.strip())
        raise Stop(f"git {' '.join(args)} failed in {cwd}:\n{detail}")
    return r


def out(cwd, *args):
    return git(cwd, *args).stdout.strip()


# ---------- where things are ----------

def checkout_info(code=HERE):
    """(top, main_top, is_main, branch) for the ai-system checkout holding `code`."""
    top = Path(out(code, "rev-parse", "--show-toplevel"))
    git_dir = Path(out(code, "rev-parse", "--path-format=absolute", "--git-dir"))
    common = Path(out(code, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    branch = git(code, "symbolic-ref", "--quiet", "--short", "HEAD", check=False).stdout.strip()
    return top, common.parent, git_dir == common, branch or None


def read_pointer(top):
    f = Path(top) / POINTER
    if not f.is_file():
        return None
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            p = Path(os.path.expandvars(os.path.expanduser(line)))
            if not p.is_absolute():
                raise Stop(f"{f}: the path must start with ~ or /")
            return p
    return None


def data_root(code=HERE):
    """The main data checkout: .data-root, then AI_SYSTEM_HOME, then ~/.config/ai-system."""
    top, main_top, _, _ = checkout_info(code)
    for t in dict.fromkeys((top, main_top)):
        p = read_pointer(t)
        if p:
            return p
    env = os.environ.get(ENV_VAR, "").strip()
    if env:
        return Path(os.path.expanduser(env))
    return Path(os.path.expanduser(DEFAULT_ROOT))


def is_checkout(path):
    return (Path(path) / ".git").exists()


def resolve(code=HERE):
    """Main ai-system checkout -> main data checkout; worktree on branch X -> data worktree X."""
    _, _, is_main, branch = checkout_info(code)
    root = data_root(code)
    if is_main:
        if not is_checkout(root):
            raise Stop(f"no data root at {root}: run setup (data_root.py init)")
        return root
    if not branch:
        raise Stop("this ai-system worktree has no branch, so no data worktree is paired with it")
    target = root / WORKTREES / branch
    if not is_checkout(target):
        raise Stop(f"no data worktree at {target}: maintenance worktrees are made with "
                   f"data_root.py add <branch>, which pairs the data side")
    return target


def branch_exists(repo, branch):
    return git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}",
               check=False).returncode == 0


def current_branch(repo):
    return git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False).stdout.strip()


def code_worktree(main_top, branch):
    path = None
    for line in out(main_top, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree "):])
        elif line == f"branch refs/heads/{branch}":
            return path
    return None


def dirty(checkout):
    return bool(out(checkout, "status", "--porcelain", "--untracked-files=all"))


def check_branch_name(branch):
    if git(".", "check-ref-format", "--branch", branch, check=False).returncode != 0:
        raise Stop(f"not a valid branch name: {branch}")


# ---------- commits ----------

def is_secret(path):
    name = PurePosixPath(path).name
    return any(fnmatch.fnmatch(name, pat) for pat in SECRET_NAMES)


def changed_paths(checkout):
    entries = git(checkout, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.split("\0")
    paths, i = [], 0
    while i < len(entries):
        e = entries[i]
        i += 1
        if not e:
            continue
        paths.append(e[3:])
        if e[0] in "RC":  # the original path of a rename follows
            paths.append(entries[i])
            i += 1
    return paths


@contextmanager
def commit_lock(checkout):
    """Serialize commits into one checkout. Held for the commit only."""
    lock = Path(out(checkout, "rev-parse", "--path-format=absolute", "--git-dir")) / LOCK_NAME
    with open(lock, "w") as fh:
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > deadline:
                    raise Stop(f"another commit still holds {lock}; try again")
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def commit(checkout, message, paths=None):
    """Stage named paths (all changed ones when none are given) and commit. None if nothing to do."""
    with commit_lock(checkout):
        todo = changed_paths(checkout) if not paths else [str(p) for p in paths]
        secrets = [p for p in todo if is_secret(p)]
        if secrets:
            raise Stop("refusing to stage secret-looking files: " + ", ".join(secrets))
        if not todo:
            return None
        git(checkout, "add", "--pathspec-from-file=-", "--pathspec-file-nul",
            stdin="\0".join(todo))
        if git(checkout, "diff", "--cached", "--quiet", check=False).returncode == 0:
            return None
        git(checkout, "commit", "-q", "-m", message)
        return out(checkout, "rev-parse", "--short", "HEAD")


# ---------- setup ----------

def example_target(rel):
    """workspaces/<ws>/targets/<path>/<name>.example.<ext> -> workspaces/<ws>/<path>/<name>.<ext>."""
    parts = PurePosixPath(rel).parts
    if len(parts) < 4 or parts[0] != "workspaces" or parts[2] != "targets":
        return None
    if ".example." not in parts[-1]:
        return None
    stem, ext = parts[-1].split(".example.", 1)
    return PurePosixPath("workspaces", parts[1], *parts[3:-1], f"{stem}.{ext}")


def layout_version(root):
    f = Path(root) / "LAYOUT"
    if not f.is_file():
        return None
    first = f.read_text().splitlines()[0:1]
    try:
        return int(first[0].split(":", 1)[1])
    except (IndexError, ValueError):
        raise Stop(f"{f}: the first line must be 'version: <number>'")


def init(code=HERE):
    """Create the data root when it is missing and seed what is missing. Never overwrites."""
    top, _, _, _ = checkout_info(code)
    root = data_root(code)
    made = []
    if not is_checkout(root):
        if root.exists() and any(root.iterdir()):
            raise Stop(f"{root} holds files but is not a git repo; it was not touched. "
                       f"Make it a data repo by hand, or point .data-root or {ENV_VAR} elsewhere")
        root.mkdir(parents=True, exist_ok=True)
        git(root, "init", "-q", "-b", "main")
        print(f"created data repo {root}")
    elif (root / ".git").is_file():
        raise Stop(f"{root} is a worktree; the data root must be a main checkout")
    version = layout_version(root)
    if version is not None and version != LAYOUT_VERSION:
        raise Stop(f"{root}/LAYOUT is version {version}, this ai-system knows {LAYOUT_VERSION}; "
                   f"run the layout migration first")

    def place(dst, write):
        target = root / dst
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            write(target)
            made.append(str(dst))

    for src, dst in SEED_FILES:
        place(PurePosixPath(dst), lambda t, s=src: shutil.copyfile(SEED / s, t))
    for d in KEEP_DIRS:
        if not (root / d).exists():
            place(PurePosixPath(d, ".gitkeep"), lambda t: t.write_text(""))
    listed = git(top, "ls-files", "-z", "--", "workspaces/*/targets/*").stdout.split("\0")
    for rel in filter(None, listed):
        dst = example_target(rel)
        if dst:
            place(dst, lambda t, s=rel: shutil.copyfile(top / s, t))
    if made:
        sha = commit(root, f"Seed data root (layout {LAYOUT_VERSION})", made)
        print(f"seeded {len(made)} file(s), commit {sha}:")
        for m in made:
            print(f"  {m}")
    else:
        print(f"data root {root} is complete; nothing changed")
    return root


# ---------- maintenance pairing ----------

def add(branch, code_path=None, code=HERE, start=None):
    check_branch_name(branch)
    _, main_top, _, _ = checkout_info(code)
    root = data_root(code)
    if not is_checkout(root):
        raise Stop(f"no data root at {root}: run setup (data_root.py init) first")
    code_wt = (Path(code_path).expanduser().resolve() if code_path
               else main_top.parent / f"{main_top.name}.worktrees" / branch)
    data_wt = root / WORKTREES / branch
    for repo in (main_top, root):
        if branch_exists(repo, branch):
            raise Stop(f"branch {branch} already exists in {repo}; nothing created")
    for p in (code_wt, data_wt):
        if p.exists():
            raise Stop(f"{p} already exists; nothing created")
    git(main_top, "worktree", "add", "-q", "-b", branch, str(code_wt), *([start] if start else []))
    try:
        git(root, "worktree", "add", "-q", "-b", branch, str(data_wt))
    except Stop:
        git(main_top, "worktree", "remove", str(code_wt), check=False)
        git(main_top, "branch", "-d", branch, check=False)
        raise
    print(f"code worktree: {code_wt}")
    print(f"data worktree: {data_wt}")
    return code_wt, data_wt


def merge(branch, code=HERE):
    _, main_top, _, _ = checkout_info(code)
    root = data_root(code)
    code_wt = code_worktree(main_top, branch)
    data_wt = root / WORKTREES / branch
    if code_wt is None or code_wt == main_top:
        raise Stop(f"no ai-system worktree on branch {branch}")
    if not is_checkout(data_wt):
        raise Stop(f"no data worktree at {data_wt}")
    for repo in (main_top, root):
        if current_branch(repo) == branch:
            raise Stop(f"the main checkout {repo} is on {branch}; switch it back first")
    if dirty(code_wt):
        raise Stop(f"{code_wt} has uncommitted changes; commit them on {branch} first. Nothing merged")
    commit(data_wt, f"Data from {branch}")
    commit(root, f"Save data before merging {branch}")
    pre = git(main_top, "merge-tree", "--write-tree", "--name-only", "HEAD", branch, check=False)
    if pre.returncode != 0:
        raise Stop(f"code branch {branch} conflicts with {current_branch(main_top)}; "
                   f"nothing merged. Merge {current_branch(main_top)} into it in {code_wt} first")
    with commit_lock(root):
        r = git(root, "merge", "--no-ff", "--no-edit", branch, check=False)
        if r.returncode != 0:
            git(root, "merge", "--abort", check=False)
            raise Stop(f"data merge of {branch} conflicts; stopped before the code merge. "
                       f"Merge {current_branch(root)} into {branch} in {data_wt}, then run merge again")
    r = git(main_top, "merge", "--no-ff", "--no-edit", branch, check=False)
    if r.returncode != 0:
        git(main_top, "merge", "--abort", check=False)
        raise Stop(f"data is merged but the code merge of {branch} failed in {main_top}:\n"
                   f"{(r.stderr or r.stdout).strip()}\nFix it there and run git merge {branch}")
    print(f"merged {branch}: data into {root}, code into {main_top}")
    print(f"remove the worktrees with: data_root.py remove {branch}")


def prune_empty(folder, stop):
    """Remove empty folders left by a worktree, up to (not including) `stop`."""
    folder, stop = Path(folder), Path(stop)
    while folder != stop and stop in folder.parents and not any(folder.iterdir()):
        folder.rmdir()
        folder = folder.parent


def remove(branch, yes=False, discard=False, code=HERE):
    top, main_top, _, _ = checkout_info(code)
    root = data_root(code)
    code_wt = code_worktree(main_top, branch)
    data_wt = root / WORKTREES / branch
    default_parent = main_top.parent / f"{main_top.name}.worktrees"
    if code_wt is not None and top == code_wt:
        raise Stop("run remove from the main checkout, not from the worktree it removes")
    plan, problems = [], []
    for repo, wt in ((main_top, code_wt), (root, data_wt if is_checkout(data_wt) else None)):
        if current_branch(repo) == branch:
            raise Stop(f"the main checkout {repo} is on {branch}; nothing removed")
        has_branch = branch_exists(repo, branch)
        if wt is not None and dirty(wt):
            problems.append(f"{wt} has uncommitted changes")
        if has_branch and git(repo, "merge-base", "--is-ancestor", branch, "HEAD",
                              check=False).returncode != 0:
            problems.append(f"branch {branch} in {repo} is not merged")
        if wt is not None or has_branch:
            plan.append((repo, wt, has_branch))
    if not plan:
        raise Stop(f"nothing named {branch} to remove")
    if problems and not discard:
        raise Stop("; ".join(problems) + ". Nothing removed. Run again with --discard to drop them")
    if not yes:
        if not sys.stdin.isatty():
            raise Stop("confirm with --yes; nothing removed")
        answer = input(f"Remove both worktrees and both branches named {branch}? "
                       f"Type the branch name to confirm: ")
        if answer.strip() != branch:
            raise Stop("not confirmed; nothing removed")
    for repo, wt, has_branch in plan:
        if wt is not None:
            git(repo, "worktree", "remove", *(["--force"] if discard else []), str(wt))
            if repo == root:
                prune_empty(wt.parent, root)
            elif default_parent in wt.parents:  # only the default code worktree folder
                prune_empty(wt.parent, default_parent.parent)
        if has_branch:
            git(repo, "branch", "-D" if discard else "-d", branch)
    print(f"removed {branch} from {main_top} and {root}")


def main(argv=None):
    p = argparse.ArgumentParser(description="ai-system data root helper (see _core/CONVENTIONS.md, Data root)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("resolve", help="print the data checkout this ai-system checkout uses")
    sub.add_parser("checkout", help="print the top folder of the ai-system checkout this script is in")
    sub.add_parser("init", help="create and seed the data root when missing (setup)")
    c = sub.add_parser("commit", help="commit in the data checkout, serialized")
    c.add_argument("-m", "--message", required=True)
    c.add_argument("paths", nargs="*", help="paths inside the data checkout (default: every change)")
    a = sub.add_parser("add", help="pair an ai-system worktree with a data worktree")
    a.add_argument("branch")
    a.add_argument("--code-path", help="where the ai-system worktree goes "
                   "(default: <checkout>.worktrees/<branch> next to the main checkout)")
    a.add_argument("--from", dest="start", help="start the code branch here, e.g. origin/my-changes "
                   "(default: the main checkout's HEAD); the data branch starts at the data HEAD")
    m = sub.add_parser("merge", help="merge data, then code, into the main checkouts")
    m.add_argument("branch")
    r = sub.add_parser("remove", help="remove both worktrees and both branches")
    r.add_argument("branch")
    r.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    r.add_argument("--discard", action="store_true", help="also drop uncommitted or unmerged work")
    args = p.parse_args(argv)
    try:
        if args.cmd == "resolve":
            print(resolve())
        elif args.cmd == "checkout":
            print(checkout_info()[0])
        elif args.cmd == "init":
            init()
        elif args.cmd == "commit":
            sha = commit(resolve(), args.message, args.paths)
            print(sha or "nothing to commit")
        elif args.cmd == "add":
            add(args.branch, args.code_path, start=args.start)
        elif args.cmd == "merge":
            merge(args.branch)
        elif args.cmd == "remove":
            remove(args.branch, args.yes, args.discard)
    except Stop as e:
        print(f"data-root: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
