import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import (
    UNMERGE_ALLOWED_STATUSES,
    CancellationStatus,
    GroupLeaderOrderStatusFilter,
    OrderStatus,
)
from app.models.group_leader import GroupLeaderProfile
from app.models.order import CancellationRequest, GroupOrder, OrderUnmergeRequest
from app.repositories import (
    cancellation_repository,
    group_buy_repository,
    order_merge_repository,
    order_repository,
    user_repository,
)
from app.schemas.common import normalize_optional_text
from app.schemas.group_leader_order import (
    GroupLeaderOrderDetailResponse,
    GroupLeaderOrderListItem,
    GroupLeaderOrderSummary,
    MemberContactSnapshot,
    MergeOrdersRequest,
)
from app.schemas.order import (
    CancellationRequestSummary,
    MergedSourceOrderSummary,
    OrderItemDetail,
    UnmergeRequestSummary,
)
from app.services import notification_service, order_service
from app.services.order_service import build_item_summary

_CANCELLABLE_STATUSES = {
    OrderStatus.PENDING_CONFIRMATION,
    OrderStatus.PENDING_PAYMENT,
    OrderStatus.PAID,
}

_AVAILABLE_ACTIONS_BY_STATUS = {
    OrderStatus.PENDING_CONFIRMATION: ["accept", "reject"],
    OrderStatus.PENDING_PAYMENT: ["mark-paid"],
    OrderStatus.PAID: ["mark-shipped"],
    OrderStatus.SHIPPED: ["complete"],
}


def _load_owned_order(
    db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID, *, for_update: bool = False
) -> GroupOrder:
    """載入自己開團底下的訂單。

    被合併掉的來源訂單（merged）依使用者 2026-07-30 裁決在團主端也視為已刪除，
    因此一律回 404，避免它從詳情頁或任何狀態操作的網址被翻出來。
    拆單還原要讀來源訂單，走的是 order_repository.get_by_id（不經過這裡）。
    """
    order = order_repository.get_by_id(db, order_id, for_update=for_update)
    if order is None:
        raise AppError(404, "ORDER_NOT_FOUND", "找不到指定的訂單。")
    if order.status == OrderStatus.MERGED:
        raise AppError(404, "ORDER_NOT_FOUND", "找不到指定的訂單。")
    group_buy = group_buy_repository.get_by_id(db, order.group_buy_id)
    if group_buy.group_leader_profile_id != profile.id:
        raise AppError(404, "ORDER_NOT_OWNED_BY_GROUP_LEADER", "此訂單不屬於你管理的開團。")
    return order


def _cancellation_to_summary(request: CancellationRequest) -> CancellationRequestSummary:
    return CancellationRequestSummary(
        id=request.id,
        order_id=request.order_id,
        reason=request.reason,
        status=request.status,
        response_note=request.response_note,
        processed_at=request.processed_at,
        created_at=request.created_at,
    )


