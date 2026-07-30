import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getActivities } from "../../api/activities.js";
import { deactivateAdminProduct, getAdminProducts, reactivateAdminProduct } from "../../api/adminProducts.js";
import MediaImage from "../../components/common/MediaImage.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import Button from "../../components/common/Button.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import ListFooter from "../../components/common/ListFooter.jsx";
import { SearchIcon } from "../../components/common/icons.jsx";

export default function ProductListPage() {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activities, setActivities] = useState([]);
  // 篩選條件以網址為單一來源（docs/03 §23a）：原本 activity_id／is_active 只取初始值、
  // keyword 放元件狀態，點側邊選單回到 /admin/products（無 query）時篩選會殘留，
  // 得離開頁面或 F5 才清得掉。活動管理頁的「查看商品」也是靠 activity_id 帶進來的。
  const activityId = searchParams.get("activity_id") ?? "";
  const isActive = searchParams.get("is_active") ?? "";
  const keyword = searchParams.get("keyword") ?? "";

  // 搜尋框的未送出輸入值；keyword 才是實際條件
  const [keywordInput, setKeywordInput] = useState(keyword);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [products, setProducts] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [error, setError] = useState(false);
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    getActivities({ pageSize: 50 }).then((response) => setActivities(response.data));
  }, []);

  function load() {
    setError(false);
    setProducts(null);
    getAdminProducts(token, {
      activityId: activityId || undefined,
      isActive: isActive === "" ? undefined : isActive === "true",
      keyword: keyword || undefined,
      page,
      pageSize,
    })
      .then((response) => {
        setProducts(response.data);
        setPagination(response.pagination);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activityId, isActive, keyword, page, pageSize]);

  // 網址的關鍵字被外部改掉時（點選單清空、瀏覽器上一頁），搜尋框要跟著更新
  useEffect(() => {
    setKeywordInput(keyword);
  }, [keyword]);

  // 網址上的篩選一改就回第一頁，否則可能停在超出範圍的頁碼而顯示空清單
  useEffect(() => {
    setPage(1);
  }, [activityId, isActive, keyword]);

  /** 更新網址上的篩選參數；值為空即移除該參數。 */
  function updateParams(changes) {
    const params = new URLSearchParams(searchParams);
    Object.entries(changes).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
    });
    setSearchParams(params, { replace: true });
  }

  function handleSearchSubmit(event) {
    event.preventDefault();
    updateParams({ keyword: keywordInput.trim() });
  }

  async function handleToggleActive(product) {
    setBusyId(product.id);
    try {
      if (product.is_active) {
        await deactivateAdminProduct(product.id, token);
      } else {
        await reactivateAdminProduct(product.id, token);
      }
      load();
    } finally {
      setBusyId(null);
    }
  }

  const activeActivity = activities.find((a) => a.id === activityId);

  return (
    <div className="admin-page">
      <div className="page-header">
        <h1>商品管理</h1>
      </div>

      {activityId && (
        <div className="filter-banner">
          <span>
            目前僅顯示活動「<strong>{activeActivity?.name ?? "指定活動"}</strong>」的商品
          </span>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => updateParams({ activity_id: "" })}
          >
            顯示全部商品
          </button>
        </div>
      )}

      <div className="admin-toolbar">
        <form className="search-input admin-toolbar-search" onSubmit={handleSearchSubmit} role="search">
          <input
            type="search"
            placeholder="搜尋商品名稱"
            value={keywordInput}
            onChange={(event) => setKeywordInput(event.target.value)}
            aria-label="搜尋商品名稱"
          />
          <button type="submit" className="search-input-icon-btn" aria-label="搜尋">
            <SearchIcon className="icon-search" />
          </button>
        </form>
        <select
          className="admin-toolbar-select"
          value={activityId}
          onChange={(event) => updateParams({ activity_id: event.target.value })}
          aria-label="選擇活動"
        >
          <option value="">全部活動</option>
          {activities.map((activity) => (
            <option key={activity.id} value={activity.id}>
              {activity.name}
            </option>
          ))}
        </select>
        <select
          className="admin-toolbar-select"
          value={isActive}
          onChange={(event) => updateParams({ is_active: event.target.value })}
          aria-label="狀態篩選"
        >
          <option value="">全部狀態</option>
          <option value="true">已上架</option>
          <option value="false">已下架</option>
        </select>
        <Link className="btn btn-primary admin-toolbar-action" to="/admin/products/new">
          + 新增商品
        </Link>
      </div>

      <div className="admin-panel">
      {error ? (
        <ErrorState onRetry={load} />
      ) : products === null ? (
        <PageLoader />
      ) : products.length === 0 ? (
        <EmptyState title="目前沒有商品。" />
      ) : (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>商品圖片</th>
                  <th>商品名稱</th>
                  <th>所屬活動</th>
                  <th>官方價格</th>
                  <th>幣別</th>
                  <th>關聯角色</th>
                  <th>狀態</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id}>
                    <td>
                      <MediaImage
                        src={product.primary_image_url}
                        alt=""
                        style={{ width: "4rem", height: "4rem", objectFit: "cover", borderRadius: "var(--radius)" }}
                      />
                    </td>
                    <td>{product.name}</td>
                    <td>{product.activity.name}</td>
                    <td>{product.official_price ?? "—"}</td>
                    <td>{product.official_currency ?? "—"}</td>
                    <td>
                      {product.characters && product.characters.length > 0 ? (
                        <span className="char-tags">
                          {product.characters.slice(0, 3).map((c) => (
                            <span key={c.id} className="char-tag">
                              {c.name}
                            </span>
                          ))}
                          {product.characters.length > 3 && (
                            <span className="char-tag char-tag-more">
                              +{product.characters.length - 3}
                            </span>
                          )}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <span className={`status-badge ${product.is_active ? "status-badge-success" : "status-badge-neutral"}`}>
                        {product.is_active ? "已上架" : "已下架"}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <Link className="btn btn-secondary" to={`/admin/products/${product.id}`}>
                          編輯
                        </Link>
                        <Link className="btn btn-secondary" to={`/products/${product.id}`}>
                          查看詳情
                        </Link>
                        <Button
                          variant={product.is_active ? "danger" : "secondary"}
                          loading={busyId === product.id}
                          onClick={() => handleToggleActive(product)}
                        >
                          {product.is_active ? "下架" : "上架"}
                        </Button>
                      </div>
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
