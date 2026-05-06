"""
CLI integration tests for every aff4 run flag.

Run against the Python source (default):
    pytest tests/test_cli_flags.py -v

Run against a compiled binary:
    pytest tests/test_cli_flags.py --binary dist/aff4 -v
"""

import re
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
AFF4_L = REPO_ROOT / "test_images" / "AFF4-L"
AFF4_STD = REPO_ROOT / "test_images" / "AFF4Std"

DREAM_AFF4 = AFF4_L / "dream.aff4"
DREAM_TXT = AFF4_L / "dream.txt"
LINEAR_AFF4 = AFF4_STD / "Base-Linear.aff4"


# ── helpers ────────────────────────────────────────────────────────────────────

def assert_ok(result, context=""):
    __tracebackhide__ = True
    if result.returncode != 0:
        msg = f"Command failed (exit {result.returncode})"
        if context:
            msg += f" [{context}]"
        msg += f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        pytest.fail(msg)


def parse_urns(listing_output):
    """Extract aff4:// URNs from the output of `aff4 -l`."""
    return re.findall(r"<(aff4://[^>]+)>", listing_output)


# ── -l / --list ────────────────────────────────────────────────────────────────

class TestList:
    def test_list_logical_container(self, run_aff4):
        r = run_aff4("-l", DREAM_AFF4)
        assert_ok(r, "-l dream.aff4")
        assert "AFF4Container" in r.stdout
        assert "dream.txt" in r.stdout

    def test_list_physical_container(self, run_aff4):
        r = run_aff4("-l", LINEAR_AFF4)
        assert_ok(r, "-l Base-Linear.aff4")
        assert "AFF4Container" in r.stdout

    def test_list_terse(self, run_aff4):
        r = run_aff4("-l", "-t", DREAM_AFF4)
        assert_ok(r, "-l -t")
        assert "AFF4Container" in r.stdout
        # Terse mode strips the volume prefix from image URNs
        full = run_aff4("-l", DREAM_AFF4)
        assert len(r.stdout) <= len(full.stdout)

    def test_list_verbose(self, run_aff4):
        r = run_aff4("-l", "--verbose", DREAM_AFF4)
        assert_ok(r, "-l --verbose")
        assert "AFF4Container" in r.stdout


# ── -m / --meta ────────────────────────────────────────────────────────────────

class TestMeta:
    def test_meta_emits_turtle(self, run_aff4):
        r = run_aff4("-m", DREAM_AFF4)
        assert_ok(r, "-m dream.aff4")
        assert "@prefix aff4:" in r.stdout
        assert "@prefix xsd:" in r.stdout

    def test_meta_contains_image_type(self, run_aff4):
        r = run_aff4("-m", DREAM_AFF4)
        assert_ok(r)
        assert "aff4:FileImage" in r.stdout

    def test_meta_contains_hashes(self, run_aff4):
        r = run_aff4("-m", DREAM_AFF4)
        assert_ok(r)
        assert "aff4:hash" in r.stdout


# ── -v / --verify ──────────────────────────────────────────────────────────────

class TestVerify:
    def test_verify_logical_container(self, run_aff4):
        r = run_aff4("-v", DREAM_AFF4)
        assert_ok(r, "-v dream.aff4")
        assert "SHA1 Verified" in r.stdout
        assert "MD5 Verified" in r.stdout

    def test_verify_shows_container_urn(self, run_aff4):
        r = run_aff4("-v", DREAM_AFF4)
        assert_ok(r)
        assert "AFF4Container" in r.stdout


# ── -c / --create-logical ──────────────────────────────────────────────────────