def get_orders(
    db: Session,
    profile: GroupLeaderProfile,
    *,
    group_buy_id: uuid.UUID | None,
    activity_id: uuid.UUID | None,
    status: GroupLeaderOrderStatusFilter | None,
    has_pending_cancellation: bool | None,
    keyword: str | None,
    page: int,
    page_size: int,
    newest_first: bool = False,
) -> tuple[list[GroupLeaderOrderListItem], int, GroupLeaderOrderSummary]:
    """status 可為單一狀態或複合值 pending（待確認＋待付款），見 enums 的說明。

    回傳的 summary 供圖 25 六張統計卡使用：吃開團／活動／關鍵字條件，但不吃狀態。
    """
    orders, total = order_repository.list_for_leader(
        db,
        profile.id,
        group_buy_id=group_buy_id,
        activity_id=activity_id,
        statuses=status.to_order_statuses() if status is not None else None,
        has_pending_cancellation=has_pending_cancellation,
        keyword=keyword,
        page=page,
        page_size=page_size,
        newest_first=newest_first,
    )

    # 輪次編號與開團狀態一次查完，避免每列各打一次 DB
    round_numbers = group_buy_repository.get_round_numbers(
        db, [order.group_buy_id for order in orders]
    )

    items = []
    for order in orders:
        member = user_repository.get_by_id(db, order.user_id)
        has_pending = cancellation_repository.get_pending_by_order_id(db, order.id) is not None
        order_items = order_repository.get_items(db, order.id)
        group_buy = group_buy_repository.get_by_id(db, order.group_buy_id)
        items.append(
            GroupLeaderOrderListItem(
                id=order.id,
                order_number=order.order_number,
                member_nickname=member.nickname if member is not None else "",
                member_avatar_url=member.avatar_url if member is not None else None,
                group_buy_id=order.group_buy_id,
                activity_name=order.activity_name_snapshot,
                round_number=round_numbers.get(order.group_buy_id, 1),
                group_buy_status=group_buy.status,
                representative_image_url=(
                    order_items[0].image_url_snapshot if order_items else ""
                ),
                item_summary=build_item_summary(order_items),
                item_count=len(order_items),
                total_quantity=sum(item.quantity for item in order_items),
                status=order.status,
                product_total_amount=order.product_total_amount,
                has_pending_cancellation=has_pending,
                created_at=order.created_at,
            )
        )

    counts = order_repository.count_for_leader_grouped_by_status(
        db,
        profile.id,
        group_buy_id=group_buy_id,
        activity_id=activity_id,
        keyword=keyword,
    )
    summary = GroupLeaderOrderSummary(
        pending_confirmation=counts.get(OrderStatus.PENDING_CONFIRMATION, 0),
        pending_payment=counts.get(OrderStatus.PENDING_PAYMENT, 0),
        paid=counts.get(OrderStatus.PAID, 0),
        shipped=counts.get(OrderStatus.SHIPPED, 0),
        completed=counts.get(OrderStatus.COMPLETED, 0),
        cancelled=counts.get(OrderStatus.CANCELLED, 0),
        rejected=counts.get(OrderStatus.REJECTED, 0),
        pending_cancellation=order_repository.count_pending_cancellation_for_leader(
            db,
            profile.id,
            group_buy_id=group_buy_id,
            activity_id=activity_id,
            keyword=keyword,
        ),
    )
    return items, total, summary


def get_order_detail(
    db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID
) -> GroupLeaderOrderDetailResponse:
    order = _load_owned_order(db, profile, order_id)
    member = user_repository.get_by_id(db, order.user_id)
    items = order_repository.get_items(db, order.id)
    cancellation_requests = cancellation_repository.list_by_order_id(db, order.id)
    pending = next(
        (r for r in cancellation_requests if r.status == CancellationStatus.PENDING), None
    )
    unmerge_requests = order_merge_repository.list_unmerge_requests_by_order(db, order.id)
    pending_unmerge = next(
        (r for r in unmerge_requests if r.status == CancellationStatus.PENDING), None
    )
    # 收單期限讀開團的即時值，團主延期後詳情頁要跟著更新
    group_buy = group_buy_repository.get_by_id(db, order.group_buy_id)

    return GroupLeaderOrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        rejection_reason=order.rejection_reason,
        product_total_amount=order.product_total_amount,
        paid_amount=order.paid_amount,
        outstanding_amount=order.product_total_amount - order.paid_amount,
        member_nickname=member.nickname if member is not None else "",
        member_avatar_url=member.avatar_url if member is not None else None,
        member_contacts=MemberContactSnapshot(
            facebook=order.member_facebook_contact_snapshot,
            discord=order.member_discord_contact_snapshot,
            line=order.member_line_contact_snapshot,
        ),
        activity_name=order.activity_name_snapshot,
        group_leader_name=order.group_leader_name_snapshot,
        deadline_at=group_buy.deadline_at,
        payment_method=order.payment_method_snapshot,
        payment_method_note=order.payment_method_note_snapshot,
        requires_second_payment=order.requires_second_payment_snapshot,
        includes_full_gift=order.includes_full_gift_snapshot,
        rules=order.rules_snapshot,
        contact_platform=order.leader_contact_platform_snapshot,
        contact_value=order.leader_contact_value_snapshot,
        items=[
            OrderItemDetail(
                id=item.id,
                product_name_snapshot=item.product_name_snapshot,
                image_url_snapshot=item.image_url_snapshot,
                # 多角色商品要顯示所選角色，原本漏傳導致團主端一律看不到
                chosen_character_name=item.chosen_character_name_snapshot,
                unit_price=item.unit_price,
                quantity=item.quantity,
                subtotal=item.subtotal,
            )
            for item in items
        ],
        pending_cancellation_request=(
            _cancellation_to_summary(pending) if pending is not None else None
        ),
        cancellation_requests=[_cancellation_to_summary(r) for r in cancellation_requests],
        pending_unmerge_request=(
            order_service.build_unmerge_summary(db, pending_unmerge)
            if pending_unmerge is not None
            else None
        ),
        unmerge_requests=[
            order_service.build_unmerge_summary(db, r) for r in unmerge_requests
        ],
        available_actions=_AVAILABLE_ACTIONS_BY_STATUS.get(order.status, []),
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


