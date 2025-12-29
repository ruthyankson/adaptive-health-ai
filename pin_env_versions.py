#!/usr/bin/env python3
"""
Pin package versions in an environment.yml using installed versions from a conda environment.

What it does:
1) Reads an input environment.yml
2) Pins conda dependencies to the exact versions installed in a specified conda env
3) Optionally pins pip dependencies inside any `pip:` subsection using `pip freeze`
4) Writes the pinned environment file (or updates the input in-place)
5) Optionally runs conda-lock to generate an explicit linux-64 lock file from the pinned env

Examples:
  # Write pinned file
  python pin_env_versions.py -i environment.yml -o environment.pinned.yml -n health-ai

  # Pin pip deps as well
  python pin_env_versions.py -i environment.yml -o environment.pinned.yml -n health-ai --pin-pip

  # Pin + generate linux-64 explicit lock file
  python pin_env_versions.py -i environment.yml -o environment.pinned.yml -n health-ai \
    --pin-pip --lock-linux64 --lock-output conda-linux-64.lock

  # Update environment.yml in-place and then lock
  python pin_env_versions.py -i environment.yml -n health-ai --inplace \
    --pin-pip --lock-linux64 --lock-output conda-linux-64.lock
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # PyYAML
except ImportError:
    print("Missing dependency: PyYAML. Install with: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)


# def run(cmd: list[str]) -> str:
#     """Run a command and return stdout. Raise on non-zero exit."""
#     proc = subprocess.run(cmd, capture_output=True, text=True)
#     if proc.returncode != 0:
#         raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
#     return proc.stdout

def _resolve_conda_exe() -> str:
    """
    Resolve a runnable conda executable on Windows/Miniforge setups.

    Preference order:
    1) CONDA_EXE environment variable (set by conda shells)
    2) PATH lookup for conda/conda.bat/conda.exe
    3) Common Miniforge/Conda locations relative to sys.prefix
    """
    conda_exe = os.environ.get("CONDA_EXE")
    if conda_exe and Path(conda_exe).exists():
        return conda_exe

    for candidate in ("conda", "conda.exe", "conda.bat"):
        found = shutil.which(candidate)
        if found:
            return found

    # Fallback guesses (sys.prefix is the python env path)
    candidates = [
        Path(sys.prefix).parent / "condabin" / "conda.bat",
        Path(sys.prefix).parent / "condabin" / "conda.exe",
        Path(sys.prefix) / "Scripts" / "conda.exe",
        Path(sys.prefix) / "Scripts" / "conda.bat",
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    raise FileNotFoundError(
        "Could not resolve conda executable. Ensure you are running inside a conda "
        "shell (so CONDA_EXE is set) or that conda is on PATH."
    )


def run(cmd: list[str]) -> str:
    """
    Run a command and return stdout.

    Special handling:
    - If the command is `conda ...`, resolve the conda executable path explicitly.
    """
    if cmd and cmd[0] == "conda":
        cmd = [_resolve_conda_exe()] + cmd[1:]

    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout


def load_env_yml(path: Path) -> dict[str, Any]:
    """Load and validate a conda environment YAML file."""
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("environment.yml is not a valid YAML mapping.")
    return data


def conda_list_json(env_name: str) -> list[dict[str, Any]]:
    """Return installed conda packages for an environment via `conda list --json`."""
    out = run(["conda", "list", "-n", env_name, "--json"])
    return json.loads(out)


def pip_freeze(env_name: str) -> dict[str, str]:
    """
    Return pip-installed packages inside the conda env as {normalized_name: version}.

    If pip is not available in the env, returns an empty mapping.
    """
    try:
        out = run(["conda", "run", "-n", env_name, "python", "-m", "pip", "freeze"])
    except Exception:
        return {}

    mapping: dict[str, str] = {}
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Standard form: package==version
        if "==" in line and not line.startswith("-e "):
            name, ver = line.split("==", 1)
            mapping[normalize_name(name)] = ver

        # For URLs/editable installs, we skip (best-effort).
    return mapping


def normalize_name(name: str) -> str:
    """PEP 503-style normalization (lowercase; collapse -_. to -)."""
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def parse_conda_dep(dep: str) -> tuple[str | None, str]:
    """
    Parse a conda dependency string and return (channel_prefix, package_name).

    Examples:
      "numpy" -> (None, "numpy")
      "numpy>=1.26" -> (None, "numpy")
      "conda-forge::numpy" -> ("conda-forge", "numpy")
      "pytorch::torchvision>=0.16" -> ("pytorch", "torchvision")
    """
    dep = dep.strip()

    channel: str | None = None
    if "::" in dep:
        channel, dep = dep.split("::", 1)

    # Extract the leading name token (supports dots, underscores, dashes)
    m = re.match(r"^([A-Za-z0-9_.-]+)", dep)
    if not m:
        return channel, dep

    return channel, m.group(1)


def build_conda_pkg_map(env_name: str) -> dict[str, str]:
    """Map installed conda packages (lowercased name -> version) for the env."""
    pkgs = conda_list_json(env_name)
    return {p["name"].lower(): p["version"] for p in pkgs if "name" in p and "version" in p}


def pin_conda_deps(
    deps: list[Any],
    conda_pkgs: dict[str, str],
    keep_python_unpinned: bool,
) -> list[Any]:
    """
    Pin conda dependencies listed in environment.yml to exact installed versions.

    - Preserves `channel::package` prefix when present
    - Leaves non-string dependency items unchanged (e.g., dict for `pip:`)
    - If a package is not found in conda list, keeps the original entry
    """
    pinned: list[Any] = []

    for item in deps:
        if not isinstance(item, str):
            pinned.append(item)
            continue

        channel, name = parse_conda_dep(item)
        name_lc = name.lower()

        if keep_python_unpinned and name_lc == "python":
            pinned_item = f"{channel}::python" if channel else "python"
            pinned.append(pinned_item)
            continue

        ver = conda_pkgs.get(name_lc)
        if not ver:
            pinned.append(item)
            continue

        pinned_item = f"{name}={ver}"
        if channel:
            pinned_item = f"{channel}::{pinned_item}"

        pinned.append(pinned_item)

    return pinned


def extract_pip_name(spec: str) -> tuple[str, str]:
    """
    Extract a pip package name from a requirement line.

    Returns:
      (base_name_normalized, extras_suffix)

    Examples:
      "uvicorn[standard]" -> ("uvicorn", "[standard]")
      "fastapi" -> ("fastapi", "")
    """
    s = spec.strip()

    m = re.match(r"^([A-Za-z0-9_.-]+)(\[.*\])?$", s)
    if not m:
        # fallback: take token until first non-name char
        m2 = re.match(r"^([A-Za-z0-9_.-]+)", s)
        base = m2.group(1) if m2 else s
        return normalize_name(base), ""

    base = normalize_name(m.group(1))
    extras = m.group(2) or ""
    return base, extras


def pin_pip_deps(pip_list: list[Any], pip_pkgs: dict[str, str]) -> list[Any]:
    """
    Pin pip requirements inside a `pip:` subsection using pip freeze data.

    Rules:
    - If already pinned via '==' or references via '@', leave as-is
    - If freeze version is available, rewrite to 'name[extras]==version'
    - Otherwise keep original entry
    """
    out: list[Any] = []

    for item in pip_list:
        if not isinstance(item, str):
            out.append(item)
            continue

        s = item.strip()
        if "==" in s or "@" in s or s.startswith("-e "):
            out.append(s)
            continue

        base_norm, extras = extract_pip_name(s)
        ver = pip_pkgs.get(base_norm)
        if ver:
            # Keep original base token (including extras) and pin to version
            out.append(f"{s}{'==' if '==' not in s else ''}{ver}" if extras else f"{s}=={ver}")
            # The above line is safe but may duplicate extras handling; simpler below:
            # out.append(f"{base_norm}{extras}=={ver}")  # uses normalized name
        else:
            out.append(s)

    return out


def run_conda_lock_linux64(input_env_yml: Path, lock_output: Path) -> None:
    """
    Generate an explicit linux-64 lock file using conda-lock.

    Requires `conda-lock` installed and available on PATH.
    """
    if not shutil.which("conda-lock"):
        raise RuntimeError("conda-lock not found. Install with: pip install conda-lock")

    # Use the modern subcommand form to ensure consistent output behavior.
    run(
        [
            "conda-lock",
            "lock",
            "--file",
            str(input_env_yml),
            "--platform",
            "linux-64",
            "--kind",
            "explicit",
            "--filename-template",
            str(lock_output),
        ]
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", default="environment.yml", help="Input environment.yml")
    ap.add_argument(
        "-o",
        "--output",
        default="environment.pinned.yml",
        help="Output pinned env yml (ignored with --inplace)",
    )
    ap.add_argument(
        "-n",
        "--env",
        default=None,
        help="Conda environment name (defaults to name in environment.yml)",
    )
    ap.add_argument(
        "--pin-pip",
        action="store_true",
        help="Also pin pip subsection using pip freeze from the env.",
    )
    ap.add_argument(
        "--keep-python-unpinned",
        action="store_true",
        help="Do not pin python version (write python without an exact version).",
    )
    ap.add_argument(
        "--inplace",
        action="store_true",
        help="Overwrite the input environment.yml with pinned versions.",
    )
    ap.add_argument(
        "--lock-linux64",
        action="store_true",
        help="After pinning, generate a linux-64 explicit lock file using conda-lock.",
    )
    ap.add_argument(
        "--lock-output",
        default="conda-linux-64.lock",
        help="Output filename for the linux-64 explicit lock file.",
    )

    args = ap.parse_args()

    in_path = Path(args.input)
    data = load_env_yml(in_path)

    env_name = args.env or data.get("name")
    if not env_name:
        print(
            "Could not determine environment name. Provide --env or ensure 'name:' exists.",
            file=sys.stderr,
        )
        return 2

    deps = data.get("dependencies")
    if not isinstance(deps, list):
        print("environment.yml must contain a top-level 'dependencies:' list.", file=sys.stderr)
        return 2

    conda_pkgs = build_conda_pkg_map(env_name)
    pinned_deps = pin_conda_deps(deps, conda_pkgs, keep_python_unpinned=args.keep_python_unpinned)

    if args.pin_pip:
        pip_pkgs = pip_freeze(env_name)
        updated: list[Any] = []
        for item in pinned_deps:
            if isinstance(item, dict) and "pip" in item and isinstance(item["pip"], list):
                new_item = dict(item)
                new_item["pip"] = pin_pip_deps(item["pip"], pip_pkgs)
                updated.append(new_item)
            else:
                updated.append(item)
        pinned_deps = updated

    out_data = dict(data)
    out_data["dependencies"] = pinned_deps

    out_path = in_path if args.inplace else Path(args.output)
    out_path.write_text(yaml.safe_dump(out_data, sort_keys=False))
    print(f"Wrote pinned environment to: {out_path}")

    if args.lock_linux64:
        lock_output = Path(args.lock_output)
        run_conda_lock_linux64(out_path, lock_output)
        print(f"Wrote linux-64 explicit lock to: {lock_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
