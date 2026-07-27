import { Link } from "react-router-dom";
import { resolveMediaUrl } from "../../api/client.js";

const PAYMENT_METHOD_LABELS = {
  bank_transfer: "匯款",
  cash_on_delivery: "取貨付款",
};

const UNAVAILABLE_REASON_LABELS = {
  closed: "已結單",
  expired: "已截止",
  activity_ended: "活動已結束",
  full: "已額滿",
};

function formatDeadline(isoString) {
  return new Date(isoString).toLocaleString("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Taipei",
  });
}

function LeaderCell({ leader }) {
  const initial = leader.display_name?.[0]?.toUpperCase() ?? "?";
  return (
    <Link to={`/group-leaders/${leader.id}`} className="compare-leader">
      {leader.avatar_url ? (
        <img className="avatar-circle avatar-circle-sm" src={resolveMediaUrl(leader.avatar_url)} alt="" />
      ) : (
        <span className="avatar-circle avatar-circle-sm" aria-hidden="true">
          {initial}
        </span>
      )}
      <span>{leader.display_name}</span>
    </Link>
  );
}

export default function GroupBuyCompareTable({ groupBuys, showFullGift = true }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>團主</th>
            <th>價格 (TWD)</th>
            <th>付款方式</th>
            <th>需二補</th>
            {showFullGift && <th>含滿贈</th>}
            <th>收團時間</th>
            <th>剩餘數量</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {groupBuys.map((groupBuy) => (
            <tr key={groupBuy.group_buy_product_id}>
              <td>
                <LeaderCell leader={groupBuy.group_leader} />
              </td>
              <td>
                <span className="compare-price">NT$ {groupBuy.unit_price}</span>
              </td>
              <td>
                {PAYMENT_METHOD_LABELS[groupBuy.payment_method]}
                {groupBuy.payment_method_note ? `（${groupBuy.payment_method_note}）` : ""}
              </td>
              <td>{groupBuy.requires_second_payment ? "是" : "否"}</td>
              {showFullGift && <td>{groupBuy.includes_full_gift ? "有" : "無"}</td>}
              <td>{formatDeadline(groupBuy.deadline_at)}</td>
              <td>
                {groupBuy.is_available ? (
                  <span className="remaining-ok">剩餘 {groupBuy.available_quantity}</span>
                ) : (
                  <span className="remaining-none">
                    {UNAVAILABLE_REASON_LABELS[groupBuy.effective_status] ?? "不可跟團"}
                  </span>
                )}
              </td>
              <td>
                <Link
                  className="btn btn-primary"
                  to={`/group-buys/${groupBuy.id}?product=${groupBuy.group_buy_product_id}`}
                >
                  查看開團詳情
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