# 可合併的狀態（依使用者 2026-07-29 裁決）。已出貨之後的訂單不再合併，
# 已取消／已拒絕也不列入。
MERGEABLE_STATUSES = (
    OrderStatus.PENDING_CONFIRMATION,
    OrderStatus.PENDING_PAYMENT,
    OrderStatus.PAID,
)


def get_mergeable_orders(
    db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID
) -> list[GroupLeaderOrderListItem]:
    """可與指定訂單合併的其他訂單：同開團、同會員、狀態可合併、且沒有待處理取消申請。"""
    order = _load_owned_order(db, profile, order_id)
    # 這張訂單本身不可合併時就沒有合併的餘地，直接回空清單，
    # 前端也就不會顯示「合併訂單」區塊（使用者 2026-07-29 指示）。
    if order.status not in MERGEABLE_STATUSES:
        return []
    if cancellation_repository.get_pending_by_order_id(db, order.id) is not None:
        return []

    candidates = order_repository.list_same_member_orders_in_group_buy(
        db,
        order.group_buy_id,
        order.user_id,
        statuses=MERGEABLE_STATUSES,
        exclude_order_id=order.id,
    )
    member = user_repository.get_by_id(db, order.user_id)
    group_buy = group_buy_repository.get_by_id(db, order.group_buy_id)
    round_number = group_buy_repository.get_round_number(db, group_buy)

    items = []
    for candidate in candidates:
        # 有待處理取消申請的訂單不能合併——那張訂單的去向還沒定案
        if cancellation_repository.get_pending_by_order_id(db, candidate.id) is not None:
            continue
        candidate_items = order_repository.get_items(db, candidate.id)
        items.append(
            GroupLeaderOrderListItem(
                id=candidate.id,
                order_number=candidate.order_number,
                member_nickname=member.nickname if member is not None else "",
                member_avatar_url=member.avatar_url if member is not None else None,
                group_buy_id=candidate.group_buy_id,
                activity_name=candidate.activity_name_snapshot,
                round_number=round_number,
                group_buy_status=group_buy.status,
                representative_image_url=(
                    candidate_items[0].image_url_snapshot if candidate_items else ""
                ),
                item_summary=build_item_summary(candidate_items),
                item_count=len(candidate_items),
                total_quantity=sum(item.quantity for item in candidate_items),
                status=candidate.status,
                product_total_amount=candidate.product_total_amount,
                has_pending_cancellation=False,
                created_at=candidate.created_at,
            )
        )
    return items


