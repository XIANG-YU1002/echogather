import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getMyApplication, submitApplication } from "../../api/groupLeaderApplications.js";
import { getMyProfile } from "../../api/users.js";
import { resolveMediaUrl } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import Alert from "../../components/common/Alert.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import Button from "../../components/common/Button.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";
import { useAutoRefresh } from "../../hooks/useAutoRefresh.js";
import {
  ArrowLeftIcon,
  CheckIcon,
  ClipboardIcon,
  DiscordIcon,
  FacebookIcon,
  InfoIcon,
  LineIcon,
  SendIcon,
  ShieldIcon,
} from "../../components/common/icons.jsx";

const STEPS = ["資格確認", "送出申請", "管理員審核", "完成團主資料", "開始開團"];

const CONTACT_FIELDS = [
  { key: "facebook_contact", label: "Facebook", icon: FacebookIcon },
  { key: "discord_contact", label: "Discord", icon: DiscordIcon },
  { key: "line_contact", label: "LINE", icon: LineIcon },
];

// 平台規範全文直接顯示於頁面（使用者提供），不外連到不存在的頁面
const PLATFORM_RULES = [
  "團主應提供正確的商品、價格、付款方式、截止時間及團購規則。",
  "開團後應依訂單送出順序處理訂單，不得任意調整會員順位。",
  "商品價格、付款方式與相關費用應清楚說明，不得刻意隱瞞額外費用。",
  "團主應妥善處理訂單確認、付款、出貨及取消申請。",
  "團主公開聯絡資訊需保持有效，方便團員聯繫。",
  "不得發布詐騙、違法、冒用或與團購無關的內容。",
  "若有重大異動，應及時透過公告通知受影響的團員。",
  "違反平台規範時，管理員得限制相關團主功能或進行必要處理。",
];

/** 目前進行到第幾步（0-based）。未申請時停在「資格確認」。 */
function stepIndexForStatus(status) {
  if (status === "pending") return 2;
  if (status === "approved") return 3;
  if (status === "rejected") return 1;
  return 0;
}

