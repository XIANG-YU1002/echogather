const STATUS_MAPS = {
  activity: {
    open: { label: "進行中", tone: "info" },
    ended: { label: "已結束", tone: "neutral" },
  },
  groupBuyEffective: {
    open: { label: "開放跟團", tone: "success" },
    closed: { label: "已結單", tone: "neutral" },
    expired: { label: "已截止", tone: "warning" },
    activity_ended: { label: "活動已結束", tone: "neutral" },
    full: { label: "已額滿", tone: "warning" },
  },
  order: {
    pending_confirmation: { label: "待團主確認", tone: "warning" },
    pending_payment: { label: "待付款", tone: "warning" },
    paid: { label: "已付款", tone: "info" },
    shipped: { label: "已出貨", tone: "info" },
    completed: { label: "已完成", tone: "success" },
    cancelled: { label: "已取消", tone: "neutral" },
    rejected: { label: "已拒絕", tone: "danger" },
    // 被併進另一張訂單的來源訂單。前後台的列表與詳情都不顯示這種訂單，
    // 這裡備著是為了狀態歷史等處不會露出原始英文值。
    merged: { label: "已合併", tone: "neutral" },
  },
  application: {
    pending: { label: "待審核", tone: "warning" },
    approved: { label: "已通過", tone: "success" },
    rejected: { label: "已拒絕", tone: "danger" },
  },
  announcementVisibility: {
    true: { label: "公開", tone: "info" },
    false: { label: "不公開", tone: "neutral" },
  },
  announcementScope: {
    leader_unfinished: { label: "團主整體", tone: "neutral" },
    group_buy_unfinished: { label: "特定開團", tone: "info" },
  },
};

export default function StatusBadge({ domain, value }) {
  const entry = STATUS_MAPS[domain]?.[value];
  if (!entry) {
    return <span className="status-badge status-badge-neutral">{String(value)}</span>;
  }
  return <span className={`status-badge status-badge-${entry.tone}`}>{entry.label}</span>;
}
