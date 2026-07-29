import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getGroupLeaderDashboard } from "../../api/groupLeaderProfile.js";
import { resolveMediaUrl } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import {
  BagIcon,
  CalendarIcon,
  ChartIcon,
  ClipboardIcon,
  CreditCardIcon,
  FileQuestionIcon,
  FlagIcon,
  GearIcon,
  HourglassIcon,
} from "../../components/common/icons.jsx";

// 統計卡：key -> 圖示與配色（依圖 20 的四張卡）
const STAT_META = {
  pending_orders: { Icon: ClipboardIcon, tone: "purple" },
  pending_cancellation_requests: { Icon: FileQuestionIcon, tone: "orange" },
  open_group_buys: { Icon: FlagIcon, tone: "blue" },
  upcoming_deadline_group_buys: { Icon: HourglassIcon, tone: "red" },
};

const PAYMENT_METHOD_LABELS = {
  bank_transfer: "匯款",
  cash_on_delivery: "貨到付款",
};

// 目前開團不分頁，資料一次全部載入，排序純前端處理
const SORT_OPTIONS = [
  { value: "deadline_asc", label: "依截止日期：最近優先" },
  { value: "deadline_desc", label: "依截止日期：最遠優先" },
];

/** 只顯示月/日與時間，省下年份的寬度讓統計欄位排得進同一排（完整日期見我的開團）。 */
function formatDeadline(isoString) {
  const date = new Date(isoString);
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mi = String(date.getMinutes()).padStart(2, "0");
  return `${mm}/${dd} ${hh}:${mi}`;
}

/** 一輪開團的統計與操作。 */
function GroupBuyRow({ groupBuy }) {
  return (
    <div className="gb-round">
      <div className="gb-round-head">
        <span className="gb-round-name">第 {groupBuy.round_number} 團</span>
        {groupBuy.is_upcoming_deadline ? (
          <span className="status-badge status-badge-danger">即將截止</span>
        ) : (
          <span className="status-badge status-badge-success">進行中</span>
        )}
      </div>

      <dl className="gb-round-stats">
        <div>
          <dt>
            <CalendarIcon />
            結單時間
          </dt>
          <dd>{formatDeadline(groupBuy.deadline_at)}</dd>
        </div>
        <div>
          <dt>
            <CreditCardIcon />
            付款方式
          </dt>
          <dd>{PAYMENT_METHOD_LABELS[groupBuy.payment_method] ?? groupBuy.payment_method}</dd>
        </div>
        <div>
          <dt>
            <ClipboardIcon />
            訂單數
          </dt>
          <dd>{groupBuy.order_count}</dd>
        </div>
        <div>
          <dt>
            <BagIcon />
            商品數量
          </dt>
          <dd>{groupBuy.ordered_quantity}</dd>
        </div>
        <div>
          <dt>
            <HourglassIcon />
            待處理
          </dt>
          <dd className={groupBuy.pending_order_count > 0 ? "gb-round-pending" : undefined}>
            {groupBuy.pending_order_count}
          </dd>
        </div>
      </dl>

      <div className="gb-round-actions">
        <Link
          className="btn btn-secondary"
          to={`/group-leader/group-buys/${groupBuy.id}/product-orders`}
        >
          <ChartIcon />
          查看訂購總覽
        </Link>
        <Link className="btn btn-primary" to={`/group-leader/group-buys/${groupBuy.id}`}>
          <GearIcon />
          管理開團
        </Link>
      </div>
    </div>
  );
}

/** 依活動分組的開團清單，「目前開團」與「已結單」共用。 */
function ActivityGroupList({ groups }) {
  return (
    <div className="gb-activity-list">
      {groups.map((group) => (
        <article key={group.activity_id} className="gb-activity-card">
          <div className="gb-activity-info">
            <img
              className="gb-activity-image"
              src={resolveMediaUrl(group.activity_image_url)}
              alt=""
            />
            <div>
              <h3 className="gb-activity-name">{group.activity_name}</h3>
              <span
                className={`status-badge ${
                  group.activity_status === "open"
                    ? "status-badge-success"
                    : "status-badge-neutral"
                }`}
              >
                {group.activity_status === "open" ? "進行中" : "已結束"}
              </span>
            </div>
          </div>
          <div className="gb-round-list">
            {group.group_buys.map((groupBuy) => (
              <GroupBuyRow key={groupBuy.id} groupBuy={groupBuy} />
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState(false);
  const [sort, setSort] = useState("deadline_asc");

  function load() {
    setError(false);
    setDashboard(null);
    getGroupLeaderDashboard(token)
      .then((response) => setDashboard(response.data))
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 後端已依最早截止排序，這裡只在使用者選「最遠優先」時反轉。
  // 每個活動以其最早截止的那一輪作為排序依據。
  const activityGroups = useMemo(() => {
    const groups = dashboard?.current_group_buys ?? [];
    if (sort === "deadline_asc") {
      return groups;
    }
    return [...groups].reverse();
  }, [dashboard, sort]);

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (!dashboard) {
    return <PageLoader />;
  }

  return (
    <>
      <div className="page-header">
        <h1>團主儀表板</h1>
        <p className="helper-text">歡迎回來，團主大人！以下是您目前開團的總覽資訊。</p>
      </div>

      <div className="stat-grid">
        {dashboard.cards.map((card) => {
          const meta = STAT_META[card.key] ?? { Icon: ClipboardIcon, tone: "purple" };
          const { Icon } = meta;
          return (
            <Link key={card.key} to={card.target_url} className="stat-card stat-card--icon">
              <span className={`dash-icon ${meta.tone}`}>
                <Icon className="dash-icon-svg" />
              </span>
              <span className="stat-card-text">
                <span className="stat-card-label">{card.label}</span>
                <span className="stat-card-value">{card.count}</span>
              </span>
            </Link>
          );
        })}
      </div>

      <section className="dash-section">
        <div className="dash-section-head">
          <div>
            <h2>目前開團</h2>
            <p className="helper-text" style={{ margin: "0.15rem 0 0" }}>
              依活動分類檢視您目前進行中的開團
            </p>
          </div>
          {activityGroups.length > 0 && (
            <label className="gb-sort">
              <select
                aria-label="排序方式"
                value={sort}
                onChange={(event) => setSort(event.target.value)}
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>

        {activityGroups.length === 0 ? (
          <div className="dash-empty">
            目前沒有進行中的開團。
            <div style={{ marginTop: "0.85rem" }}>
              <Link className="btn btn-primary" to="/group-leader/group-buys/new">
                建立開團
              </Link>
            </div>
          </div>
        ) : (
          <ActivityGroupList groups={activityGroups} />
        )}
      </section>
    </>
  );
}
