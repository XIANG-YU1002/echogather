import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProductDetail, getProductGroupBuys } from "../api/products.js";
import { ApiError, resolveMediaUrl } from "../api/client.js";
import Breadcrumb from "../components/common/Breadcrumb.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import PageLoader from "../components/common/PageLoader.jsx";
import FavoriteButton from "../components/product/FavoriteButton.jsx";
import ProductGallery from "../components/product/ProductGallery.jsx";
import GroupBuyCompareTable from "../components/group-buy/GroupBuyCompareTable.jsx";
import { ChevronDownIcon } from "../components/common/icons.jsx";
import { useAuth } from "../context/AuthContext.jsx";

const SORT_OPTIONS = [
  { value: "newest", label: "開團時間：新到舊" },
  { value: "price_asc", label: "價格：低到高" },
  { value: "price_desc", label: "價格：高到低" },
  { value: "deadline_asc", label: "截止時間：近到遠" },
  { value: "deadline_desc", label: "截止時間：遠到近" },
];

// 空字串 = 未選擇（不限），為預設值
const PAYMENT_METHOD_OPTIONS = [
  { value: "", label: "不限" },
  { value: "cash_on_delivery", label: "取貨付款" },
  { value: "bank_transfer", label: "匯款" },
];

const PAGE_SIZE = 10;

export default function ProductDetailPage() {
  const { productId } = useParams();
  const { token } = useAuth();

  const [product, setProduct] = useState(null);
  const [error, setError] = useState(null);

  const [groupBuys, setGroupBuys] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [groupBuysError, setGroupBuysError] = useState(false);
  const [page, setPage] = useState(1);
  const [loadingMore, setLoadingMore] = useState(false);
  const [sort, setSort] = useState("newest");
  const [availableOnly, setAvailableOnly] = useState(false);
  // 空字串代表未選擇（不限付款方式）
  const [paymentMethod, setPaymentMethod] = useState("");

  async function loadProduct() {
    setError(null);
    setProduct(null);
    try {
      const response = await getProductDetail(productId, token);
      setProduct(response.data);
    } catch (err) {
      setError(err);
    }
  }

  async function loadGroupBuys(pageToLoad, append) {
    setGroupBuysError(false);
    if (append) {
      setLoadingMore(true);
    } else {
      setGroupBuys(null);
    }
    try {
      const response = await getProductGroupBuys(productId, {
        sort,
        availableOnly,
        paymentMethod,
        page: pageToLoad,
        pageSize: PAGE_SIZE,
      });
      setGroupBuys((prev) => (append && prev ? [...prev, ...response.data] : response.data));
      setPagination(response.pagination);
    } catch {
      setGroupBuysError(true);
    } finally {
      setLoadingMore(false);
    }
  }

  useEffect(() => {
    loadProduct();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId]);

  useEffect(() => {
    setPage(1);
    loadGroupBuys(1, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId, sort, availableOnly, paymentMethod]);

  function handleLoadMore() {
    const next = page + 1;
    setPage(next);
    loadGroupBuys(next, true);
  }

  if (error) {
    if (error instanceof ApiError && error.status === 404) {
      return <ErrorState title="找不到此商品" description="商品不存在或已被移除。" />;
    }
    return <ErrorState onRetry={loadProduct} />;
  }

  if (!product) {
    return <PageLoader />;
  }

  const images = [product.primary_image_url, ...product.images.map((image) => image.image_url)].map(
    resolveMediaUrl,
  );

  const hasMore = pagination && pagination.page < pagination.total_pages;

  return (
    <>
      <Breadcrumb
        items={[
          { label: "首頁", to: "/" },
          { label: product.activity.name, to: `/activities/${product.activity.id}` },
          { label: product.name },
        ]}
      />

      <div className="product-detail">
        <ProductGallery images={images} alt={product.name} />

        <div className="product-info-card">
          <div className="product-info-title">
            <h1>{product.name}</h1>
          </div>
          <p className="product-info-activity">
            <Link to={`/activities/${product.activity.id}`}>{product.activity.name}</Link>
          </p>
          {product.characters.length > 0 && (
            <p className="product-info-characters">
              角色：{product.characters.map((character) => character.name).join("、")}
            </p>
          )}
          {product.official_price && (
            <p className="product-info-price">
              官方原價：
              <strong>
                {product.official_currency === "TWD" ? "NT$" : `${product.official_currency} `}
                {product.official_price}
              </strong>
            </p>
          )}
          {product.description && <p className="product-info-desc">{product.description}</p>}
          {!product.is_active && <p className="product-info-inactive">此商品已下架。</p>}
          <div className="product-info-actions">
            <FavoriteButton productId={product.id} initialFavorited={product.is_favorited} />
          </div>
        </div>
      </div>

      <section className="compare-panel">
        <div className="compare-panel-head">
          <h2 className="section-title" style={{ marginBottom: 0 }}>
            可跟團開團
            {pagination && <span className="section-count"> {pagination.total_items} 筆開團中</span>}
          </h2>
        </div>

        <div className="compare-filters">
          <label className="sort-control">
            排序
            <select
              value={sort}
              onChange={(event) => {
                setSort(event.target.value);
              }}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="compare-filter-check">
            <input
              type="checkbox"
              checked={availableOnly}
              onChange={(event) => setAvailableOnly(event.target.checked)}
            />
            只顯示目前可跟團
          </label>
          <label className="sort-control">
            付款方式
            <select
              value={paymentMethod}
              onChange={(event) => setPaymentMethod(event.target.value)}
            >
              {PAYMENT_METHOD_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {groupBuysError ? (
          <ErrorState onRetry={() => loadGroupBuys(1, false)} />
        ) : groupBuys === null ? (
          <PageLoader />
        ) : groupBuys.length === 0 ? (
          <EmptyState title="目前沒有符合條件的開團。" />
        ) : (
          <>
            <GroupBuyCompareTable
              groupBuys={groupBuys}
              showFullGift={product.activity.has_full_gift}
            />
            {hasMore && (
              <div className="compare-more">
                <button type="button" onClick={handleLoadMore} disabled={loadingMore}>
                  {loadingMore ? "載入中…" : "查看更多開團"}
                  <ChevronDownIcon className="compare-more-chevron" />
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </>
  );
}
