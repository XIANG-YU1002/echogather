import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  getGroupLeaderAnnouncements,
  getGroupLeaderGroupBuys,
  getGroupLeaderProfile,
} from "../api/groupLeaders.js";
import { ApiError, resolveMediaUrl } from "../api/client.js";
import Breadcrumb from "../components/common/Breadcrumb.jsx";
import MediaImage from "../components/common/MediaImage.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import PageLoader from "../components/common/PageLoader.jsx";
import {
  BagIcon,
  CalendarIcon,
  ChevronRightIcon,
  ClipboardIcon,
  DiscordIcon,
  FacebookIcon,
  LineIcon,
  MegaphoneIcon,
  ShieldIcon,
  TagIcon,
} from "../components/common/icons.jsx";

const CONTACT_LINKS = [
  { key: "facebook", label: "Facebook", icon: FacebookIcon },
  { key: "discord", label: "Discord", icon: DiscordIcon },
  { key: "line", label: "LINE", icon: LineIcon },
];

function formatDate(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())}`;
}

function formatDeadline(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/**
 * Facebook 公開聯絡欄位存的是網址；能判定為網址時做成超連結，
 * 連結文字用團主名稱（與圖 12 團主列表頁一致）。
 */
function facebookHref(value) {
  if (!value) return null;
  const trimmed = value.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (/^(www\.)?facebook\.com\//i.test(trimmed)) return `https://${trimmed}`;
  return null;
}

/**
 * 把開團依「活動」合併：
 * - 只要該活動還有進行中的開團，整個活動歸入「開團中」
 * - 全部輪次都已結單的活動歸入「曾經開過團」，並依開團時間標記第幾團
 */
function groupByActivity(groupBuys) {
  const map = new Map();
  groupBuys.forEach((groupBuy) => {
    const activityId = groupBuy.activity.id;
    if (!map.has(activityId)) {
      map.set(activityId, { activity: groupBuy.activity, rounds: [] });
    }
    map.get(activityId).rounds.push(groupBuy);
  });

  const groups = [...map.values()].map((group) => {
    // 依開團建立時間排序，最早的是第 1 團
    const rounds = [...group.rounds].sort(
      (a, b) => new Date(a.created_at) - new Date(b.created_at),
    );
    const numbered = rounds.map((round, index) => ({ ...round, roundNumber: index + 1 }));
    return {
      activity: group.activity,
      rounds: numbered,
      openRound: numbered.find((round) => round.status === "open") ?? null,
    };
  });

  return {
    ongoing: groups.filter((group) => group.openRound),
    past: groups.filter((group) => !group.openRound),
  };
}