def merge_orders(
    db: Session,
    profile: GroupLeaderProfile,
    order_id: uuid.UUID,
    payload: MergeOrdersRequest,
) -> GroupLeaderOrderDetailResponse:
    """把同會員同開團的多筆訂單合併成一筆（依使用者 2026-07-29 裁決）。

    規則：
    - 保留哪一張由 keep 決定（oldest／newest），保留者的訂單編號與建立時間留下；
      建立時間會影響先喊先得的排隊順位，所以這是團主的選擇而非系統決定。
    - 同商品同角色的明細數量相加（order_item 有 (order,product,character) 唯一約束）。
    - 合併後狀態取進度最慢者：含待確認就是待確認。
    - 已付款訂單併入時，那部分的錢已收，記入 paid_amount 與待收金額分開顯示。
    - 被併入的訂單標記為 merged（使用者 2026-07-30 改為專屬狀態，不再寫成已取消），
      前後台都不再顯示，但資料完整保留；同時寫入 order_merge 紀錄合併前的狀態與金額，
      供會員申請拆單、團主核准後還原。
    """
    if not payload.merge_with_order_ids:
        raise AppError(422, "VALIDATION_ERROR", "請選擇要合併的訂單。")

    # 一起鎖定，避免併發合併造成明細重複搬移
    base = _load_owned_order(db, profile, order_id, for_update=True)
    others = []
    for other_id in payload.merge_with_order_ids:
        if other_id == order_id:
            raise AppError(422, "VALIDATION_ERROR", "不能與自己合併。")
        other = _load_owned_order(db, profile, other_id, for_update=True)
        if other.group_buy_id != base.group_buy_id:
            raise AppError(409, "ORDER_MERGE_DIFFERENT_GROUP_BUY", "只能合併同一個開團的訂單。")
        if other.user_id != base.user_id:
            raise AppError(409, "ORDER_MERGE_DIFFERENT_MEMBER", "只能合併同一位會員的訂單。")
        others.append(other)

    all_orders = [base, *others]
    for order in all_orders:
        if order.status not in MERGEABLE_STATUSES:
            raise AppError(
                409,
                "ORDER_MERGE_STATUS_NOT_ALLOWED",
                "只有待確認、待付款、已付款的訂單可以合併。",
                {"order_number": order.order_number, "status": order.status.value},
            )
        if cancellation_repository.get_pending_by_order_id(db, order.id) is not None:
            raise AppError(
                409,
                "ORDER_MERGE_HAS_PENDING_CANCELLATION",
                "有待處理取消申請的訂單無法合併，請先處理該申請。",
                {"order_number": order.order_number},
            )

    # 依建立時間決定保留哪一張（同時間時以 id 穩定排序）
    ordered = sorted(all_orders, key=lambda o: (o.created_at, str(o.id)))
    target = ordered[0] if payload.keep == "oldest" else ordered[-1]
    sources = [order for order in all_orders if order.id != target.id]

    # 目標訂單既有明細，用 (商品, 角色) 當索引以便數量相加
    target_items = {
        (item.group_buy_product_id, item.chosen_character_id): item
        for item in order_repository.get_items(db, target.id)
    }
    # 已收金額＝各訂單已收部分的總和。已付款訂單是全額已收；其餘取它自己的
    # paid_amount，這樣先前合併留下的已收金額不會在二次合併時被丟掉。
    paid_amount = sum(
        (
            order.product_total_amount
            if order.status == OrderStatus.PAID
            else order.paid_amount
        )
        for order in all_orders
    )

    for source in sources:
        for item in order_repository.get_items(db, source.id):
            key = (item.group_buy_product_id, item.chosen_character_id)
            existing = target_items.get(key)
            if existing is not None:
                existing.quantity += item.quantity
                existing.subtotal = existing.unit_price * existing.quantity
            else:
                # 複製到目標訂單，來源訂單保留自己的明細作為歷史紀錄——若直接搬移，
                # 被合併的訂單會變成沒有商品的空殼，列表上顯示「共 0 件商品」。
                # 來源訂單已標記為 cancelled，依 §20.1 不計入庫存佔用量，不會重複佔用。
                target_items[key] = order_repository.create_order_item(
                    db,
                    order_id=target.id,
                    group_buy_product_id=item.group_buy_product_id,
                    chosen_character_id=item.chosen_character_id,
                    chosen_character_name_snapshot=item.chosen_character_name_snapshot,
                    product_name_snapshot=item.product_name_snapshot,
                    image_url_snapshot=item.image_url_snapshot,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                    subtotal=item.subtotal,
                )
    db.flush()

    # 拆單要能還原成合併前各自的狀態，所以在改動任何欄位「之前」先把快照留下來
    batch_id = uuid.uuid4()
    target_status_before = target.status
    target_product_total_before = target.product_total_amount
    target_paid_amount_before = target.paid_amount
    source_states_before = {source.id: (source.status, source.paid_amount) for source in sources}
    # 通知要列出被併掉的訂單各自有哪些商品（使用者 2026-07-30 需求），
    # 而來源明細在下面不會被改動，但先取出來語意較清楚
    source_item_lines = [
        f"{source.order_number}："
        f"{order_service.describe_items(order_repository.get_items(db, source.id))}"
        for source in sources
    ]

    merged_items = order_repository.get_items(db, target.id)
    target.product_total_amount = sum(item.subtotal for item in merged_items)
    target.paid_amount = paid_amount
    # 合併後狀態（依使用者 2026-07-29 裁決）：團主願意合併就代表已確認這些訂單，
    # 因此待確認的部分直接進到待付款；只有全部都已付款時才維持已付款。
    # 「部分已付款」不另外新增狀態，由 paid_amount 與待收金額的差額表達。
    all_paid = all(order.status == OrderStatus.PAID for order in all_orders)
    target.status = OrderStatus.PAID if all_paid else OrderStatus.PENDING_PAYMENT

    for source in sources:
        status_before, paid_before = source_states_before[source.id]
        source.status = OrderStatus.MERGED
        order_repository.create_status_history(
            db,
            source.id,
            OrderStatus.MERGED,
            note=f"已合併至訂單 {target.order_number}",
        )
        order_merge_repository.create_merge_record(
            db,
            batch_id=batch_id,
            target_order_id=target.id,
            source_order_id=source.id,
            source_status_before=status_before,
            source_paid_amount_before=paid_before,
            target_status_before=target_status_before,
            target_product_total_before=target_product_total_before,
            target_paid_amount_before=target_paid_amount_before,
        )

    order_repository.create_status_history(
        db,
        target.id,
        target.status,
        note="已合併 " + "、".join(source.order_number for source in sources),
    )

    outstanding = target.product_total_amount - target.paid_amount
    if target.status == OrderStatus.PAID:
        payment_note = "款項已全數收到，無需再付款。"
    elif target.paid_amount > 0:
        payment_note = f"其中 NT${target.paid_amount} 已收到，尚需付款 NT${outstanding}。"
    else:
        payment_note = f"合併後應付金額為 NT${outstanding}。"

    # 通知內容依使用者 2026-07-30 需求：說明哪幾筆併到哪一筆、被併掉的訂單各有什麼商品、
    # 有問題請聯絡團主。unmerge_batch_id 讓圖 10 通知中心在這一則底下顯示
    # 「取消合併訂單」按鈕（其他通知不會有）。
    notification_service.notify_order_event(
        db,
        user_id=target.user_id,
        order_id=target.id,
        title="訂單已合併",
        message=(
            f"團主已將你的訂單 {'、'.join(s.order_number for s in sources)} "
            f"合併至 {target.order_number}，原本的訂單不再顯示，請以合併後的訂單為準。\n"
            f"被合併的訂單內容：\n"
            + "\n".join(source_item_lines)
            + f"\n{payment_note}\n"
            "如對合併內容有疑問請聯絡團主；若要恢復成原本的多張訂單，"
            "可在此通知下方提出取消合併申請，由團主為你拆回。"
        ),
        unmerge_batch_id=batch_id,
    )

    db.commit()
    return get_order_detail(db, profile, target.id)


