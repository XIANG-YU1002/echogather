import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getGroupBuyProductOrders } from "../../api/groupLeaderGroupBuys.js";
import { resolveMediaUrl } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";
import GroupBuyTabs from "../../components/group-leader/GroupBuyTabs.jsx";
import { BagIcon, ClipboardIcon, UsersIcon } from "../../components/common/icons.jsx";

function formatDateTime(isoString) {
  const date = new Date(isoString);
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mi = String(date.getMinutes()).padStart(2, "0");
  return `${yyyy}/${mm}/${dd} ${hh}:${mi}`;
}

function MemberCell({ item }) {
  return (
    <span className="dash-applicant">
      {item.avatar_url ? (
        <img
          className="avatar-circle avatar-circle-sm"
          src={resolveMediaUrl(item.avatar_url)}
          alt=""
        />
      ) : (
        <span className="avatar-circle avatar-circle-sm" aria-hidden="true">
          {item.nickname?.[0]?.toUpperCase() ?? "?"}
        </span>
      )}
      {item.nickname}
    </span>
  );
}

/** 單一商品的訂購明細。有角色的商品才顯示「角色」欄（依使用者裁決）。 */
function ProductCard({ group }) {
  const hasCharacter = group.items.some((item) => item.chosen_character_name);

  return (
    <article className="po-card">
      <header className="po-card-head">
        <img
          className="po-card-image"
          src={resolveMediaUrl(group.product.primary_image_url)}
          alt=""
        />
        <h2 className="po-card-name">{group.product.name}</h2>
        <dl className="po-card-stats">
          <div>
            <dt>總訂購數量</dt>
            <dd>
              {group.total_quantity} <span className="po-unit">件</span>
            </dd>
          </div>
          <div>
            <dt>訂購成員數</dt>
            <dd>
              {group.member_count} <span className="po-unit">人</span>
            </dd>
          </div>
        </dl>
      </header>

      {group.items.length === 0 ? (
        <p className="po-card-empty">這項商品還沒有人訂購。</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>成員</th>
                {hasCharacter && <th>角色</th>}
                <th>數量</th>
                <th>訂單狀態</th>
                <th>提交時間</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {group.items.map((item) => (
                <tr key={`${item.order_id}-${item.chosen_character_name ?? "none"}`}>
                  <td>
                    <MemberCell item={item} />
                  </td>
                  {hasCharacter && <td>{item.chosen_character_name ?? "—"}</td>}
                  <td>{item.quantity}</td>
                  <td>
                    <StatusBadge domain="order" value={item.order_status} />
                  </td>
                  <td>{formatDateTime(item.submitted_at)}</td>
                  <td>
                    <Link
                      className="btn btn-secondary"
                      to={`/group-leader/orders/${item.order_id}`}
                    >
                      查看訂單
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}

export default function ProductOrdersPage() {
  const { groupBuyId } = useParams();
  const { token } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  function load() {
    setError(false);
    setData(null);
    getGroupBuyProductOrders(groupBuyId, token)
      .then((response) => setData(response.data))
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupBuyId]);

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (!data) {
    return <PageLoader />;
  }

  const roundLabel = `第 ${data.round_number} 團`;

  return (
    <>
      {/* 中間兩層都給實際去處：活動名稱帶搜尋看該活動的所有輪次，輪次連到開團設定。
          Breadcrumb 元件對沒有 to 的中間項會套用「目前位置」樣式，給了連結才不會
          出現多個深色項。 */}
      <Breadcrumb
        items={[
          { label: "我的開團", to: "/group-leader/group-buys" },
          {
            label: data.activity.name,
            to: `/group-leader/group-buys?keyword=${encodeURIComponent(data.activity.name)}`,
          },
          { label: roundLabel, to: `/group-leader/group-buys/${groupBuyId}` },
          { label: "商品訂購總覽" },
        ]}
      />

      <div className="page-header">
        <h1>商品訂購總覽</h1>
        <p className="helper-text">查看本團各商品的訂購狀況與成員訂單明細</p>
      </div>

      <section className="po-summary">
        <div className="po-summary-activity">
          <img
            className="po-summary-image"
            src={resolveMediaUrl(data.activity.image_url)}
            alt=""
          />
          <div>
            <h2 className="po-summary-name">
              {data.activity.name}
              <span
                className={`status-badge ${
                  data.status === "open" ? "status-badge-success" : "status-badge-neutral"
                }`}
              >
                {data.status === "open" ? "進行中" : "已結單"}
              </span>
            </h2>
            <p className="po-summary-round">{roundLabel}</p>
            <p className="po-summary-deadline">截止日期：{formatDateTime(data.deadline_at)}</p>
          </div>
        </div>

        <div className="po-summary-stats">
          <div className="po-summary-stat">
            <span className="dash-icon purple">
              <ClipboardIcon className="dash-icon-svg" />
            </span>
            <span className="stat-card-text">
              <span className="stat-card-label">總訂單數</span>
              <span className="stat-card-value">
                {data.total_order_count} <span className="po-unit">筆</span>
              </span>
            </span>
          </div>
          <div className="po-summary-stat">
            <span className="dash-icon blue">
              <BagIcon className="dash-icon-svg" />
            </span>
            <span className="stat-card-text">
              <span className="stat-card-label">總訂購數量</span>
              <span className="stat-card-value">
                {data.total_ordered_quantity} <span className="po-unit">件</span>
              </span>
            </span>
          </div>
        </div>
      </section>

      <GroupBuyTabs groupBuyId={groupBuyId} />

      {data.products.length === 0 ? (
        <EmptyState
          title="這個開團還沒有商品"
          description="請先到開團設定加入商品。"
          action={
            <Link className="btn btn-primary" to={`/group-leader/group-buys/${groupBuyId}`}>
              前往開團設定
            </Link>
          }
        />
      ) : (
        <div className="po-list">
          {data.products.map((group) => (
            <ProductCard key={group.group_buy_product_id} group={group} />
          ))}
        </div>
      )}
    </>
  );
}
