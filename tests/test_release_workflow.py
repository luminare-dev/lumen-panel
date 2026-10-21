"""Tests for the publish job in .github/workflows/reusable-release.yml (needs bash).

The job's shell steps run here with a stand-in `gh` that records its arguments, so the file names,
the files handed to `gh release upload` and the order (verify, attach, then publish) are checked
without GitHub. Published releases are immutable: a file that is not attached before the draft is
published can never be added.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "reusable-release.yml"
REPO = "luminare-dev/lumen-panel"
ARCHIVE = "lumen-panel-0.1.0.tar.gz"

ATTEST = "Attest build provenance"
PROVENANCE = "Add the provenance file and verify it"
PUBLISH = "Attach the files and publish the release"


def publish_steps() -> list[dict[str, str]]:
    """The publish job's steps as flat {key: value}: "name", "if", "env.BUNDLE", "with.subject-path"
    and so on, and "run" with the step's script (the subset of YAML this workflow uses)."""
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = lines.index("  publish:")
    steps: list[dict[str, str]] = []
    in_run = False
    parent = ""
    for line in lines[start + 1:]:
        indent = len(line) - len(line.lstrip(" "))
        if line.strip() and indent < 4:  # the next job or top-level key
            break
        if in_run and (not line.strip() or indent > 8):
            steps[-1]["run"] += line[10:] + "\n"
            continue
        in_run = False
        if line.startswith("      - "):
            steps.append({})
            line, indent = "        " + line[8:], 8
        if not steps or indent not in (8, 10) or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        if indent == 8:
            parent = key
        else:
            key = f"{parent}.{key}"
        steps[-1][key] = value
        if key == "run" and value == "|":
            steps[-1]["run"], in_run = "", True
    return steps


def step(name: str) -> dict[str, str]:
    return next(s for s in publish_steps() if s.get("name") == name)


class ReleaseRun:
    """A scratch dist/ folder and a stand-in gh, for running the job's scripts with bash."""

    def __init__(self, archives: tuple[str, ...] = (ARCHIVE,), fail: str = "") -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="release-test-"))
        unittest.addModuleCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        (self.dir / "dist").mkdir()
        for name in archives:
            (self.dir / "dist" / name).write_bytes(b"archive " + name.encode())
        (self.dir / "dist" / "SHA256SUMS").write_text("checksums\n", encoding="utf-8")
        self.bundle = self.dir / "attestation.json"
        self.bundle.write_text('{"mediaType":"application/vnd.dev.sigstore.bundle.v0.3+json"}\n', encoding="utf-8")
        self.log = self.dir / "gh.log"
        bin_dir = self.dir / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text(textwrap.dedent(f"""\
            #!{sys.executable}
            import json, os, sys
            with open(os.environ["GH_LOG"], "a", encoding="utf-8") as fh:
                fh.write(json.dumps(sys.argv[1:]) + "\\n")
            sys.exit(1 if sys.argv[1:2] == [os.environ.get("GH_FAIL")] else 0)
            """), encoding="utf-8")
        gh.chmod(0o755)
        self.env = {"PATH": f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin", "HOME": str(self.dir), "LC_ALL": "C",
                    "GH_LOG": str(self.log), "GH_FAIL": fail, "GH_TOKEN": "unused", "GITHUB_REPOSITORY": REPO,
                    "BUNDLE": str(self.bundle), "DEFAULT_BRANCH": "main", "TAG": "v0.1.0"}

    def run(self, name: str) -> subprocess.CompletedProcess[str]:
        script = self.dir / "step.sh"
        script.write_text(step(name)["run"], encoding="utf-8")
        # The shell GitHub Actions uses for "run:" steps on Linux.
        return subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)], cwd=self.dir,
                              env=self.env, capture_output=True, text=True, timeout=60)

    def gh_calls(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]


class StepOrderTest(unittest.TestCase):
    def test_the_provenance_file_is_added_after_the_attestation_and_before_publishing(self):
        names = [s.get("name") for s in publish_steps()]
        self.assertLess(names.index(ATTEST), names.index(PROVENANCE))
        self.assertLess(names.index(PROVENANCE), names.index(PUBLISH))
        self.assertEqual(names[-1], PUBLISH)

    def test_the_provenance_step_runs_exactly_when_the_attestation_was_made(self):
        """In a private repository the attest step is skipped, and so is this step."""
        self.assertEqual(step(ATTEST).get("id"), "attest")
        self.assertEqual(step(PROVENANCE).get("if"), "${{ steps.attest.outcome == 'success' }}")
        self.assertEqual(step(PROVENANCE).get("env.BUNDLE"), "${{ steps.attest.outputs.bundle-path }}")
        self.assertEqual(step(PROVENANCE).get("env.DEFAULT_BRANCH"), "${{ github.event.repository.default_branch }}")


class PublishJobTest(unittest.TestCase):
    def test_bundle_is_verified_attached_and_then_the_release_published(self):
        rel = ReleaseRun()
        out = rel.run(PROVENANCE)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        provenance = rel.dir / "dist" / f"{ARCHIVE}.intoto.jsonl"
        self.assertEqual(provenance.read_bytes(), rel.bundle.read_bytes())
        # The signer is this workflow file (a reusable workflow signs with its own path), run from main.
        self.assertEqual(rel.gh_calls(), [["attestation", "verify", f"dist/{ARCHIVE}", "--repo", REPO,
                                           "--signer-workflow", f"{REPO}/.github/workflows/{WORKFLOW.name}",
                                           "--source-ref", "refs/heads/main",
                                           "--bundle", f"dist/{ARCHIVE}.intoto.jsonl"]])

        out = rel.run(PUBLISH)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        upload, publish = rel.gh_calls()[1:]
        self.assertEqual(upload[:3], ["release", "upload", "v0.1.0"])
        self.assertEqual(sorted(a for a in upload if a.startswith("dist/")),
                         ["dist/SHA256SUMS", f"dist/{ARCHIVE}", f"dist/{ARCHIVE}.intoto.jsonl"])
        self.assertEqual(publish, ["release", "edit", "v0.1.0", "--draft=false", "--repo", REPO])

    def test_failed_verification_stops_the_job_before_publishing(self):
        rel = ReleaseRun(fail="attestation")
        out = rel.run(PROVENANCE)
        self.assertNotEqual(out.returncode, 0)
        self.assertEqual([c[:2] for c in rel.gh_calls()], [["attestation", "verify"]])

    def test_needs_exactly_one_archive(self):
        for archives in ((), (ARCHIVE, "lumen-panel-0.1.1.tar.gz")):
            with self.subTest(archives=archives):
                rel = ReleaseRun(archives=archives)
                out = rel.run(PROVENANCE)
                self.assertNotEqual(out.returncode, 0)
                self.assertIn("expected one archive", out.stdout)
                self.assertEqual(rel.gh_calls(), [])
                self.assertEqual(list((rel.dir / "dist").glob("*.intoto.jsonl")), [])

    def test_without_an_attestation_the_archive_and_checksums_are_still_published(self):
        """Private repository: the provenance step is skipped, the upload takes what is there."""
        rel = ReleaseRun()
        out = rel.run(PUBLISH)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        upload, publish = rel.gh_calls()
        self.assertEqual(sorted(a for a in upload if a.startswith("dist/")), ["dist/SHA256SUMS", f"dist/{ARCHIVE}"])
        self.assertEqual(publish[:4], ["release", "edit", "v0.1.0", "--draft=false"])


if __name__ == "__main__":
    unittest.main()
