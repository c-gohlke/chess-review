from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from chess_review.db import connect


def test_a_request_can_use_its_connection_on_another_thread(tmp_path: Path) -> None:
    conn = connect(tmp_path / "db.sqlite3")

    with ThreadPoolExecutor(1) as pool:
        rows = pool.submit(lambda: conn.execute("SELECT 1").fetchone()[0])

        assert rows.result() == 1
