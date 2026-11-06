"""按天切分的文件日志：文件名自带日期，每天一个文件。

    logs/lowcode-2026-11-06.log
    logs/lowcode-2026-11-07.log   # 跨天自动切换；早于保留天数的文件会被删除

与 TimedRotatingFileHandler 的区别：后者当天写固定名（lowcode.log），切分时才改名；
这里文件创建时就带日期，直接按文件名就能定位某一天的日志。
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, TextIO


class DailyFileHandler(logging.Handler):
    """每天的日志写入 ``<directory>/<stem>-YYYY-MM-DD.log``。"""

    def __init__(self, directory: Path, stem: str = "lowcode", backup: int = 7,
                 encoding: str = "utf-8") -> None:
        super().__init__()
        self.directory = Path(directory)
        self.stem = stem
        self.backup = backup
        self.encoding = encoding
        self._stream: Optional[TextIO] = None
        self._day: Optional[date] = None

    def path_for(self, day: date) -> Path:
        return self.directory / f"{self.stem}-{day:%Y-%m-%d}.log"

    def emit(self, record: logging.LogRecord) -> None:
        try:
            today = date.today()
            if self._stream is None or self._day != today:
                self._open(today)
            assert self._stream is not None
            self._stream.write(self.format(record) + "\n")
            self._stream.flush()
        except Exception:  # noqa: BLE001  日志失败不应影响业务
            self.handleError(record)

    def _open(self, day: date) -> None:
        self._close()
        self.directory.mkdir(parents=True, exist_ok=True)
        self._stream = open(self.path_for(day), "a", encoding=self.encoding)
        self._day = day
        self._cleanup(day)

    def _cleanup(self, today: date) -> None:
        """删除超过 backup 天的旧日志；backup <= 0 表示不清理。"""
        if self.backup <= 0:
            return
        prefix = f"{self.stem}-"
        cutoff = today - timedelta(days=self.backup)
        for path in self.directory.glob(f"{prefix}*.log"):
            raw = path.name[len(prefix):-len(".log")]
            try:
                day = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                continue
            if day < cutoff:
                path.unlink(missing_ok=True)

    def _close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    def close(self) -> None:
        self._close()
        super().close()
