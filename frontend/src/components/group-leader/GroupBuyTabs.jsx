import { NavLink } from "react-router-dom";
import { ClipboardIcon, GearIcon, MegaphoneIcon } from "../common/icons.jsx";

/**
 * 單一開團底下的分頁導覽（依圖 22）。
 *
 * 依使用者 2026-07-29 裁決不放「訂單列表」；「團購公告」帶 group_buy_id，
 * 只顯示針對該團的公告。圖 23 開團設定頁共用同一列。
 */
export default function GroupBuyTabs({ groupBuyId }) {
  const tabs = [
    {
      to: `/group-leader/group-buys/${groupBuyId}/product-orders`,
      label: "商品訂購總覽",
      Icon: ClipboardIcon,
    },
    { to: `/group-leader/group-buys/${groupBuyId}`, label: "開團設定", Icon: GearIcon, end: true },
    {
      to: `/group-leader/announcements?group_buy_id=${groupBuyId}`,
      label: "團購公告",
      Icon: MegaphoneIcon,
      // 帶 query string 的路徑 NavLink 不會自動比對，公告頁不屬於本群組故不需高亮
      neverActive: true,
    },
  ];

  return (
    <nav className="gbt-tabs" aria-label="開團功能">
      {tabs.map((tab) => (
        <NavLink
          key={tab.label}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) =>
            `gbt-tab${!tab.neverActive && isActive ? " is-active" : ""}`
          }
        >
          <tab.Icon />
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
