"""算子测试套件：一个算子 = 节点模板 + 用例文件 + 约 5 行测试入口（对应 datamore 的 testhelper）。

    class TestSqlQuery(OperatorTestSuite):
        md_root = MD_ROOT
        operator = "sqlQuery"
        template = "external/usql/sqlQuery.yaml"

每个用例生成 test_case_<用例名> 方法。执行流程与线上同一条代码路径：
模板 config + 用例 config → 构造 Mock 数据源 → compile_node → run_node → 断言 → 契约检查。
"""
from __future__ import annotations

import copy
import unittest
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable, ClassVar, List, Optional, Tuple, Union

import yaml

from ..config.loader import load_node, read_yaml
from ..config.models import GroupDef, NodeDef
from ..core import BuildEnv, Context, Executor
from ..core.builder import compile_node
from ..errors import ConfigError, LowcodeError
from ..operators import get_operator
from .assertion import first_diff
from .cases import InputCase, load_cases
from .mocks import build_mocks

_GROUP = GroupDef(module="test", group="node", name="test")


class OperatorTestSuite(unittest.TestCase):
    """子类声明下面三个属性即可；没有声明 operator 的子类视为抽象基类，不生成测试。

    内置算子在 lowcode.operators 包导入时即完成注册，测试无需额外加载步骤。
    """

    md_root: ClassVar[Optional[Union[str, Path]]] = None  # 算子手册根目录（模板 / 用例路径的基准）
    operator: ClassVar[str] = ""                          # 算子注册名
    template: ClassVar[str] = ""                          # 节点模板，相对 md_root，如 external/usql/sqlQuery.yaml

    _node: ClassVar[NodeDef]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.operator:
            return
        try:
            cls._node, cases = _load_suite(cls)
        except (ConfigError, OSError) as e:
            # 模板 / 用例文件有误时生成一个失败的测试，而不是让整个测试模块导入失败
            cls.test_load = _failing(f"failed to load test assets for {cls.operator}:\n{e}")
            return
        cls.test_register = _register_test()
        for case in cases:
            setattr(cls, f"test_case_{case.name}", _case_test(case))


def _load_suite(cls: type) -> Tuple[NodeDef, List[InputCase]]:
    if cls.md_root is None:
        raise ConfigError(f"{cls.__name__} has no md_root set")
    root = Path(cls.md_root).resolve()
    tpl = root / cls.template
    if not tpl.is_file():
        raise ConfigError(f"template not found: {tpl}")
    node = load_node(read_yaml(tpl, cls.template), cls.template)
    if node.name != cls.operator:
        raise ConfigError(f"template operator {node.name!r} does not match declared {cls.operator!r}", cls.template)

    cases_file = tpl.with_name(f"{tpl.stem}_input{tpl.suffix}")  # sqlQuery.yaml → sqlQuery_input.yaml
    if not cases_file.is_file():
        raise ConfigError(f"case file not found: {cases_file}")
    return node, load_cases(cases_file, cases_file.relative_to(root).as_posix())


def _failing(msg: str) -> Callable[[unittest.TestCase], None]:
    def test_load(self: unittest.TestCase) -> None:
        self.fail(msg)
    return test_load


def _register_test() -> Callable[[OperatorTestSuite], None]:
    def test_register(self: OperatorTestSuite) -> None:
        """算子已注册；模板所在目录与注册分类一致"""
        try:
            op = get_operator(self.operator)
        except ConfigError as e:
            self.fail(str(e))
        folder = Path(self.template).parent.as_posix()
        if folder == ".":  # 模板直接放在 md_root 下，不校验目录
            return
        # 分类目录须与 category 一致；external 下还按数据源分子目录（usql / uhttp / uredis）
        if folder != op.category and not folder.startswith(op.category + "/"):
            self.fail(f"template lives in {folder}/ but operator {op.name} is registered as {op.category}")
    return test_register


def _case_test(case: InputCase) -> Callable[[OperatorTestSuite], None]:
    def test(self: OperatorTestSuite) -> None:
        run_case(self, self._node, case)
    test.__doc__ = case.desc  # unittest -v 显示为用例说明
    return test


