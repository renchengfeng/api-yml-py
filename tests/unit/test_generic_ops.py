"""通用文件 / 序列化 / 集合算子的行为测试。

算子测试套件已经覆盖模板、用例与错误路径；这里补真实文件系统行为，
避免只测到“路径穿越被拒绝”而没有覆盖成功写入。
"""
import base64
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from lowcode.config.models import GroupDef
from lowcode.core import BuildEnv, Context
from lowcode.errors import BizError
from lowcode.operators import create_operator


class GenericOpsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = BuildEnv(None, GroupDef(module="test", group="node", name="test"), "test")

    def tearDown(self):
        self.tmp.cleanup()

    def run_op(self, name, config):
        op = create_operator(name, "n", config, self.env)
        return op.execute(Context({}), op.config)

    def test_file_write_read_copy_delete(self):
        config = {"baseDir": str(self.root), "path": "a/b.txt", "content": "hello"}
        written = self.run_op("fileWrite", config)
        self.assertEqual(written["bytes"], 5)
        self.assertTrue((self.root / "a" / "b.txt").is_file())

        read = self.run_op("fileRead", {"baseDir": str(self.root), "path": "a/b.txt"})
        self.assertEqual(read["content"], "hello")
        self.assertEqual(read["rev"], written["rev"])

        copied = self.run_op("fileCopy", {"baseDir": str(self.root), "from": "a/b.txt", "to": "c.txt"})
        self.assertEqual(copied["bytes"], 5)
        self.assertTrue((self.root / "c.txt").is_file())

        deleted = self.run_op("fileDelete", {"baseDir": str(self.root), "path": "c.txt"})
        self.assertTrue(deleted["deleted"])
        self.assertFalse((self.root / "c.txt").exists())

    def test_file_write_rev_conflict(self):
        first = self.run_op("fileWrite", {"baseDir": str(self.root), "path": "x.txt", "content": "a"})
        with self.assertRaises(BizError) as ctx:
            self.run_op("fileWrite", {
                "baseDir": str(self.root), "path": "x.txt", "content": "b",
                "expectedRev": "not-the-current-rev",
            })
        self.assertEqual(ctx.exception.status, 409)
        self.assertEqual((self.root / "x.txt").read_text(encoding="utf-8"), "a")
        self.assertEqual(first["rev"], self.run_op("fileRead", {"baseDir": str(self.root), "path": "x.txt"})["rev"])

    def test_file_path_escape_is_rejected(self):
        with self.assertRaises(BizError) as ctx:
            self.run_op("fileRead", {"baseDir": str(self.root), "path": "../outside.txt"})
        self.assertEqual(ctx.exception.status, 403)

    def test_file_read_many(self):
        (self.root / "a.yaml").write_text("id: a\n", encoding="utf-8")
        (self.root / "b.yaml").write_text("id: b\n", encoding="utf-8")
        result = self.run_op("fileReadMany", {
            "baseDir": str(self.root), "suffix": ".yaml", "format": "yaml",
        })
        self.assertEqual(result["count"], 2)
        self.assertEqual([x["data"]["id"] for x in result["items"]], ["a", "b"])

    def test_yaml_and_frontmatter(self):
        parsed = self.run_op("yamlParse", {"content": "a: 1\n"})
        self.assertEqual(parsed, {"a": 1})
        text = self.run_op("yamlStringify", {"data": {"a": 1}})
        self.assertEqual(text, "a: 1\n")
        fm = self.run_op("frontmatterParse", {"content": "---\nname: demo\n---\nbody\n"})
        self.assertEqual(fm["meta"], {"name": "demo"})
        self.assertEqual(fm["body"], "body\n")

    def test_file_copy_tree_base64_and_diff(self):
        src = self.root / "src"
        src.mkdir()
        (src / "a.txt").write_text("a", encoding="utf-8")
        (src / "sub").mkdir()
        (src / "sub" / "b.txt").write_text("b", encoding="utf-8")
        copied = self.run_op("fileCopyTree", {"baseDir": str(self.root), "from": "src", "to": "dst"})
        self.assertEqual(copied["count"], 2)
        self.assertEqual((self.root / "dst" / "sub" / "b.txt").read_text(encoding="utf-8"), "b")

        written = self.run_op("fileWriteBase64", {
            "baseDir": str(self.root), "path": "bin/a.bin", "contentBase64": "aGVsbG8=",
        })
        self.assertEqual(written["bytes"], 5)
        self.assertEqual((self.root / "bin" / "a.bin").read_bytes(), b"hello")
        diff = self.run_op("textDiff", {"left": "a\n", "right": "b\n"})
        self.assertIn("+b", diff)

    def test_file_write_many_and_swap(self):
        result = self.run_op("fileWriteMany", {
            "baseDir": str(self.root),
            "files": [{"path": "m/a.txt", "content": "a"}, {"path": "m/b.txt", "content": "b"}],
        })
        self.assertEqual(result["count"], 2)
        self.assertEqual((self.root / "m" / "b.txt").read_text(encoding="utf-8"), "b")

        src = self.root / "swap-src"
        dst = self.root / "swap-dst"
        src.mkdir(); dst.mkdir()
        (src / "new.txt").write_text("new", encoding="utf-8")
        (dst / "old.txt").write_text("old", encoding="utf-8")
        swapped = self.run_op("fileSwapTree", {"baseDir": str(self.root), "from": "swap-src", "to": "swap-dst"})
        self.assertTrue(swapped["backup"])
        self.assertFalse(src.exists())
        self.assertEqual((dst / "new.txt").read_text(encoding="utf-8"), "new")

    def test_file_move_stat_branch(self):
        src = self.root / "move-src.txt"
        src.write_text("x", encoding="utf-8")
        moved = self.run_op("fileMove", {"baseDir": str(self.root), "from": "move-src.txt", "to": "move-dst.txt"})
        self.assertEqual(moved["to"], "move-dst.txt")
        self.assertFalse(src.exists())
        stat = self.run_op("fileStat", {"baseDir": str(self.root), "path": "move-dst.txt"})
        self.assertTrue(stat["exists"])
        self.assertEqual(stat["size"], 1)
        self.assertEqual(self.run_op("pickValue", {"condition": True, "whenTrue": "a", "whenFalse": "b"}), "a")

    def test_fs_transaction_rolls_back(self):
        (self.root / "tx.txt").write_text("old", encoding="utf-8")
        with self.assertRaises(BizError):
            self.run_op("fsTransaction", {
                "baseDir": str(self.root),
                "operations": [
                    {"op": "write", "path": "tx.txt", "content": "new"},
                    {"op": "write", "path": "../escape.txt", "content": "bad"},
                ],
            })
        self.assertEqual((self.root / "tx.txt").read_text(encoding="utf-8"), "old")
        self.assertFalse((self.root.parent / "escape.txt").exists())

    def test_zip_extract(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("dir/a.txt", "hello")
            zf.writestr("../escape.txt", "bad")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        with self.assertRaises(BizError) as ctx:
            self.run_op("zipExtract", {"baseDir": str(self.root), "target": "unzip", "zipBase64": encoded})
        self.assertEqual(ctx.exception.status, 403)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("dir/a.txt", "hello")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        result = self.run_op("zipExtract", {"baseDir": str(self.root), "target": "unzip", "zipBase64": encoded})
        self.assertEqual(result["count"], 1)
        self.assertEqual((self.root / "unzip" / "dir" / "a.txt").read_text(encoding="utf-8"), "hello")

    def test_hash_sort_pick(self):
        self.assertEqual(self.run_op("hash", {"content": "abc"}),
                         "a9993e364706816aba3e25717850c26c9cd0d89d")
        rows = [{"id": "a", "data": {"at": "1"}}, {"id": "b", "data": {"at": "2"}}]
        sorted_rows = self.run_op("sortList", {"data": rows, "field": "data.at", "desc": True})
        self.assertEqual([x["id"] for x in sorted_rows], ["b", "a"])
        self.assertEqual(rows[0]["id"], "a")  # 不修改上游
        picked = self.run_op("pickPaths", {
            "data": rows, "fields": {"id": "id", "at": "data.at"},
        })
        self.assertEqual(picked[0], {"id": "a", "at": "1"})


if __name__ == "__main__":
    unittest.main()
