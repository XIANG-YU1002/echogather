"""訂單合併紀錄與拆單申請的資料存取。

合併紀錄以 batch_id 分批：一次合併操作產生一個批次，批次內每張來源訂單一列。
拆單一律以「整個批次」為單位還原（部分還原會讓數量與金額算不回去）。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import CancellationStatus
from app.models.order import OrderMerge, OrderUnmergeRequest


def create_merge_record(
    db: Session,
    *,
    batch_id: uuid.UUID,
    target_order_id: uuid.UUID,
    source_order_id: uuid.UUID,
    source_status_before: str,
    source_paid_amount_before: object,
    target_status_before: str,
    target_product_total_before: object,
    target_paid_amount_before: object,
) -> OrderMerge:
    record = OrderMerge(
        batch_id=batch_id,
        target_order_id=target_order_id,
        source_order_id=source_order_id,
        source_status_before=source_status_before,
        source_paid_amount_before=source_paid_amount_before,
        target_status_before=target_status_before,
        target_product_total_before=target_product_total_before,
        target_paid_amount_before=target_paid_amount_before,
    )
    db.add(record)
    return record


def list_active_by_target(db: Session, target_order_id: uuid.UUID) -> list[OrderMerge]:
    """指定訂單上尚未拆開的合併紀錄，新的批次排在前面。"""
    stmt = (
        select(OrderMerge)
        .where(
            OrderMerge.target_order_id == target_order_id,
            OrderMerge.unmerged_at.is_(None),
        )
        .order_by(OrderMerge.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_batch(
    db: Session, batch_id: uuid.UUID, *, only_active: bool = True, for_update: bool = False
) -> list[OrderMerge]:
    stmt = select(OrderMerge).where(OrderMerge.batch_id == batch_id)
    if only_active:
        stmt = stmt.where(OrderMerge.unmerged_at.is_(None))
    if for_update:
        stmt = stmt.with_for_update()
    return list(db.execute(stmt).scalars().all())


def get_latest_active_batch_id(db: Session, target_order_id: uuid.UUID) -> uuid.UUID | None:
    """最近一次尚未拆開的合併批次。

    二次合併後只能從最新的批次往回拆——先拆舊批次會把新批次併進來的數量算錯。
    """
    records = list_active_by_target(db, target_order_id)
    return records[0].batch_id if records else None


def mark_batch_unmerged(db: Session, records: list[OrderMerge], unmerged_at: object) -> None:
    for record in records:
        record.unmerged_at = unmerged_at


def create_unmerge_request(
    db: Session, *, order_id: uuid.UUID, batch_id: uuid.UUID, reason: str | None
) -> OrderUnmergeRequest:
    request = OrderUnmergeRequest(order_id=order_id, batch_id=batch_id, reason=reason)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def get_unmerge_request_by_id(
    db: Session, request_id: uuid.UUID, *, for_update: bool = False
) -> OrderUnmergeRequest | None:
    stmt = select(OrderUnmergeRequest).where(OrderUnmergeRequest.id == request_id)
    if for_update:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def get_pending_unmerge_request(
    db: Session, order_id: uuid.UUID, batch_id: uuid.UUID | None = None
) -> OrderUnmergeRequest | None:
    stmt = select(OrderUnmergeRequest).where(
        OrderUnmergeRequest.order_id == order_id,
        OrderUnmergeRequest.status == CancellationStatus.PENDING,
    )
    if batch_id is not None:
        stmt = stmt.where(OrderUnmergeRequest.batch_id == batch_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none()


def list_unmerge_requests_by_order(db: Session, order_id: uuid.UUID) -> list[OrderUnmergeRequest]:
    stmt = (
        select(OrderUnmergeRequest)
        .where(OrderUnmergeRequest.order_id == order_id)
        .order_by(OrderUnmergeRequest.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())
