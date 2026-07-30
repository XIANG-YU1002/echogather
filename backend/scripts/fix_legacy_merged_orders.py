"""一次性資料修正：舊合併邏輯留下的 cancelled 訂單改標為 merged。

背景（使用者 2026-07-30 同意執行）：
2026-07-29 的合併功能把被併掉的來源訂單標為 cancelled，2026-07-30 改為專屬狀態
merged。在改版前用瀏覽器實測合併所產生的訂單仍是 cancelled，會被算進「已取消」
的頁籤數字，畫面也與新規則不一致。

判斷依據：狀態歷史裡有一筆 cancelled 且 note 以「已合併至」開頭——那是舊版
merge_orders 寫的。會員自己申請取消的訂單沒有這種 note，不會被動到。

安全性：
- 只 UPDATE status，不刪除任何資料
- 另外補一筆 merged 狀態歷史註明是資料修正，原本的 cancelled 歷史保留
- 修正前後比對庫存占用量，不同就中止不提交
  （cancelled 與 merged 同屬不佔用庫存的狀態，占用量應完全不變）

注意：這些訂單沒有 order_merge 紀錄，因此無法拆單，只是不再顯示於前後台。

執行方式（於 backend/ 目錄）：
    .\\venv\\Scripts\\python.exe scripts/fix_legacy_merged_orders.py

（自帶 sys.path 處理，不需要先設 PYTHONPATH——其他 seed 腳本沒有這段，
所以那些要嘛設 PYTHONPATH，要嘛以 python -m scripts.xxx 執行。）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402 — 需先補上 sys.path 才能匯入 app

from app.core.database import SessionLocal  # noqa: E402
from app.models.enums import OrderStatus  # noqa: E402
from app.models.order import OrderStatusHistory  # noqa: E402

SELECT_LEGACY = """
    select o.id, o.order_number
    from group_order o
    join order_status_history h on h.order_id = o.id
    where o.status = 'cancelled'
      and h.status = 'cancelled'
      and h.note like '已合併至%'
    order by o.order_number
"""

OCCUPIED = """
    select coalesce(sum(i.quantity), 0)
    from order_item i
    join group_order o on o.id = i.order_id
    where o.status not in ('cancelled', 'rejected', 'merged')
"""

NOTE = "資料修正（2026-07-30）：舊合併邏輯標為已取消，改標為已合併"


def main() -> None:
    db = SessionLocal()
    try:
        targets = db.execute(text(SELECT_LEGACY)).all()
        if not targets:
            print("沒有需要修正的訂單。")
            return

        print(f"待修正：{len(targets)} 筆")
        occupied_before = db.execute(text(OCCUPIED)).scalar()

        for row in targets:
            db.execute(
                text("update group_order set status = 'merged' where id = :i"),
                {"i": row.id},
            )
            # 用 ORM 物件而非 raw INSERT：order_status_history.id 沒有 DB 層
            # gen_random_uuid() 預設值，UUID 是 UUIDPrimaryKeyMixin 在 Python 端產生的，
            # raw SQL 會繞過它而違反 NOT NULL。
            db.add(
                OrderStatusHistory(
                    order_id=row.id, status=OrderStatus.MERGED, note=NOTE
                )
            )
            print(f"  {row.order_number} -> merged")

        db.flush()
        occupied_after = db.execute(text(OCCUPIED)).scalar()
        if occupied_before != occupied_after:
            db.rollback()
            raise SystemExit(
                f"庫存占用量變了（{occupied_before} -> {occupied_after}），已中止不提交"
            )

        db.commit()
        print(f"\n已提交。庫存占用量 {occupied_before} 不變。")

        print("\n修正後各狀態訂單數：")
        print("  ", dict(db.execute(text(
            "select status, count(*) from group_order group by status order by status"
        )).all()))
        print("\n剩餘 cancelled（應只有會員真正申請取消的）：")
        for r in db.execute(text(
            "select order_number from group_order where status = 'cancelled' "
            "order by order_number"
        )).all():
            print("  ", r.order_number)
    finally:
        db.close()


if __name__ == "__main__":
    main()
