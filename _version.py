
# Machine Generated - do not edit!
#
# Update by running:  python version.py update --version MAJOR.MINOR.PATCH
# from the project root.  Configuration lives in version.yaml.

def get_versions():
    return tag_version_data(raw_versions(), """version.yaml""")

def raw_versions():
    return json.loads("""
{
    "version": "0.33.1"
}
""")

import json
import os
import subprocess

try:
    # Locate the git repo that contains this file.
    MY_DIR = os.path.dirname(os.path.abspath(__file__))
except Exception:
    MY_DIR = None

def is_tree_dirty():
    try:
        return bool(subprocess.check_output(
            ["git", "diff", "--name-only"], stderr=subprocess.PIPE,
            cwd=MY_DIR,
        ).splitlines())
    except (OSError, subprocess.CalledProcessError):
        return False

def get_version_file_path(version_file="version.yaml"):
    try:
        return os.path.join(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.PIPE,
            cwd=MY_DIR,
        ).decode("utf-8").strip(), version_file)
    except (OSError, subprocess.CalledProcessError):
        return None

def number_of_commit_since(version_file="version.yaml"):
    """Number of commits on HEAD since version.yaml was last changed (0 = exact tag)."""
    try:
        last_commit = subprocess.check_output(
            ["git", "log", "--no-merges", "-n", "1", "--pretty=format:%H",
             version_file], cwd=MY_DIR, stderr=subprocess.PIPE,
        ).strip()
        all_commits = subprocess.check_output(
            ["git", "log", "--no-merges", "-n", "1000", "--pretty=format:%H"],
            stderr=subprocess.PIPE, cwd=MY_DIR,
        ).splitlines()
        return all_commits.index(last_commit)
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None

def get_current_git_hash():
    try:
        return subprocess.check_output(
            ["git", "log", "--no-merges", "-n", "1", "--pretty=format:%H"],
            stderr=subprocess.PIPE, cwd=MY_DIR,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None

def tag_version_data(version_data, version_path="version.yaml"):
    """Augment version_data with 'semver' and 'pep440' strings.

    Format:  MAJOR.MINOR.PATCH+COMMITS.SHORTHASH[.dirty]
    """
    current_hash = get_current_git_hash()

    if current_hash is None:
        version_data["error"] = "Not in a git repository."
        version_data["semver"] = version_data["version"] + "+unknown"
        version_data["pep440"] = version_data["semver"]
        return version_data

    if isinstance(current_hash, bytes):
        current_hash = current_hash.decode("utf-8")

    short_hash = current_hash[:7]
    dirty = is_tree_dirty()
    commits = number_of_commit_since(get_version_file_path(version_path))

    version_data["revisionid"] = current_hash
    version_data["dirty"] = dirty
    version_data["dev"] = commits  # kept for backward compatibility

    meta_parts = []
    if commits is not None:
        meta_parts.append(str(commits))
    meta_parts.append(short_hash)
    if dirty:
        meta_parts.append("dirty")

    version_data["semver"] = version_data["version"] + "+" + ".".join(meta_parts)
    version_data["pep440"] = version_data["semver"]

    return version_data