def run_case(tc: unittest.TestCase, template: NodeDef, case: InputCase) -> None:
    """按用例执行一次算子并断言。失败信息里都带用例位置（文件 › 用例名）。"""
    node_id = template.id or template.name
    if node_id in case.upstream:
        tc.fail(f"{case.where}: upstream {node_id!r} conflicts with the node id under test")
    node = NodeDef(name=template.name, id=node_id, depends=list(case.upstream),
                   config={**template.config, **case.config}, where=case.where)
    upstream_ids = set(case.upstream)

    with ExitStack() as stack:
        build_error: Optional[ConfigError] = None
        try:
            datasources = build_mocks(case.mocks, stack, f"{case.where}.mocks")
            env = BuildEnv(datasources, _GROUP, case.where)
            plan_node = compile_node(node, env, upstream_ids, upstream_ids | {node_id}, list(case.inputs))
        except ConfigError as e:
            build_error = e

        if case.expect.kind == "buildError":
            _check_build_error(tc, case, build_error)
            return
        if build_error is not None:
            tc.fail(f"{case.where}: build failed\n{build_error}")

        ctx = Context(case.inputs, request=case.request, timeout=case.timeout)
        for nid, value in case.upstream.items():
            ctx.set_output(nid, value)
        snapshot = copy.deepcopy((case.inputs, case.upstream, plan_node.static))

        error: Optional[LowcodeError] = None
        try:
            Executor.run_node(plan_node, ctx)  # run_node 已把所有异常统一为 LowcodeError
        except LowcodeError as e:
            error = e

        _check_untouched(tc, case, snapshot, (case.inputs, case.upstream, plan_node.static))
        if case.expect.kind == "error":
            _check_error(tc, case, error, ctx, node_id)
        else:
            _check_output(tc, case, error, ctx, node_id)


def _check_build_error(tc: unittest.TestCase, case: InputCase, err: Optional[ConfigError]) -> None:
    want = case.expect.build_error
    if err is None:
        tc.fail(f"{case.where}: expected build error containing {want!r}, but build succeeded")
    if want not in str(err):
        tc.fail(f"{case.where}: build error does not contain {want!r}\nactual: {err}")


def _check_error(tc: unittest.TestCase, case: InputCase, err: Optional[LowcodeError],
                 ctx: Context, node_id: str) -> None:
    want = case.expect.error
    if err is None:
        tc.fail(f"{case.where}: expected an error, but it succeeded. output:\n{_dump(ctx.output(node_id))}")
    actual = {"code": err.code, "status": err.status, "type": type(err).__name__, "msg": err.msg}
    for key, expected in want.items():
        if expected is None:
            continue
        ok = expected in actual["msg"] if key == "msg" else actual[key] == expected
        if not ok:
            tc.fail(f"{case.where}: error.{key} expected {expected!r}, got {actual[key]!r}\nactual error: {actual}")


def _check_output(tc: unittest.TestCase, case: InputCase, err: Optional[LowcodeError],
                  ctx: Context, node_id: str) -> None:
    if err is not None:
        tc.fail(f"{case.where}: expected success, got {type(err).__name__}(code={err.code}): {err.msg}")
    actual = ctx.output(node_id)
    diff = first_diff(actual, case.expect.output)
    if diff:
        tc.fail(f"{case.where}: {diff}\n实际输出：\n{_dump(actual)}")


def _check_untouched(tc: unittest.TestCase, case: InputCase, before: Any, after: Any) -> None:
    """契约：算子不得原地修改 inputs / 上游输出 / 静态参数（它们在节点之间、请求之间共享）。"""
    for label, b, a in zip(("inputs", "upstream", "config"), before, after):
        diff = first_diff(a, b, label)
        if diff:
            tc.fail(f"{case.where}: operator mutated {label} in place (contract violation: copy before modifying)\n{diff}")


def _dump(value: Any) -> str:
    """把实际输出转成 YAML，方便直接粘贴进用例文件。"""
    try:
        return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, default_flow_style=None).rstrip()
    except yaml.YAMLError:
        return repr(value)
