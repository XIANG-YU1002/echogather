import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listGroupLeaders } from "../api/groupLeaders.js";
import { resolveMediaUrl } from "../api/client.js";
import Breadcrumb from "../components/common/Breadcrumb.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import PageLoader from "../components/common/PageLoader.jsx";
import Pagination from "../components/common/Pagination.jsx";
import {
  BagIcon,
  CalendarIcon,
  ClipboardIcon,
  DiscordIcon,
  FacebookIcon,
  LineIcon,
  SearchIcon,
} from "../components/common/icons.jsx";

// 依圖 12：一頁 5 位團主
const PAGE_SIZE = 5;

const SORT_OPTIONS = [
  { value: "created_desc", label: "依加入時間（最新）" },
  { value: "created_asc", label: "依加入時間（最早）" },
  { value: "group_buy_desc", label: "目前開團數（多 → 少）" },
  { value: "completed_order_desc", label: "完成訂單數（多 → 少）" },
];

const CONTACTS = [
  { key: "facebook", label: "Facebook", icon: FacebookIcon },
  { key: "discord", label: "Discord", icon: DiscordIcon },
  { key: "line", label: "LINE", icon: LineIcon },
];

function formatJoinDate(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/**
 * Facebook 欄位存的是網址（group_leader_profile.facebook_url），能判定為網址時
 * 顯示成以團主名稱為文字的超連結；判定不出來就照團主填寫的內容原樣顯示。
 */
function facebookHref(value) {
  if (!value) return null;
  const trimmed = value.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (/^(www\.)?facebook\.com\//i.test(trimmed)) return `https://${trimmed}`;
  return null;
}

function ContactCell({ contact, profile }) {
  const value = profile.public_contacts[contact.key];
  const Icon = contact.icon;
  const href = contact.key === "facebook" ? facebookHref(value) : null;

  return (
    <div className="ldr-contact">
      <span className="ldr-contact-icon">
        <Icon />
      </span>
      <div className="ldr-contact-text">
        <span className="ldr-contact-label">{contact.label}</span>
        {!value ? (
          <span className="ldr-contact-value ldr-contact-empty">未填寫</span>
        ) : href ? (
          <a
            className="ldr-contact-value ldr-contact-link"
            href={href}
            target="_blank"
            rel="noreferrer noopener"
          >
            {profile.display_name}
          </a>
        ) : (
          <span className="ldr-contact-value">{value}</span>
        )}
      </div>
    </div>
  );
}

export default function GroupLeaderListPage() {
  const [keyword, setKeyword] = useState("");
  const [keywordInput, setKeywordInput] = useState("");
  const [sort, setSort] = useState("created_desc");
  const [page, setPage] = useState(1);
  const [profiles, setProfiles] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [error, setError] = useState(false);

  function load() {
    setError(false);
    setProfiles(null);
    listGroupLeaders({ keyword: keyword || undefined, page, pageSize: PAGE_SIZE, sort })
      .then((response) => {
        setProfiles(response.data);
        setPagination(response.pagination);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyword, page, sort]);

  function handleSearchSubmit(event) {
    event.preventDefault();
    setPage(1);
    setKeyword(keywordInput.trim());
  }

  return (
    <>
      <Breadcrumb items={[{ label: "首頁", to: "/" }, { label: "團主" }]} />

      <div className="ldr-head">
        <h1>團主列表</h1>
        <p>瀏覽值得信賴的團主，安心參與鳴潮周邊團購。</p>
      </div>

      <div className="ldr-toolbar">
        <form className="ldr-search" onSubmit={handleSearchSubmit}>
          <span className="ldr-search-icon">
            <SearchIcon />
          </span>
          <input
            type="search"
            placeholder="搜尋團主名稱"
            value={keywordInput}
            onChange={(event) => setKeywordInput(event.target.value)}
            aria-label="搜尋團主名稱"
          />
        </form>
        <select
          className="ldr-sort"
          value={sort}
          aria-label="排序方式"
          onChange={(event) => {
            setPage(1);
            setSort(event.target.value);
          }}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <ErrorState onRetry={load} />
      ) : profiles === null ? (
        <PageLoader />
      ) : profiles.length === 0 ? (
        <EmptyState title="沒有符合的團主。" />
      ) : (
        <>
          <div className="ldr-list">
            {profiles.map((profile) => (
              <article key={profile.id} className="ldr-card">
                {profile.avatar_url ? (
                  <img
                    className="ldr-avatar"
                    src={resolveMediaUrl(profile.avatar_url)}
                    alt=""
                    loading="lazy"
                  />
                ) : (
                  <div className="ldr-avatar ldr-avatar-fallback" aria-hidden="true">
                    {profile.display_name?.[0] ?? "?"}
                  </div>
                )}

                <div className="ldr-identity">
                  <h2 className="ldr-name">{profile.display_name}</h2>
                  {profile.introduction && <p className="ldr-intro">{profile.introduction}</p>}
                </div>

                <div className="ldr-panel">
                  <div className="ldr-stats">
                    <div className="ldr-stat">
                      <span className="ldr-stat-icon">
                        <CalendarIcon />
                      </span>
                      <div className="ldr-stat-text">
                        <span className="ldr-stat-label">成為團主時間</span>
                        <strong className="ldr-stat-value">
                          {formatJoinDate(profile.created_at)}
                        </strong>
                      </div>
                    </div>
                    <div className="ldr-stat">
                      <span className="ldr-stat-icon">
                        <BagIcon />
                      </span>
                      <div className="ldr-stat-text">
                        <span className="ldr-stat-label">目前開團數</span>
                        <strong className="ldr-stat-value">
                          {profile.statistics.group_buy_count}
                        </strong>
                      </div>
                    </div>
                    <div className="ldr-stat">
                      <span className="ldr-stat-icon">
                        <ClipboardIcon />
                      </span>
                      <div className="ldr-stat-text">
                        <span className="ldr-stat-label">完成訂單數</span>
                        <strong className="ldr-stat-value">
                          {profile.statistics.completed_order_count}
                        </strong>
                      </div>
                    </div>
                  </div>

                  <div className="ldr-contacts">
                    {CONTACTS.map((contact) => (
                      <ContactCell key={contact.key} contact={contact} profile={profile} />
                    ))}
                  </div>
                </div>

                <Link className="btn btn-secondary ldr-view" to={`/group-leaders/${profile.id}`}>
                  查看團主頁
                </Link>
              </article>
            ))}
          </div>
          <Pagination
            page={pagination.page}
            totalPages={pagination.total_pages}
            onPageChange={setPage}
          />
        </>
      )}
    </>
  );
}
