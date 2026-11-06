"""生成演示数据库 data/demo.db（可重复执行，会重建）。

    python data/make_db.py
"""
import random
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "demo.db"
CITIES = ["北京", "上海", "深圳", "杭州", "成都"]
STATUS = ["paid", "paid", "paid", "refunded", "pending"]


def main() -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    rnd = random.Random(42)  # 固定种子：每次生成的数据一致，便于演示与测试
    with sqlite3.connect(DB) as conn:
        conn.executescript("""
            create table users (
                id integer primary key autoincrement,
                name text not null, phone text not null, level integer not null,
                city text not null, created_at text not null default (datetime('now'))
            );
            create table orders (
                id integer primary key autoincrement,
                uid integer not null references users(id),
                amount real not null, status text not null,
                created_at text not null default (datetime('now'))
            );
            create index idx_orders_uid on orders(uid);
        """)
        for i in range(1, 31):
            conn.execute("insert into users(name, phone, level, city) values (?, ?, ?, ?)",
                         (f"用户{i:02d}", f"138{rnd.randint(10000000, 99999999)}",
                          rnd.randint(1, 5), rnd.choice(CITIES)))
        for _ in range(120):
            conn.execute("insert into orders(uid, amount, status) values (?, ?, ?)",
                         (rnd.randint(1, 30), round(rnd.uniform(10, 500), 2), rnd.choice(STATUS)))
    print(f"已生成 {DB}（users 30 行，orders 120 行）")


if __name__ == "__main__":
    main()