def _load_owned_unmerge_request(
    db: Session, profile: GroupLeaderProfile, request_id: uuid.UUID
) -> tuple[OrderUnmergeRequest, GroupOrder]:
    request = order_merge_repository.get_unmerge_request_by_id(db, request_id, for_update=True)
    if request is None:
        raise AppError(404, "UNMERGE_REQUEST_NOT_FOUND", "找不到指定的取消合併申請。")
    order = _load_owned_order(db, profile, request.order_id, for_update=True)
    return request, order


def approve_unmerge(
    db: Session, profile: GroupLeaderProfile, request_id: uuid.UUID, response_note: str | None
) -> UnmergeRequestSummary:
    """核准會員的拆單申請：把訂單還原成合併前的多張（使用者 2026-07-30 裁決）。

    還原方式：
    - 目標訂單的明細扣掉各來源訂單當初併進來的數量，扣到 0 的那筆是合併時新建的，直接刪除。
    - 目標訂單的狀態與金額改回 order_merge 存下的合併前快照。
    - 各來源訂單改回自己合併前的狀態與已收金額，重新出現在會員端與團主端。

    只能拆最新一批：二次合併後先拆舊批次會把新批次併進來的數量一起扣掉。
    """
    request, target = _load_owned_unmerge_request(db, profile, request_id)
    if request.status != CancellationStatus.PENDING:
        raise AppError(409, "UNMERGE_REQUEST_ALREADY_PROCESSED", "此取消合併申請已被處理。")
    if target.status not in UNMERGE_ALLOWED_STATUSES:
        raise AppError(
            409,
            "UNMERGE_NOT_ALLOWED",
            "訂單目前狀態已無法拆單。",
            {"status": target.status.value},
        )

    records = order_merge_repository.get_batch(db, request.batch_id, for_update=True)
    if not records:
        raise AppError(409, "ORDER_MERGE_ALREADY_UNMERGED", "這批合併已經拆開過了。")
    if order_merge_repository.get_latest_active_batch_id(db, target.id) != request.batch_id:
        raise AppError(
            409,
            "UNMERGE_NOT_LATEST_BATCH",
            "這張訂單之後又合併過，請先拆開最近一次的合併。",
        )

    now = datetime.now(timezone.utc)
    target_items = {
        (item.group_buy_product_id, item.chosen_character_id): item
        for item in order_repository.get_items(db, target.id)
    }

    restored_numbers = []
    for record in records:
        source = order_repository.get_by_id(db, record.source_order_id, for_update=True)
        if source is None:
            continue
        for item in order_repository.get_items(db, source.id):
            key = (item.group_buy_product_id, item.chosen_character_id)
            existing = target_items.get(key)
            if existing is None:
                continue
            existing.quantity -= item.quantity
            if existing.quantity <= 0:
                # 合併時才新建的那筆，拆回後目標訂單本來就不該有
                db.delete(existing)
                target_items.pop(key, None)
            else:
                existing.subtotal = existing.unit_price * existing.quantity
        source.status = record.source_status_before
        source.paid_amount = record.source_paid_amount_before
        order_repository.create_status_history(
            db,
            source.id,
            record.source_status_before,
            note=f"已從訂單 {target.order_number} 拆回",
        )
        restored_numbers.append(source.order_number)

    # 同一批次的 target_*_before 每列都相同，取第一列即可
    snapshot = records[0]
    target.product_total_amount = snapshot.target_product_total_before
    target.paid_amount = snapshot.target_paid_amount_before
    target.status = snapshot.target_status_before
    order_merge_repository.mark_batch_unmerged(db, records, now)
    order_repository.create_status_history(
        db,
        target.id,
        target.status,
        note="已拆回 " + "、".join(restored_numbers),
    )

    request.status = CancellationStatus.APPROVED
    request.response_note = normalize_optional_text(response_note)
    request.processed_at = now

    notification_service.notify_order_event(
        db,
        user_id=target.user_id,
        order_id=target.id,
        title="取消合併申請已核准",
        message=(
            f"團主已將訂單 {target.order_number} 拆回合併前的狀態，"
            f"{'、'.join(restored_numbers)} 已恢復顯示，請分別確認各張訂單的狀態與金額。"
            + (f"\n團主備註：{request.response_note}" if request.response_note else "")
        ),
    )
    db.commit()
    db.refresh(request)
    return order_service.build_unmerge_summary(db, request)