export default function GroupLeaderProfilePage() {
  const { groupLeaderId } = useParams();
  const [profile, setProfile] = useState(null);
  const [activityGroups, setActivityGroups] = useState({ ongoing: [], past: [] });
  const [announcements, setAnnouncements] = useState([]);
  const [error, setError] = useState(null);

  async function load() {
    setError(null);
    setProfile(null);
    try {
      // 不帶 status 取回全部開團，前端再依活動合併並分成進行中／已結束
      const [profileResponse, groupBuysResponse, announcementsResponse] = await Promise.all([
        getGroupLeaderProfile(groupLeaderId),
        getGroupLeaderGroupBuys(groupLeaderId, { pageSize: 100 }),
        getGroupLeaderAnnouncements(groupLeaderId),
      ]);
      setProfile(profileResponse.data);
      setAnnouncements(announcementsResponse.data);
      setActivityGroups(groupByActivity(groupBuysResponse.data));
    } catch (err) {
      setError(err);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupLeaderId]);

  if (error) {
    if (error instanceof ApiError && error.status === 404) {
      return (
        <ErrorState
          title="找不到此團主公開頁"
          description="此團主公開資料尚未完成，或頁面不存在。"
        />
      );
    }
    return <ErrorState onRetry={load} />;
  }

  if (!profile) {
    return <PageLoader />;
  }

  const stats = [
    { icon: CalendarIcon, label: "加入日期", value: formatDate(profile.created_at) },
    { icon: BagIcon, label: "開團數", value: profile.statistics.group_buy_count },
    { icon: ClipboardIcon, label: "已完成訂單", value: profile.statistics.completed_order_count },
  ];

  const filledContacts = CONTACT_LINKS.filter((contact) => profile.public_contacts[contact.key]);
  const { ongoing, past } = activityGroups;

  return (
    <>
      <Breadcrumb
        items={[
          { label: "首頁", to: "/" },
          { label: "團主", to: "/group-leaders" },
          { label: profile.display_name },
        ]}
      />

      <div className="glp-top">
        <div className="glp-banner">
          <div className="glp-banner-main">
            {profile.avatar_url ? (
              <img className="glp-avatar" src={resolveMediaUrl(profile.avatar_url)} alt="" />
            ) : (
              <span className="glp-avatar glp-avatar-fallback" aria-hidden="true">
                {profile.display_name?.[0] ?? "?"}
              </span>
            )}

            <div className="glp-banner-text">
              <h1>{profile.display_name}</h1>
              {profile.introduction && <p className="glp-intro">{profile.introduction}</p>}

              <div className="glp-stats">
                {stats.map((stat) => {
                  const Icon = stat.icon;
                  return (
                    <span key={stat.label} className="glp-stat">
                      <Icon />
                      <span className="glp-stat-label">{stat.label}</span>
                      <strong>{stat.value}</strong>
                    </span>
                  );
                })}
              </div>
            </div>
          </div>

          {filledContacts.length > 0 && (
            <div className="glp-contacts">
              <h2>聯絡方式</h2>
              <div className="glp-contact-list">
                {filledContacts.map((contact) => {
                  const Icon = contact.icon;
                  const value = profile.public_contacts[contact.key];
                  const href = contact.key === "facebook" ? facebookHref(value) : null;
                  return (
                    <span key={contact.key} className="glp-contact">
                      <Icon />
                      <span className="glp-contact-label">{contact.label}</span>
                      {/* 只有團主名稱這段是連結，整列不做成按鈕 */}
                      {href ? (
                        <a
                          className="glp-contact-link"
                          href={href}
                          target="_blank"
                          rel="noreferrer noopener"
                        >
                          {profile.display_name}
                        </a>
                      ) : (
                        <span className="glp-contact-value">{value}</span>
                      )}
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {profile.default_rules && (
          <div className="glp-rules">
            <h2>
              <ShieldIcon />
              預設團規
            </h2>
            {/* 依圖 06／08 既有決議：團主自己寫的團規原樣顯示，不自動加編號 */}
            <div className="glp-rules-text">{profile.default_rules}</div>
            <p className="glp-rules-note">
              此為團主平常的開團習慣，各開團的正式團規仍以該開團詳情頁與訂單快照為準。
            </p>
          </div>
        )}
      </div>

      <section className="glp-section">
        <div className="glp-section-head">
          <h2>
            <TagIcon />
            開團中的活動
          </h2>
        </div>
        {ongoing.length === 0 ? (
          <EmptyState title="目前沒有進行中的開團。" />
        ) : (
          <div className="glp-activity-grid">
            {ongoing.map((group) => (
              <Link
                key={group.activity.id}
                className="glp-activity"
                to={`/group-buys/${group.openRound.id}/products`}
              >
                <MediaImage
                  className="glp-activity-image"
                  src={group.activity.image_url}
                  alt={group.activity.name}
                  loading="lazy"
                />
                <div className="glp-activity-body">
                  <h3>{group.activity.name}</h3>
                  <span className="glp-activity-round">
                    {group.rounds.length > 1
                      ? `第 ${group.openRound.roundNumber} 團進行中`
                      : "進行中"}
                  </span>
                  <p className="glp-activity-deadline">
                    結團時間 {formatDeadline(group.openRound.deadline_at)}
                  </p>
                  <span className="glp-activity-cta">
                    查看接單商品
                    <ChevronRightIcon />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {past.length > 0 && (
        <section className="glp-section">
          <div className="glp-section-head">
            <h2>
              <ClipboardIcon />
              已結單的活動
            </h2>
          </div>
          <div className="glp-activity-grid">
            {past.map((group) => (
              <article key={group.activity.id} className="glp-activity glp-activity-past">
                <MediaImage
                  className="glp-activity-image"
                  src={group.activity.image_url}
                  alt={group.activity.name}
                  loading="lazy"
                />
                <div className="glp-activity-body">
                  <h3>{group.activity.name}</h3>
                  <span className="glp-activity-round">共 {group.rounds.length} 團・已結單</span>
                  {/* 同一活動的各輪合併在同一張卡，逐輪提供入口 */}
                  <ul className="glp-round-list">
                    {group.rounds.map((round) => (
                      <li key={round.id}>
                        <Link to={`/group-buys/${round.id}/products`}>
                          第 {round.roundNumber} 團
                          <span className="glp-round-date">
                            {formatDate(round.deadline_at)} 結單
                          </span>
                          <ChevronRightIcon />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {announcements.length > 0 && (
        <section className="glp-section">
          <div className="glp-section-head">
            <h2>
              <MegaphoneIcon />
              公開公告
            </h2>
          </div>
          <div className="glp-announcement-grid">
            {announcements.map((announcement) => (
              <article key={announcement.id} className="glp-announcement">
                <h3>{announcement.title}</h3>
                <div className="glp-announcement-content">{announcement.content}</div>
                <p className="glp-announcement-date">
                  <CalendarIcon />
                  {formatDate(announcement.published_at)}
                </p>
              </article>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
