/** 訂單狀態的共用文案與流程定義（圖 07／08／09 共用）。 */

export const STATUS_LABELS = {
  pending_confirmation: "等待團主確認",
  pending_payment: "等待付款",
  paid: "已付款",
  shipped: "已出貨",
  completed: "已完成",
  rejected: "已拒絕",
  cancelled: "已取消",
};

/** 依 Business Rules §22.1：可申請取消的訂單狀態。 */
export const CANCELLABLE_STATUSES = ["pending_confirmation", "pending_payment", "paid"];

/** 正常流程的五個節點（rejected／cancelled 為終止狀態，不在流程上）。 */
export const TIMELINE_STEPS = [
  {
    key: "pending_confirmation",
    label: "等待團主確認",
    description: "訂單建立，等待團主確認",
    hint: "訂單已送出，請耐心等待團主確認。",
  },
  {
    key: "pending_payment",
    label: "等待付款",
    description: "團主已接受，等待您付款",
    hint: "請在團主提供的付款期限內完成付款，逾期訂單可能會被取消。",
  },
  {
    key: "paid",
    label: "已付款",
    description: "您已完成付款，等待團主出貨",
    hint: "已完成付款，等待團主出貨。",
  },
  {
    key: "shipped",
    label: "已出貨",
    description: "團主已出貨，等待您確認完成",
    hint: "團主已出貨，收到商品後請與團主確認完成。",
  },
  {
    key: "completed",
    label: "已完成",
    description: "訂單完成，交易結束",
    hint: "訂單已完成，感謝您的跟團。",
  },
];

/** 由狀態歷史取出各狀態「第一次發生」的時間。 */
export function firstOccurrenceMap(statusHistory) {
  const map = {};
  for (const entry of statusHistory ?? []) {
    if (!map[entry.status]) {
      map[entry.status] = entry.created_at;
    }
  }
  return map;
}

export function formatOrderDateTime(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}