def reject_unmerge(
    db: Session, profile: GroupLeaderProfile, request_id: uuid.UUID, response_note: str | None
) -> UnmergeRequestSummary:
    """拒絕拆單申請：訂單維持合併後的狀態，會員可再次提出（同取消申請的做法）。"""
    request, target = _load_owned_unmerge_request(db, profile, request_id)
    if request.status != CancellationStatus.PENDING:
        raise AppError(409, "UNMERGE_REQUEST_ALREADY_PROCESSED", "此取消合併申請已被處理。")

    note = normalize_optional_text(response_note)
    if note is None:
        raise AppError(422, "VALIDATION_ERROR", "拒絕取消合併時必須填寫原因。")

    request.status = CancellationStatus.REJECTED
    request.response_note = note
    request.processed_at = datetime.now(timezone.utc)

    notification_service.notify_order_event(
        db,
        user_id=target.user_id,
        order_id=target.id,
        title="取消合併申請未通過",
        message=(
            f"團主未通過訂單 {target.order_number} 的取消合併申請。\n"
            f"團主說明：{note}\n如仍有疑問請直接聯絡團主。"
        ),
    )
    db.commit()
    db.refresh(request)
    return order_service.build_unmerge_summary(db, request)


def _transition(
    db: Session,
    profile: GroupLeaderProfile,
    order_id: uuid.UUID,
    *,
    from_status: OrderStatus,
    to_status: OrderStatus,
    note: str | None = None,
) -> GroupOrder:
    order = _load_owned_order(db, profile, order_id, for_update=True)
    if order.status != from_status:
        raise AppError(
            409,
            "ORDER_STATUS_CONFLICT",
            "訂單狀態已變更，請重新載入資料。",
            {"current_status": order.status.value},
        )
    order.status = to_status
    # 進到已付款代表全額收齊；合併過的訂單原本只收了一部分，這裡要補齊，
    # 否則畫面會出現「已付款」卻還顯示待收金額的矛盾。
    if to_status == OrderStatus.PAID:
        order.paid_amount = order.product_total_amount
    order_repository.create_status_history(db, order.id, to_status, note)
    return order


