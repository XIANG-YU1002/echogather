import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getMyGroupBuys } from "../../api/groupLeaderGroupBuys.js";
import { resolveMediaUrl } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import Pagination from "../../components/common/Pagination.jsx";
import {
  ChartIcon,
  FlagIcon,
  FolderIcon,
  GearIcon,
  HourglassIcon,
  PlusCircleIcon,
  SearchIcon,
} from "../../components/common/icons.jsx";

const TABS = [
  { value: undefined, label: "全部" },
  { value: "open", label: "進行中" },
  { value: "closed", label: "已結單" },
];

// 上方三張統計卡。summary 固定統計全部開團，不隨篩選變動。
const SUMMARY_CARDS = [
  { key: "total", label: "全部", Icon: FolderIcon, tone: "purple" },
  { key: "open", label: "進行中", Icon: FlagIcon, tone: "blue" },
  { key: "closed", label: "已結單", Icon: HourglassIcon, tone: "orange" },
];

// 參考圖寫「活動時間」，但 activity 沒有起訖日期欄位，改以開團建立時間排序
const SORT_OPTIONS = [
  { value: "created_desc", label: "建立時間：最新優先" },
  { value: "created_asc", label: "建立時間：最舊優先" },
];

const PAGE_SIZE_OPTIONS = [10, 20, 50];

function formatDeadline(isoString) {
  const date = new Date(isoString);
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mi = String(date.getMinutes()).padStart(2, "0");
  return `${yyyy}/${mm}/${dd} ${hh}:${mi}`;
}

