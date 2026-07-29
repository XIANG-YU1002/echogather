from typing import Any, Sequence


def envelope(data: Any) -> dict:
    return {"data": data}


def paginated_envelope(
    items: Sequence[Any],
    page: int,
    page_size: int,
    total_items: int,
    *,
    summary: Any = None,
) -> dict:
    """分頁回應。

    summary 供「列表與統計卡同頁」的畫面使用（例如圖 21 我的開團上方三張卡），
    避免前端為了幾個數字再打一次 API——Supabase 在 ap-south-1，每次往返約 700ms。
    未指定時回應形狀與原本完全相同。
    """
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
    response = {
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_previous": page > 1,
            "has_next": page < total_pages,
        },
    }
    if summary is not None:
        response["summary"] = summary
    return response