def accept_order(db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID) -> GroupOrder:
    """依 Business Rules §21.3：pending_confirmation -> pending_payment，並建立會員通知。"""
    order = _transition(
        db,
        profile,
        order_id,
        from_status=OrderStatus.PENDING_CONFIRMATION,
        to_status=OrderStatus.PENDING_PAYMENT,
    )
    notification_service.notify_order_event(
        db,
        user_id=order.user_id,
        order_id=order.id,
        title="訂單已受理",
        message=f"你的訂單 {order.order_number} 已受理，請留意付款通知。",
    )
    db.commit()
    db.refresh(order)
    return order


def reject_order(
    db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID, reason: str
) -> GroupOrder:
    """依 Business Rules §21.4：pending_confirmation -> rejected，拒絕原因必填且不可修改。"""
    normalized_reason = normalize_optional_text(reason)
    if not normalized_reason:
        raise AppError(422, "ORDER_REJECTION_REASON_REQUIRED", "請填寫拒絕原因。")

    order = _transition(
        db,
        profile,
        order_id,
        from_status=OrderStatus.PENDING_CONFIRMATION,
        to_status=OrderStatus.REJECTED,
        note=normalized_reason,
    )
    order.rejection_reason = normalized_reason
    notification_service.notify_order_event(
        db,
        user_id=order.user_id,
        order_id=order.id,
        title="訂單已被拒絕",
        message=f"你的訂單 {order.order_number} 已被拒絕：{normalized_reason}",
    )
    db.commit()
    db.refresh(order)
    return order


def mark_paid(db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID) -> GroupOrder:
    order = _transition(
        db, profile, order_id, from_status=OrderStatus.PENDING_PAYMENT, to_status=OrderStatus.PAID
    )
    db.commit()
    db.refresh(order)
    return order


def mark_shipped(db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID) -> GroupOrder:
    order = _transition(
        db, profile, order_id, from_status=OrderStatus.PAID, to_status=OrderStatus.SHIPPED
    )
    notification_service.notify_order_event(
        db,
        user_id=order.user_id,
        order_id=order.id,
        title="訂單已出貨",
        message=f"你的訂單 {order.order_number} 已由團主出貨，收到商品後請與團主確認完成。",
    )
    db.commit()
    db.refresh(order)
    return order