export default function GroupBuyListPage() {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  // 篩選條件以網址為單一來源（docs/03 §23a）：原本只取初始值、之後由元件狀態管理，
  // 導致點左側選單回到 /group-leader/group-buys（無 query）時搜尋殘留，
  // 得離開頁面或 F5 才清得掉。也讓其他頁面能帶搜尋連進來（例如圖 22 麵包屑的活動名稱）。
  const status = searchParams.get("status") ?? undefined;
  const keyword = searchParams.get("keyword") ?? "";

  // 搜尋框的未送出輸入值；keyword 才是實際條件，否則每打一個字就查一次 API
  const [searchInput, setSearchInput] = useState(keyword);
  const [sort, setSort] = useState("created_desc");
  const [page, setPage] = useState(1);
  // 依圖 21 預設每頁 10 筆；卡片列表比表格佔空間，一頁 20 張要捲很久
  const [pageSize, setPageSize] = useState(10);
  const [groupBuys, setGroupBuys] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(false);

  function load() {
    setError(false);
    setGroupBuys(null);
    getMyGroupBuys(token, { status, keyword, sort, page, pageSize })
      .then((response) => {
        setGroupBuys(response.data);
        setPagination(response.pagination);
        setSummary(response.summary);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, keyword, sort, page, pageSize]);

  // 網址的關鍵字被外部改掉時（點選單清空、瀏覽器上一頁），搜尋框要跟著更新
  useEffect(() => {
    setSearchInput(keyword);
  }, [keyword]);

  // 網址上的篩選一改就回第一頁，否則在第 3 頁切換篩選會看到空白清單
  useEffect(() => {
    setPage(1);
  }, [status, keyword]);

  /** 更新網址上的篩選參數；值為空即移除該參數。 */
  function updateParams(changes) {
    const params = new URLSearchParams(searchParams);
    Object.entries(changes).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
    });
    setSearchParams(params, { replace: true });
  }

  // 排序與每頁筆數不是篩選條件，維持元件狀態；改動時同樣回第一頁
  function changeFilter(setter) {
    return (value) => {
      setter(value);
      setPage(1);
    };
  }

  function handleSearch(event) {
    event.preventDefault();
    updateParams({ keyword: searchInput.trim() });
  }

  return (
    <>
      <div className="page-header gbl-header">
        <div>
          <h1>我的開團</h1>
          <p className="helper-text">管理您發起的所有開團活動</p>
        </div>
        <Link className="btn btn-primary gbl-create" to="/group-leader/group-buys/new">
          <PlusCircleIcon />
          建立開團
        </Link>
      </div>

      {summary && (
        <div className="stat-grid">
          {SUMMARY_CARDS.map((card) => (
            <div key={card.key} className="stat-card stat-card--icon">
              <span className={`dash-icon ${card.tone}`}>
                <card.Icon className="dash-icon-svg" />
              </span>
              <span className="stat-card-text">
                <span className="stat-card-label">{card.label}</span>
                <span className="stat-card-value">{summary[card.key]}</span>
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="gbl-toolbar">
        <div className="gbl-tabs">
          {TABS.map((tab) => (
            <button
              key={tab.label}
              type="button"
              className={`gbl-tab${status === tab.value ? " is-active" : ""}`}
              onClick={() => updateParams({ status: tab.value })}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <form className="search-input gbl-search" onSubmit={handleSearch} role="search">
          <input
            type="search"
            placeholder="搜尋活動名稱"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            aria-label="搜尋活動名稱"
          />
          <button type="submit" className="search-input-icon-btn" aria-label="搜尋">
            <SearchIcon className="icon-search" />
          </button>
        </form>

        <label className="gb-sort">
          <select
            aria-label="排序方式"
            value={sort}
            onChange={(event) => changeFilter(setSort)(event.target.value)}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? (
        <ErrorState onRetry={load} />
      ) : groupBuys === null ? (
        <PageLoader />
      ) : groupBuys.length === 0 ? (
        <EmptyState
          title={keyword ? "找不到符合的開團" : "目前沒有開團紀錄。"}
          description={keyword ? `沒有活動名稱包含「${keyword}」的開團。` : undefined}
          action={
            keyword ? undefined : (
              <Link className="btn btn-primary" to="/group-leader/group-buys/new">
                建立開團
              </Link>
            )
          }
        />
      ) : (
        <>
          <div className="gbl-list">
            {groupBuys.map((groupBuy) => (
              <article key={groupBuy.id} className="gbl-card">
                <img
                  className="gbl-card-image"
                  src={resolveMediaUrl(groupBuy.activity.image_url)}
                  alt=""
                />

                <div className="gbl-card-main">
                  <h2 className="gbl-card-title">
                    {groupBuy.activity.name}
                    <span className="gbl-card-round">｜第 {groupBuy.round_number} 團</span>
                    <span
                      className={`status-badge ${
                        groupBuy.status === "open"
                          ? "status-badge-success"
                          : "status-badge-neutral"
                      }`}
                    >
                      {groupBuy.status === "open" ? "進行中" : "已結單"}
                    </span>
                  </h2>
                  <p className="gbl-card-deadline">
                    截止日期：{formatDeadline(groupBuy.deadline_at)}
                  </p>
                </div>

                <dl className="gbl-card-stats">
                  <div>
                    <dt>訂單數</dt>
                    <dd>{groupBuy.order_count}</dd>
                  </div>
                  <div>
                    <dt>商品數</dt>
                    <dd>{groupBuy.ordered_quantity}</dd>
                  </div>
                </dl>

                <div className="gbl-card-actions">
                  <Link
                    className="btn btn-secondary"
                    to={`/group-leader/group-buys/${groupBuy.id}/product-orders`}
                  >
                    <ChartIcon />
                    查看訂購總覽
                  </Link>
                  <Link
                    className="btn btn-primary"
                    to={`/group-leader/group-buys/${groupBuy.id}`}
                  >
                    <GearIcon />
                    開團設定
                  </Link>
                </div>
              </article>
            ))}
          </div>

          <div className="gbl-footer">
            <Pagination
              page={pagination.page}
              totalPages={pagination.total_pages}
              onPageChange={setPage}
            />
            <label className="gbl-page-size">
              每頁顯示
              <select
                aria-label="每頁顯示筆數"
                value={pageSize}
                onChange={(event) => changeFilter(setPageSize)(Number(event.target.value))}
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
              筆
            </label>
          </div>
        </>
      )}
    </>
  );
}
