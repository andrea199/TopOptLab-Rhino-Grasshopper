# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that a clone/export contains the complete source and teaching assets.

Only the Python standard library is required. --tracked additionally audits the
Git file list; omit it when checking an extracted source archive without .git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def check_manifest(base, manifest_file):
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    for name, digest in manifest.items():
        path = base / name
        if not path.is_file():
            raise ValueError(f"Missing manifest file: {path.relative_to(ROOT)}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Checksum mismatch: {path.relative_to(ROOT)}")
    return {p.relative_to(ROOT).as_posix() for p in (base / n for n in manifest)}


def check_archive(path):
    tree = ET.parse(path)
    ids = [i.text for i in tree.iter("item") if i.get("name") == "InstanceGuid"]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError(f"Missing/duplicate object identities: {path.name}")
    sources = [i.text for i in tree.iter("item") if i.get("name") == "Source"]
    if not set(sources) <= set(ids):
        raise ValueError(f"Unresolved source wire: {path.name}")
    if not path.with_suffix(".gh").is_file():
        raise ValueError(f"Missing binary GH counterpart: {path.name}")


def check_links():
    guides = [
        ROOT / "README.md", ROOT / "CONTRIBUTING.md",
        ROOT / "docs/README.md", ROOT / "docs/INSTALLATION.md",
        ROOT / "docs/QUICKSTART.md", ROOT / "docs/ARCHITECTURE.md",
        ROOT / "docs/EXAMPLES.md", ROOT / "teaching/README.md",
        *sorted((ROOT / "teaching/roof_2d").glob("*.md")),
    ]
    for guide in guides:
        text = re.sub(chr(96)*3 + r".*?" + chr(96)*3, "", guide.read_text(encoding="utf-8"), flags=re.S)
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = unquote(target.split("#")[0].strip("<>"))
            if target and not (guide.parent / target).exists():
                raise ValueError(f"Broken link in {guide.relative_to(ROOT)}: {target}")
    return len(guides)


def check_tracked(required):
    names = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode("utf-8").split("\0")
    tracked = {n for n in names if n}
    missing = required - tracked
    if missing:
        raise ValueError("Manifest files not tracked: " + ", ".join(sorted(missing)))
    forbidden_dirs = {".venv", "build", "__pycache__", ".pytest_cache", "node_modules", "dist"}
    token = re.compile(
        rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|"
        rb"AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)"
    )
    forbidden_ext = {".gha", ".dll", ".exe", ".pem", ".key", ".pfx", ".pyc"}
    total = 0
    for name in sorted(tracked):
        path = Path(name)
        if (set(path.parts) & forbidden_dirs or any(p.startswith(".chart-data-") for p in path.parts)
                or path.name == "local-settings.json" or path.name == ".env"
                or (path.name.startswith(".env.") and path.name != ".env.example")
                or path.suffix.lower() in forbidden_ext):
            raise ValueError("Local/generated/sensitive file tracked: " + name)
        data = (ROOT / path).read_bytes()
        total += len(data)
        if len(data) >= 50 * 1024**2:
            raise ValueError("Oversized repository file: " + name)
        if token.search(data):
            raise ValueError("Possible credential/private key in: " + name)
    print(f"Tracked source: {len(tracked)} files, {total / 1024**2:.2f} MiB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracked", action="store_true")
    args = parser.parse_args()
    upstream = check_manifest(ROOT / "vendor/topoptlab", ROOT / "vendor/upstream-sha256.json")
    course_root = ROOT / "teaching/roof_2d/output"
    course = check_manifest(course_root, course_root / "MANIFEST_SHA256.json")
    examples = sorted((ROOT / "tool/examples").glob("*.ghx"))
    assert len(examples) == 20, "Update the gallery and integrity check when adding examples"
    examples.append(course_root / "case/roof_2d_classroom.ghx")
    for path in examples:
        check_archive(path)
    with zipfile.ZipFile(course_root / "Centina_tetto_2D_lezione_v3.pptx") as deck:
        assert deck.testzip() is None, "Corrupt PowerPoint package"
        names = deck.namelist()
        assert len([n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]) == 40
        assert len([n for n in names if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n)]) == 40
    guide_count = check_links()
    if args.tracked:
        check_tracked(upstream | course)
    print(f"OK: {len(upstream)} upstream files; {len(course)} course files; "
          f"{len(examples)} GH/GHX pairs; 40 slides/notes; {guide_count} linked guides")


if __name__ == "__main__":
    main()
