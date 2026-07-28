import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminApplications } from "../../api/adminGroupLeaderApplications.js";
import { resolveMediaUrl } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import ListFooter from "../../components/common/ListFooter.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";
import { useAutoRefresh } from "../../hooks/useAutoRefresh.js";
import {
  DiscordIcon,
  FacebookIcon,
  LineIcon,
  MailIcon,
  SearchIcon,
} from "../../components/common/icons.jsx";

/** 依圖 29：日期與時間分兩行顯示。 */
function formatDateParts(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return { date: isoString, time: "" };
  const pad = (n) => String(n).padStart(2, "0");
  return {
    date: `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())}`,
    time: `${pad(date.getHours())}:${pad(date.getMinutes())}`,
  };
}

// 以申請 UUID 前 8 碼組成好讀的申請編號
function applicationCode(id) {
  return `#${id.replace(/-/g, "").slice(0, 8).toUpperCase()}`;
}

/** 聯絡方式摘要：已填的平台配品牌圖示，Email 一律列出。 */
function contactSummary(user) {
  const items = [];
  if (user.line_contact) items.push({ key: "line", icon: LineIcon, value: user.line_contact });
  if (user.facebook_contact) {
    items.push({ key: "facebook", icon: FacebookIcon, value: user.facebook_contact });
  }
  if (user.discord_contact) {
    items.push({ key: "discord", icon: DiscordIcon, value: user.discord_contact });
  }
  items.push({ key: "email", icon: MailIcon, value: user.email, muted: true });
  return items;
}

export default function GroupLeaderApplicationListPage() {
  const { token } = useAuth();
  const [status, setStatus] = useState("pending");
  const [keyword, setKeyword] = useState("");
  const [keywordInput, setKeywordInput] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [applications, setApplications] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [error, setError] = useState(false);

  /** silent=true 供背景輪詢使用：不清空清單也不跳 loading，避免畫面閃動。 */
  function load({ silent = false } = {}) {
    if (!silent) {
      setError(false);
      setApplications(null);
    }
    return getAdminApplications(token, {
      status: status || undefined,
      keyword: keyword || undefined,
      page,
      pageSize,
    })
      .then((response) => {
        setApplications(response.data);
        setPagination(response.pagination);
        setError(false);
      })
      .catch(() => {
        // 背景刷新失敗不要把已顯示的清單換成錯誤畫面
        if (!silent) setError(true);
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, keyword, page, pageSize]);

  // 新申請進來時自動出現，不必手動重新整理
  useAutoRefresh(() => load({ silent: true }));

  function handleSearchSubmit(event) {
    event.preventDefault();
    setPage(1);
    setKeyword(keywordInput.trim());
  }

  return (
    <div className="admin-page">
      <div className="page-header">
        <h1>團主申請管理</h1>
      </div>

      <div className="admin-toolbar">
        <form className="search-input admin-toolbar-search" onSubmit={handleSearchSubmit} role="search">
          <input
            type="search"
            placeholder="搜尋會員暱稱或 Email"
            value={keywordInput}
            onChange={(event) => setKeywordInput(event.target.value)}
            aria-label="搜尋會員暱稱或 Email"
          />
          <button type="submit" className="search-input-icon-btn" aria-label="搜尋">
            <SearchIcon className="icon-search" />
          </button>
        </form>
        <select
          className="admin-toolbar-select"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
          aria-label="狀態篩選"
        >
          <option value="pending">待審核</option>
          <option value="approved">已核准</option>
          <option value="rejected">已拒絕</option>
          <option value="">全部狀態</option>
        </select>
      </div>

      <div className="admin-panel">
      {error ? (
        <ErrorState onRetry={load} />
      ) : applications === null ? (
        <PageLoader />
      ) : applications.length === 0 ? (
        <EmptyState title="沒有符合的申請。" />
      ) : (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>申請編號</th>
                  <th>會員暱稱</th>
                  <th>聯絡方式摘要</th>
                  <th>申請時間</th>
                  <th>狀態</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {applications.map((application) => (
                  <tr key={application.id}>
                    <td>{applicationCode(application.id)}</td>
                    <td>
                      <span className="dash-applicant">
                        {application.user.avatar_url ? (
                          <img className="avatar-circle avatar-circle-sm" src={resolveMediaUrl(application.user.avatar_url)} alt="" />
                        ) : (
                          <span className="avatar-circle avatar-circle-sm" aria-hidden="true">
                            {application.user.nickname?.[0]?.toUpperCase() ?? "?"}
                          </span>
                        )}
                        {application.user.nickname}
                      </span>
                    </td>
                    <td>
                      <span className="contact-summary">
                        {contactSummary(application.user).map((item) => {
                          const Icon = item.icon;
                          return (
                            <span
                              key={item.key}
                              className={`contact-summary-line${item.muted ? " muted" : ""}`}
                            >
                              <Icon />
                              {item.value}
                            </span>
                          );
                        })}
                      </span>
                    </td>
                    <td className="app-time">
                      <span>{formatDateParts(application.created_at).date}</span>
                      <span className="app-time-clock">
                        {formatDateParts(application.created_at).time}
                      </span>
                    </td>
                    <td>
                      <StatusBadge domain="application" value={application.status} />
                    </td>
                    <td>
                      <Link className="btn btn-secondary" to={`/admin/group-leader-applications/${application.id}`}>
                        查看審核
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ListFooter
            pagination={pagination}
            onPageChange={setPage}
            pageSize={pageSize}
            onPageSizeChange={(n) => {
              setPageSize(n);
              setPage(1);
            }}
          />
        </>
      )}
      </div>
    </div>
  );
}
