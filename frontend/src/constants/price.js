/**
 * 官方原價顯示格式（依圖 11：NT$ 680）。
 *
 * 後端 Money 序列化為固定兩位小數字串（"680.00"），周邊商品定價都是整數，
 * 因此小數為 0 時去掉尾數，並加上千分位。
 */
export function formatOfficialPrice(price, currency) {
  if (price === null || price === undefined || price === "") return null;

  const numeric = Number(price);
  if (Number.isNaN(numeric)) return `${currency ?? ""} ${price}`.trim();

  const amount = Number.isInteger(numeric)
    ? numeric.toLocaleString("en-US")
    : numeric.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  return currency === "TWD" || !currency ? `NT$ ${amount}` : `${currency} ${amount}`;
}
