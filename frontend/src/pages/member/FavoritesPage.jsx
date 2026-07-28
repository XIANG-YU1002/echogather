import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getFavoriteProducts, removeFavorite } from "../../api/favorites.js";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import MediaImage from "../../components/common/MediaImage.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import Pagination from "../../components/common/Pagination.jsx";
import { BookmarkIcon, HeartIcon } from "../../components/common/icons.jsx";
import { formatOfficialPrice } from "../../constants/price.js";

// 依圖 11：一頁 4 欄 × 2 列
const PAGE_SIZE = 8;

const SORT_OPTIONS = [
  { value: "created_desc", label: "依收藏時間（最新）" },
  { value: "created_asc", label: "依收藏時間（最舊）" },
  { value: "name_asc", label: "商品名稱（A → Z）" },
  { value: "price_desc", label: "價格（高 → 低）" },
  { value: "price_asc", label: "價格（低 → 高）" },
];

export default function FavoritesPage() {
  const { token } = useAuth();
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("created_desc");
  const [items, setItems] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [error, setError] = useState(false);
  const [removingId, setRemovingId] = useState(null);

  /** silent=true 用於取消收藏後的重新整理，避免整頁跳回「載入中」。 */
  function load({ silent = false } = {}) {
    setError(false);
    if (!silent) setItems(null);
    return getFavoriteProducts(token, { page, pageSize: PAGE_SIZE, sort })
      .then((response) => {
        setItems(response.data);
        setPagination(response.pagination);
        return response;
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, sort]);

  async function handleRemove(productId) {
    setRemovingId(productId);
    try {
      await removeFavorite(productId, token);
      // 重新查詢而非只從本地陣列移除，總筆數與分頁才會正確
      const response = await load({ silent: true });
      // 刪掉當頁最後一筆時本頁會變空，退回上一頁（setPage 會觸發重新載入）
      if (response && response.data.length === 0 && page > 1) {
        setPage(page - 1);
      }
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <>
      <Breadcrumb items={[{ label: "首頁", to: "/" }, { label: "收藏" }]} />

      <div className="page-head">
        <span className="page-head-badge">
          <HeartIcon filled />
        </span>
        <div>
          <h1>我的收藏</h1>
          <p>您收藏的商品清單，方便快速查看與日後比較。</p>
        </div>
      </div>

      {error ? (
        <ErrorState onRetry={load} />
      ) : items === null ? (
        <PageLoader />
      ) : (
        <>
          <div className="fav-bar">
            <div className="fav-bar-count">
              <span className="fav-bar-icon">
                <BookmarkIcon />
              </span>
              <span className="fav-bar-label">已收藏商品數量</span>
              <span className="fav-bar-divider" aria-hidden="true" />
              <strong className="fav-bar-value">{pagination.total_items}</strong>
              <span className="fav-bar-unit">項商品</span>
            </div>
            <div className="fav-bar-sort">
              <label htmlFor="favorite-sort">排序方式</label>
              <select
                id="favorite-sort"
                value={sort}
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
          </div>

          {items.length === 0 ? (
            <EmptyState title="您還沒有收藏任何商品。" />
          ) : (
            <>
              <div className="fav-grid">
                {items.map((item) => {
                  const product = item.product;
                  const price = formatOfficialPrice(
                    product.official_price,
                    product.official_currency,
                  );
                  return (
                    <article
                      key={item.favorite_id}
                      className={`fav-card${product.is_active ? "" : " inactive"}`}
                    >
                      <div className="fav-thumb">
                        <MediaImage src={product.primary_image_url} alt={product.name} loading="lazy" />
                        {!product.is_active && <span className="fav-thumb-badge">商品已下架</span>}
                      </div>
                      <div className="fav-card-body">
                        <div className="fav-card-top">
                          <span className="fav-activity">{product.activity.name}</span>
                          <button
                            type="button"
                            className="fav-heart"
                            aria-label={`取消收藏 ${product.name}`}
                            title="取消收藏"
                            disabled={removingId === product.id}
                            onClick={() => handleRemove(product.id)}
                          >
                            <HeartIcon filled />
                          </button>
                        </div>
                        <h3 className="fav-name">{product.name}</h3>
                        {price ? (
                          <p className="fav-price">{price}</p>
                        ) : (
                          <p className="fav-price fav-price-empty">未提供官方原價</p>
                        )}
                        <Link className="btn btn-secondary fav-view" to={`/products/${product.id}`}>
                          查看商品
                        </Link>
                      </div>
                    </article>
                  );
                })}
              </div>
              <Pagination
                page={pagination.page}
                totalPages={pagination.total_pages}
                onPageChange={setPage}
              />
            </>
          )}
        </>
      )}
    </>
  );
}