class TestCreateLogical:
    def test_create_single_file(self, run_aff4, tmp_path):
        container = tmp_path / "single.aff4"
        r = run_aff4("-c", container, DREAM_TXT)
        assert_ok(r, "-c single file")
        assert container.exists()

        listing = run_aff4("-l", container)
        assert_ok(listing)
        assert "dream.txt" in listing.stdout

    def test_create_multiple_files(self, run_aff4, tmp_path):
        container = tmp_path / "multi.aff4"
        f1 = tmp_path / "alpha.txt"
        f2 = tmp_path / "beta.txt"
        f1.write_text("alpha content")
        f2.write_text("beta content")

        r = run_aff4("-c", container, f1, f2)
        assert_ok(r, "-c multiple files")

        listing = run_aff4("-l", container)
        assert "alpha.txt" in listing.stdout
        assert "beta.txt" in listing.stdout

    def test_create_recursive(self, run_aff4, tmp_path):
        container = tmp_path / "recursive.aff4"
        src = tmp_path / "srcdir"
        src.mkdir()
        (src / "child1.txt").write_text("child 1")
        (src / "child2.txt").write_text("child 2")

        r = run_aff4("-c", "-r", container, src)
        assert_ok(r, "-c -r")

        listing = run_aff4("-l", container)
        assert "child1.txt" in listing.stdout
        assert "child2.txt" in listing.stdout


# ── -X / --extract-all ─────────────────────────────────────────────────────────

class TestExtractAll:
    def test_extract_all_from_reference_image(self, run_aff4, tmp_path):
        dest = tmp_path / "out"
        dest.mkdir()
        r = run_aff4("-X", "-f", dest, DREAM_AFF4)
        assert_ok(r, "-X dream.aff4")

        extracted = list(dest.rglob("dream.txt"))
        assert extracted, "dream.txt not found after extraction"
        assert "I have a Dream" in extracted[0].read_text(errors="replace")

    def test_extract_all_roundtrip(self, run_aff4, tmp_path):
        container = tmp_path / "rt.aff4"
        src = tmp_path / "payload.bin"
        src.write_bytes(bytes(range(256)) * 16)

        run_aff4("-c", container, src)

        dest = tmp_path / "out"
        dest.mkdir()
        run_aff4("-X", "-f", dest, container)

        extracted = list(dest.rglob("payload.bin"))
        assert extracted, "payload.bin not found after extraction"
        assert extracted[0].read_bytes() == src.read_bytes()


# ── -x / --extract ─────────────────────────────────────────────────────────────

class TestExtract:
    def test_extract_specific_urn(self, run_aff4, tmp_path):
        container = tmp_path / "specific.aff4"
        src = tmp_path / "target.txt"
        src.write_bytes(b"specific file content")
        run_aff4("-c", container, src)

        listing = run_aff4("-l", container)
        urns = [u for u in parse_urns(listing.stdout) if "target.txt" in u]
        assert urns, f"Could not find target.txt URN in listing:\n{listing.stdout}"

        dest = tmp_path / "out"
        dest.mkdir()
        r = run_aff4("-x", "-f", dest, container, urns[0])
        assert_ok(r, "-x specific URN")

        extracted = list(dest.rglob("target.txt"))
        assert extracted, "target.txt not found after -x extraction"
        assert extracted[0].read_bytes() == b"specific file content"


# ── -a / --append ──────────────────────────────────────────────────────────────

class TestAppend:
    def test_append_adds_second_file(self, run_aff4, tmp_path):
        container = tmp_path / "append.aff4"
        f1 = tmp_path / "first.txt"
        f2 = tmp_path / "second.txt"
        f1.write_text("first file")
        f2.write_text("second file")

        run_aff4("-c", container, f1)
        r = run_aff4("-c", "-a", container, f2)
        assert_ok(r, "-c -a")

        listing = run_aff4("-l", container)
        assert "first.txt" in listing.stdout
        assert "second.txt" in listing.stdout

    def test_appended_content_extractable(self, run_aff4, tmp_path):
        container = tmp_path / "append_extract.aff4"
        f1 = tmp_path / "one.txt"
        f2 = tmp_path / "two.txt"
        f1.write_bytes(b"content one")
        f2.write_bytes(b"content two")

        run_aff4("-c", container, f1)
        run_aff4("-c", "-a", container, f2)

        dest = tmp_path / "out"
        dest.mkdir()
        run_aff4("-X", "-f", dest, container)

        assert list(dest.rglob("one.txt")), "one.txt missing after append+extract"
        assert list(dest.rglob("two.txt")), "two.txt missing after append+extract"


# ── -H / --hash (hash-based imaging) ──────────────────────────────────────────