function formatDateTime(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** 橫向連線步驟指示器：已完成打勾、目前步驟橘框、未達成灰圓。 */
function StepIndicator({ activeIndex }) {
  return (
    <ol className="gla-steps">
      {STEPS.map((step, index) => {
        const state = index < activeIndex ? "done" : index === activeIndex ? "current" : "todo";
        return (
          <li key={step} className={`gla-step gla-step-${state}`}>
            <span className="gla-step-line gla-step-line-before" aria-hidden="true" />
            <span className="gla-step-dot">
              {state === "done" ? <CheckIcon /> : <span className="gla-step-inner" />}
            </span>
            <span className="gla-step-line gla-step-line-after" aria-hidden="true" />
            <span className="gla-step-label">{step}</span>
          </li>
        );
      })}
    </ol>
  );
}

function ContactSummary({ profile, showSetupLink }) {
  return (
    <ul className="gla-contacts">
      {CONTACT_FIELDS.map((contact) => {
        const Icon = contact.icon;
        const value = profile[contact.key];
        return (
          <li key={contact.key} className="gla-contact">
            <span className="gla-contact-head">
              <Icon />
              {contact.label}
            </span>
            <span className={`gla-contact-value${value ? "" : " gla-contact-empty"}`}>
              {value || "未設定"}
            </span>
            {value ? (
              <span className="gla-contact-tag">已連結</span>
            ) : (
              showSetupLink && (
                <Link className="btn btn-secondary gla-contact-btn" to="/profile">
                  前往設定
                </Link>
              )
            )}
          </li>
        );
      })}
    </ul>
  );
}

export default function GroupLeaderApplicationPage() {
  const { token, refreshSession } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [application, setApplication] = useState(undefined);
  const [error, setError] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  /** silent=true 供背景輪詢使用：不清空內容也不跳 loading。 */
  function load({ silent = false } = {}) {
    if (!silent) {
      setError(false);
      setProfile(null);
      setApplication(undefined);
    }
    return Promise.all([getMyProfile(token), getMyApplication(token)])
      .then(([profileResponse, applicationResponse]) => {
        setProfile(profileResponse.data);
        setApplication(applicationResponse.data);
        setError(false);
        return applicationResponse.data;
      })
      .catch(() => {
        if (!silent) setError(true);
        return undefined;
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 管理員審核完成後畫面自動更新。狀態一改變就要重新取得 session——
  // 核准後使用者變成團主，側邊欄的「團主申請」會換成「團主後台」。
  useAutoRefresh(async () => {
    const previousStatus = application?.status;
    const latest = await load({ silent: true });
    if (latest?.status && latest.status !== previousStatus) {
      await refreshSession();
    }
  }, { enabled: !submitting });

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      await submitApplication(token, { reason });
      await refreshSession();
      load();
    } catch (err) {
      setSubmitError(err.message ?? "送出申請時發生錯誤，請稍後再試。");
    } finally {
      setSubmitting(false);
    }
  }

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (!profile || application === undefined) {
    return <PageLoader />;
  }

  const hasContact = CONTACT_FIELDS.some((contact) => profile[contact.key]);
  const hasPendingApplication = application?.status === "pending";
  const canSubmit = hasContact && !hasPendingApplication && (!application || application.can_reapply);

  const avatar = profile.avatar_url ? (
    <img className="gla-avatar" src={resolveMediaUrl(profile.avatar_url)} alt="" />
  ) : (
    <span className="gla-avatar gla-avatar-fallback" aria-hidden="true">
      {profile.nickname?.[0]?.toUpperCase() ?? "?"}
    </span>
  );

  // ---- 圖 18：已送出或已通過的申請狀態頁 ----
  if (application && (application.status === "pending" || application.status === "approved")) {
    const approved = application.status === "approved";
    return (
      <>
        <Breadcrumb items={[{ label: "首頁", to: "/" }, { label: "團主申請狀態" }]} />

        <div className="gla-head">
          <h1>團主申請狀態</h1>
          <p>查看您目前的申請進度與已提交資料。</p>
        </div>

        <div className="gla-panel gla-status-head">
          {avatar}
          <div className="gla-status-text">
            <h2>{approved ? "申請已通過" : "申請已送出"}</h2>
            <p>
              {approved
                ? "恭喜！您的團主申請已通過審核，可以前往團主後台完成公開資料設定。"
                : "您的團主申請已成功送出，目前正在等待管理員審核。"}
            </p>
            <StatusBadge domain="application" value={application.status} />
          </div>
          <div className="gla-status-time">
            <span className="gla-label">申請時間</span>
            <strong>{formatDateTime(application.created_at)}</strong>
          </div>
        </div>

        <div className="gla-panel">
          <h2 className="gla-panel-title">申請進度</h2>
          <StepIndicator activeIndex={stepIndexForStatus(application.status)} />
        </div>

        <div className="gla-two-col">
          <div className="gla-panel">
            <h2 className="gla-panel-title">申請資料</h2>
            <dl className="gla-data">
              <dt>申請編號</dt>
              {/* 後端只有 UUID，沿用管理員申請列表頁的做法顯示前 8 碼 */}
              <dd className="gla-mono">{String(application.id).slice(0, 8)}</dd>
              <dt>會員暱稱</dt>
              <dd>{profile.nickname}</dd>
              <dt>Email</dt>
              <dd>{profile.email}</dd>
              <dt>目前狀態</dt>
              <dd>
                <StatusBadge domain="application" value={application.status} />
              </dd>
              <dt>申請原因</dt>
              <dd className={application.reason ? "gla-reason-text" : "gla-contact-empty"}>
                {application.reason || "未填寫"}
              </dd>
            </dl>
          </div>

          <div className="gla-panel">
            <h2 className="gla-panel-title">聯絡方式摘要</h2>
            <ContactSummary profile={profile} showSetupLink={false} />
            <p className="gla-tip">
              <InfoIcon />
              {approved
                ? "請前往團主後台完成公開名稱與公開聯絡方式設定。"
                : "審核期間無需重複送出申請。"}
            </p>
          </div>
        </div>

        <div className="gla-actions gla-actions-end">
          {approved ? (
            <Button onClick={() => navigate("/group-leader")}>前往團主後台</Button>
          ) : (
            <Button variant="secondary" onClick={() => navigate("/")}>
              返回首頁
            </Button>
          )}
        </div>
      </>
    );
  }

  // ---- 圖 17：尚未申請（或上次被拒可重新申請）的申請表單 ----
  return (
    <>
      <Breadcrumb items={[{ label: "首頁", to: "/" }, { label: "申請成為團主" }]} />

      <div className="gla-head">
        <h1>申請成為團主</h1>
        <p>通過審核後，你將完成團主資料並取得團主資格，即可開團、管理團購與發布公告。</p>
      </div>

      <StepIndicator activeIndex={stepIndexForStatus(application?.status)} />

      {application?.status === "rejected" && (
        <Alert type="info">您上一次的申請未通過審核，可以重新送出申請。</Alert>
      )}
      {submitError && <Alert type="error">{submitError}</Alert>}

      <div className="gla-two-col gla-form-layout">
        <div>
          <div className="gla-panel">
            <h2 className="gla-panel-title">資格確認</h2>
            <div className="gla-eligibility">
              <div className="gla-identity">
                {avatar}
                <div>
                  <div className="gla-identity-name">
                    {profile.nickname}
                    <span className="gla-role-tag">會員</span>
                  </div>
                  <div className="gla-identity-email">{profile.email}</div>
                </div>
              </div>
              <ul className="gla-checks">
                <li className="gla-check-ok">
                  <CheckIcon />
                  已登入會員帳號
                </li>
                <li className={hasContact ? "gla-check-ok" : "gla-check-fail"}>
                  <CheckIcon />
                  {hasContact
                    ? "已設定至少一項會員聯絡方式"
                    : "尚未設定聯絡方式，請先於下方補齊"}
                </li>
                <li className={hasPendingApplication ? "gla-check-fail" : "gla-check-ok"}>
                  <CheckIcon />
                  {hasPendingApplication
                    ? "目前已有待審核中的團主申請"
                    : "目前沒有待審核中的團主申請"}
                </li>
              </ul>
            </div>
          </div>

          <div className="gla-panel">
            <h2 className="gla-panel-title">會員聯絡方式</h2>
            <p className="gla-panel-lead">此聯絡方式將用於管理員聯繫與團務相關通知。</p>
            <ContactSummary profile={profile} showSetupLink />
          </div>

          <div className="gla-panel">
            <h2 className="gla-panel-title">
              申請原因
              <span className="gla-optional">選填</span>
            </h2>
            <p className="gla-panel-lead">
              可簡單說明開團經驗或想開團的商品類型，供管理員審核時參考。
            </p>
            <textarea
              className="gla-reason"
              rows={4}
              maxLength={1000}
              placeholder="例如：長期收集鳴潮周邊，想幫同好一起代購官方商品。"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
            <div className="gla-reason-count">{reason.length} / 1000</div>
          </div>

          <div className="gla-panel">
            <h2 className="gla-panel-title">申請確認</h2>
            <label className="gla-agree">
              <input
                type="checkbox"
                checked={agreed}
                onChange={(event) => setAgreed(event.target.checked)}
              />
              我已確認並會遵守平台規範
            </label>
          </div>
        </div>

        <div>
          <div className="gla-panel">
            <h2 className="gla-panel-title">
              <ClipboardIcon />
              申請說明
            </h2>
            <ul className="gla-notes">
              <li>管理員審核通過後才會取得團主資格。</li>
              <li>通過後需完成公開名稱與至少一項公開聯絡方式。</li>
              <li>完成團主資料後才能公開團主頁、開團與發布公告。</li>
            </ul>
          </div>

          <div className="gla-panel">
            <h2 className="gla-panel-title">平台規範</h2>
            <p className="gla-panel-lead">
              成為團主前請詳閱以下規範，取得團主資格後即受其約束。
            </p>
            <ol className="gla-rules gla-rules-plain">
              {PLATFORM_RULES.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ol>
          </div>

          <div className="gla-panel">
            <h2 className="gla-panel-title">
              <ShieldIcon />
              審核方式
            </h2>
            <p className="gla-panel-lead">
              由管理員人工審核，審核結果會以站內通知寄送給您，請留意通知中心。
            </p>
          </div>

          <div className="gla-panel">
            <h2 className="gla-panel-title">
              <InfoIcon />
              目前狀態
            </h2>
            <p className="gla-current-status">
              {application?.status === "rejected" ? "上次申請未通過" : "尚未送出申請"}
            </p>
            <p className="gla-panel-lead">完成資格確認並送出申請後，狀態將更新。</p>
          </div>
        </div>
      </div>

      <div className="gla-actions">
        <Button variant="secondary" onClick={() => navigate("/profile")}>
          <ArrowLeftIcon />
          返回個人資料
        </Button>
        <Button onClick={handleSubmit} loading={submitting} disabled={!agreed || !canSubmit}>
          <SendIcon />
          送出團主申請
        </Button>
      </div>
    </>
  );
}
