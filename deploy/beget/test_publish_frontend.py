import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import publish_frontend as publisher


class PublishFrontendTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "initial").mkdir()
        (self.root / "initial/index.html").write_text("previous version")
        (self.root / "current").symlink_to("initial")

    def upload(self, paths, digest=None):
        packet = io.BytesIO()
        with tarfile.open(fileobj=packet, mode="w:gz") as archive:
            for path in paths:
                contents = b"page"
                entry = tarfile.TarInfo(path)
                entry.size = len(contents)
                archive.addfile(entry, io.BytesIO(contents))
        data = packet.getvalue()
        with patch("publish_frontend.sys.stdin") as stdin:
            stdin.buffer = io.BytesIO(data)
            publisher.publish(self.root, "a" * 40, digest or hashlib.sha256(data).hexdigest())

    @patch("publish_frontend.smoke")
    def test_publishes_checked_release(self, smoke):
        self.upload(["index.html", "project/index.html"])
        smoke.assert_called_once_with("a" * 40)
        self.assertEqual((self.root / "current/__release.txt").read_text().strip(), "a" * 40)

    def test_invalid_upload_keeps_previous_release(self):
        for paths, digest in [
            (["index.html", "project/index.html", "../escape"], None),
            (["index.html", "project/index.html"], "0" * 64),
        ]:
            with self.subTest(paths=paths, digest=digest):
                with self.assertRaises(ValueError):
                    self.upload(paths, digest)
                self.assertEqual((self.root / "current").readlink(), Path("initial"))

    @patch("publish_frontend.smoke", side_effect=RuntimeError("health check"))
    def test_restores_previous_release(self, _smoke):
        with self.assertRaises(RuntimeError):
            self.upload(["index.html", "project/index.html"])
        self.assertEqual((self.root / "current").readlink(), Path("initial"))


if __name__ == "__main__":
    unittest.main()
