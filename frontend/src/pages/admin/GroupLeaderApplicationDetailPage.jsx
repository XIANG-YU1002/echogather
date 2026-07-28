import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  approveAdminApplication,
  getAdminApplicationDetail,
  rejectAdminApplication,
} from "../../api/adminGroupLeaderApplications.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError, resolveMediaUrl } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";
import { useAutoRefresh } from "../../hooks/useAutoRefresh.js";
import {
  CheckCircleIcon,
  CheckIcon,
  ClipboardIcon,
  DiscordIcon,
  FacebookIcon,
  LineIcon,
  MailIcon,
} from "../../components/common/icons.jsx";

const CONTACT_FIELDS = [
  { key: "line_contact", label: "LINE", icon: LineIcon },
  { key: "discord_contact", label: "Discord", icon: DiscordIcon },
  { key: "facebook_contact", label: "Facebook", icon: FacebookIcon },
];

function formatDateTime(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function applicationCode(id) {
  return `#${String(id).replace(/-/g, "").slice(0, 8).toUpperCase()}`;
}

export default function GroupLeaderApplicationDetailPage() {
  const { applicationId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();

  const [application, setApplication] = useState(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [confirming, setConfirming] = useState(null);

  /** silent=true 供背景輪詢使用：不清空內容也不跳 loading。 */
  function load({ silent = false } = {}) {
    if (!silent) {
      setError(false);
      setApplication(null);
    }
    return getAdminApplicationDetail(applicationId, token)
      .then((response) => {
        setApplication(response.data);
        setError(false);
      })
      .catch(() => {
        if (!silent) setError(true);
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applicationId]);

  // 若這筆申請已被其他管理員審核，畫面會跟著更新（審核按鈕自動消失）
  useAutoRefresh(() => load({ silent: true }), { enabled: !confirming && !busy });

  async function runReview(action) {
    setBusy(true);
    setActionError(null);
    setConfirming(null);
    try {
      if (action === "approve") {
        await approveAdminApplication(applicationId, token);
      } else {
        await rejectAdminApplication(applicationId, token);
      }
      navigate("/admin/group-leader-applications", { replace: true });
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "審核時發生錯誤，請稍後再試。");
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (!application) {
    return <PageLoader />;
  }

  const { user } = application;
  const isPending = application.status === "pending";
  const filledContacts = CONTACT_FIELDS.filter((contact) => user[contact.key]);

  // 審核重點只列出系統真的查得到的事實（平台沒有帳號停權／異常紀錄機制）
  const reviewPoints = [
    {
      ok: filledContacts.length > 0,
      title: filledContacts.length > 0 ? "聯絡方式已提供" : "尚未提供聯絡方式",
      detail:
        filledContacts.length > 0
          ? `已提供 ${filledContacts.map((c) => c.label).join("、")} 聯絡方式。`
          : "此會員尚未填寫任何外部聯絡方式，核准後將無法聯繫。",
    },
    {
      ok: isPending,
      title: isPending ? "尚未有其他待審核申請" : "此申請已完成審核",
      detail: isPending
        ? "同一會員同時只能有一筆待審核申請，此為目前唯一待審件。"
        : `審核時間：${application.reviewed_at ? formatDateTime(application.reviewed_at) : "—"}`,
    },
    {
      ok: isPending,
      title: isPending ? "尚未具有團主資格" : "已完成資格處理",
      detail: isPending
        ? "系統查無團主資格紀錄，可進行審核。"
        : "此會員的團主資格已依審核結果處理。",
    },
  ];

  return (
    <>
      <div className="page-header">
        <h1>團主申請詳情</h1>
      </div>

      <nav className="adm-crumb" aria-label="麵包屑">
        <Link to="/admin/group-leader-applications">團主申請</Link>
        <span aria-hidden="true">›</span>
        <span>申請詳情</span>
      </nav>

      <div className="admin-panel adm-app-head">
        {user.avatar_url ? (
          <img className="adm-app-avatar" src={resolveMediaUrl(user.avatar_url)} alt="" />
        ) : (
          <span className="adm-app-avatar adm-app-avatar-fallback" aria-hidden="true">
            {user.nickname?.[0]?.toUpperCase() ?? "?"}
          </span>
        )}

        <div className="adm-app-identity">
          <span className="adm-app-label">會員暱稱</span>
          <strong className="adm-app-name">{user.nickname}</strong>
          <span className="adm-app-label">Email</span>
          <span className="adm-app-email">{user.email}</span>
        </div>

        <div className="adm-app-meta">
          <span className="adm-app-label">申請編號</span>
          <strong className="adm-app-code">{applicationCode(application.id)}</strong>
          <span className="adm-app-label">申請時間</span>
          <strong>{formatDateTime(application.created_at)}</strong>
        </div>

        <div className="adm-app-contacts">
          <span className="adm-app-label">狀態</span>
          <StatusBadge domain="application" value={application.status} />
          <span className="adm-app-label adm-app-label-gap">會員聯絡方式</span>
          <ul>
            {CONTACT_FIELDS.map((contact) => {
              const Icon = contact.icon;
              const value = user[contact.key];
              return (
                <li key={contact.key}>
                  <Icon />
                  <span className="adm-app-contact-label">{contact.label}</span>
                  <span className={value ? "" : "adm-app-contact-empty"}>
                    {value || "未設定"}
                  </span>
                </li>
              );
            })}
            <li>
              <MailIcon />
              <span className="adm-app-contact-label">Email</span>
              <span>{user.email}</span>
            </li>
          </ul>
        </div>
      </div>

      {actionError && <Alert type="error">{actionError}</Alert>}

      <div className="adm-app-body">
        <div className="admin-panel">
          <h2 className="adm-app-section">
            申請說明
            <span className="gla-optional">選填</span>
          </h2>
          {application.reason ? (
            <p className="adm-app-reason">{application.reason}</p>
          ) : (
            <div className="adm-app-reason-empty">
              <ClipboardIcon />
              此申請未提供額外說明。
            </div>
          )}
        </div>

        <div className="admin-panel">
          <h2 className="adm-app-section">審核重點</h2>
          <ul className="adm-app-points">
            {reviewPoints.map((point) => (
              <li key={point.title} className={point.ok ? "ok" : "warn"}>
                <span className="adm-app-point-icon">
                  {point.ok ? <CheckCircleIcon /> : <CheckIcon />}
                </span>
                <div>
                  <strong>{point.title}</strong>
                  <p>{point.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* 警告與操作另成一列，只占右半邊，讓上方兩張卡片維持等高 */}
        {isPending && (
          <div className="adm-app-tail">
            <p className="adm-app-warning">
              通過後，會員需完成團主公開資料，才能公開團主頁與建立開團。
            </p>
            <div className="adm-app-actions">
              <Button loading={busy} onClick={() => setConfirming("approve")}>
                <CheckIcon />
                核准申請
              </Button>
              <Button variant="danger" loading={busy} onClick={() => setConfirming("reject")}>
                拒絕申請
              </Button>
            </div>
          </div>
        )}
      </div>

      {confirming && (
        <ConfirmModal
          title={confirming === "approve" ? "核准申請" : "拒絕申請"}
          message={
            confirming === "approve"
              ? `確定要核准「${user.nickname}」的團主申請嗎？核准後會立即建立團主資料並通知申請人。`
              : `確定要拒絕「${user.nickname}」的團主申請嗎？拒絕後該會員可以重新提出申請。`
          }
          confirmLabel={confirming === "approve" ? "核准" : "拒絕"}
          cancelLabel="取消"
          danger={confirming === "reject"}
          onCancel={() => setConfirming(null)}
          onConfirm={() => runReview(confirming)}
        />
      )}
    </>
  );
}