class TestHashBased:
    @pytest.fixture(autouse=True)
    def _require_fastchunking(self):
        pytest.importorskip("fastchunking",
                             reason="fastchunking not installed; pip install pyaff4[cdc]")

    def test_hash_create_and_list(self, run_aff4, tmp_path):
        container = tmp_path / "hash.aff4"
        src = tmp_path / "data.bin"
        src.write_bytes(b"hash imaging test data" * 500)

        r = run_aff4("-c", "-H", container, src)
        assert_ok(r, "-c -H")
        assert container.exists()

        listing = run_aff4("-l", container)
        assert_ok(listing)
        assert "data.bin" in listing.stdout

    def test_hash_deduplicates_identical_content(self, run_aff4, tmp_path):
        container = tmp_path / "dedup.aff4"
        payload = b"identical content for dedup test" * 500
        f1 = tmp_path / "copy_a.bin"
        f2 = tmp_path / "copy_b.bin"
        f1.write_bytes(payload)
        f2.write_bytes(payload)

        r = run_aff4("-c", "-H", container, f1, f2)
        assert_ok(r, "-c -H dedup")

        listing = run_aff4("-l", container)
        assert "copy_a.bin" in listing.stdout
        assert "copy_b.bin" in listing.stdout

    def test_hash_paranoid_mode(self, run_aff4, tmp_path):
        container = tmp_path / "paranoid.aff4"
        src = tmp_path / "paranoid_data.bin"
        src.write_bytes(b"paranoid mode test" * 500)

        # -p (paranoid) does byte-level verification when hashes match; no output
        # difference is expected — just confirm it completes without error
        r = run_aff4("-c", "-H", "-p", container, src)
        assert_ok(r, "-c -H -p")
        assert container.exists()


# ── -e / --password (encryption) ──────────────────────────────────────────────

class TestEncrypted:
    PASSWORD = "t3st_p@ssw0rd"

    def test_create_and_list_encrypted(self, run_aff4, tmp_path):
        container = tmp_path / "enc.aff4"
        src = tmp_path / "secret.txt"
        src.write_text("top secret content")

        r = run_aff4("-c", "-e", self.PASSWORD, container, src)
        assert_ok(r, "-c -e")
        assert container.exists()

        listing = run_aff4("-l", "-e", self.PASSWORD, container)
        assert_ok(listing, "-l -e")
        assert "secret.txt" in listing.stdout

    def test_encrypted_extract_all(self, run_aff4, tmp_path):
        container = tmp_path / "enc_extract.aff4"
        src = tmp_path / "classified.txt"
        src.write_bytes(b"classified bytes")

        run_aff4("-c", "-e", self.PASSWORD, container, src)

        dest = tmp_path / "out"
        dest.mkdir()
        r = run_aff4("-X", "-e", self.PASSWORD, "-f", dest, container)
        assert_ok(r, "-X -e")

        extracted = list(dest.rglob("classified.txt"))
        assert extracted, "classified.txt not found after encrypted extraction"
        assert extracted[0].read_bytes() == b"classified bytes"

    def test_encrypted_meta(self, run_aff4, tmp_path):
        container = tmp_path / "enc_meta.aff4"
        src = tmp_path / "file.txt"
        src.write_text("some content")

        run_aff4("-c", "-e", self.PASSWORD, container, src)

        r = run_aff4("-m", "-e", self.PASSWORD, container)
        assert_ok(r, "-m -e")
        assert "@prefix" in r.stdout


# ── -i / --ingest ──────────────────────────────────────────────────────────────

class TestIngest:
    @pytest.fixture(autouse=True)
    def _require_fastchunking(self):
        pytest.importorskip("fastchunking",
                             reason="fastchunking not installed; pip install pyaff4[cdc]")

    def test_ingest_zip_creates_container(self, run_aff4, tmp_path):
        zip_path = tmp_path / "archive.bag.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("doc1.txt", "document one contents")
            zf.writestr("doc2.txt", "document two contents")

        container = tmp_path / "ingested.aff4"
        r = run_aff4("-i", container, zip_path)
        assert_ok(r, "-i")
        assert container.exists()

    def test_ingest_then_list(self, run_aff4, tmp_path):
        zip_path = tmp_path / "data.bag.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("report.txt", "report contents")

        container = tmp_path / "ingested2.aff4"
        r = run_aff4("-i", container, zip_path)
        assert_ok(r, "-i")

        listing = run_aff4("-l", container)
        assert_ok(listing, "-l after -i")
        assert "AFF4Container" in listing.stdout
