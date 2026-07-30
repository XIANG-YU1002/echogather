/**
 * Facebook 聯絡欄位存的是網址；能判定成網址時回傳可直接開啟的 href。
 *
 * 團主資料的 Facebook 由後端 is_facebook_url 驗證過，但訂單／開團上的值是
 * 下單當時的快照，也可能是舊資料，所以這裡仍然做判定而不是無條件當成連結。
 */
export function facebookHref(value) {
  if (!value) return null;
  const trimmed = value.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (/^(www\.)?facebook\.com\//i.test(trimmed)) return `https://${trimmed}`;
  return null;
}

/**
 * 聯絡方式的「值」顯示元件（使用者 2026-07-30 裁決：Facebook 一律用超連結）。
 *
 * Facebook 的值是一長串網址，直接印出來會撐破「標籤靠左、值靠右」的資訊列，
 * 把標籤壓成一個字一行（確認訂單頁、訂單詳情頁的「主要聯絡方式」都出現過）。
 * 因此 Facebook 顯示成以名稱為文字的超連結，Discord／LINE 照原樣顯示 ID。
 *
 * displayName 傳團主或會員的名稱；沒有名稱可用時退回「Facebook 頁面」。
 */
export default function ContactValue({ platform, value, displayName, className }) {
  const href = platform === "facebook" ? facebookHref(value) : null;

  if (!href) {
    return <span className={className}>{value}</span>;
  }

  return (
    <a className={className} href={href} target="_blank" rel="noreferrer noopener">
      {displayName || "Facebook 頁面"}
    </a>
  );
}
