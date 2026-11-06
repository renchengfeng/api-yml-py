"""算子测试入口：按算子分类分目录 tests/operators/<分类>/test_<算子名>.py，与 lowcode/operators 层级一一对应；用例数据在 operator_md/<分类>/<算子名>_input.yaml。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MD_ROOT = ROOT / "operator_md"  # 内置算子手册根目录