def mark_all_shipped(
    db: Session, profile: GroupLeaderProfile, group_buy_id: uuid.UUID
) -> dict:
    """一鍵將指定開團中所有「已付款」訂單標記為已出貨。

    只處理 paid 狀態的訂單；其餘狀態（待確認、待付款、已出貨、已完成、已拒絕、已取消）
    一律略過，並在回應中回報略過筆數，讓團主知道還有多少張沒進到可出貨狀態。
    """
    group_buy = group_buy_repository.get_by_id(db, group_buy_id)
    if group_buy is None or group_buy.group_leader_profile_id != profile.id:
        raise AppError(404, "GROUP_BUY_NOT_FOUND", "找不到指定的開團。")

    orders = order_repository.list_by_group_buy_and_status(
        db, group_buy_id, OrderStatus.PAID, for_update=True
    )
    pending_confirmation = order_repository.count_by_group_buy_and_status(
        db, group_buy_id, OrderStatus.PENDING_CONFIRMATION
    )
    pending_payment = order_repository.count_by_group_buy_and_status(
        db, group_buy_id, OrderStatus.PENDING_PAYMENT
    )

    for order in orders:
        order.status = OrderStatus.SHIPPED
        order_repository.create_status_history(db, order.id, OrderStatus.SHIPPED)
        notification_service.notify_order_event(
            db,
            user_id=order.user_id,
            order_id=order.id,
            title="訂單已出貨",
            message=f"你的訂單 {order.order_number} 已由團主出貨，收到商品後請與團主確認完成。",
        )

    db.commit()
    return {
        "shipped_count": len(orders),
        "skipped_pending_confirmation": pending_confirmation,
        "skipped_pending_payment": pending_payment,
    }


def complete_order(db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID) -> GroupOrder:
    order = _transition(
        db, profile, order_id, from_status=OrderStatus.SHIPPED, to_status=OrderStatus.COMPLETED
    )
    db.commit()
    db.refresh(order)
    return order


def _load_owned_cancellation_request(
    db: Session, profile: GroupLeaderProfile, request_id: uuid.UUID
) -> tuple[CancellationRequest, GroupOrder]:
    request = cancellation_repository.get_by_id(db, request_id, for_update=True)
    if request is None:
        raise AppError(404, "CANCELLATION_REQUEST_NOT_FOUND", "找不到指定的取消申請。")
    order = order_repository.get_by_id(db, request.order_id, for_update=True)
    group_buy = group_buy_repository.get_by_id(db, order.group_buy_id)
    if group_buy.group_leader_profile_id != profile.id:
        raise AppError(404, "CANCELLATION_REQUEST_NOT_FOUND", "找不到指定的取消申請。")
    return request, order


def approve_cancellation(
    db: Session, profile: GroupLeaderProfile, request_id: uuid.UUID, response_note: str | None
) -> CancellationRequestSummary:
    """依 Business Rules §22.6：核准前重新確認訂單仍可取消，並原子更新訂單狀態與通知。"""
    request, order = _load_owned_cancellation_request(db, profile, request_id)
    if request.status != CancellationStatus.PENDING:
        raise AppError(409, "CANCELLATION_REQUEST_ALREADY_PROCESSED", "此取消申請已被處理。")
    if order.status not in _CANCELLABLE_STATUSES:
        raise AppError(409, "CANCELLATION_NOT_ALLOWED", "訂單目前狀態已不可取消。")

    now = datetime.now(timezone.utc)
    request.status = CancellationStatus.APPROVED
    request.response_note = normalize_optional_text(response_note)
    request.processed_at = now
    order.status = OrderStatus.CANCELLED
    order_repository.create_status_history(
        db, order.id, OrderStatus.CANCELLED, request.response_note
    )

    notification_service.notify_order_event(
        db,
        user_id=order.user_id,
        order_id=order.id,
        title="取消申請已核准",
        message=f"你的訂單 {order.order_number} 取消申請已核准。",
    )
    db.commit()
    db.refresh(request)
    return _cancellation_to_summary(request)


def reject_cancellation(
    db: Session, profile: GroupLeaderProfile, request_id: uuid.UUID, response_note: str | None
) -> CancellationRequestSummary:
    """依 Business Rules §22.7：拒絕後訂單狀態維持原狀，會員可再次申請。"""
    request, _order = _load_owned_cancellation_request(db, profile, request_id)
    if request.status != CancellationStatus.PENDING:
        raise AppError(409, "CANCELLATION_REQUEST_ALREADY_PROCESSED", "此取消申請已被處理。")

    request.status = CancellationStatus.REJECTED
    request.response_note = normalize_optional_text(response_note)
    request.processed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(request)
    return _cancellation_to_summary(request)
