import { useEffect, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { globalSearchPreview, searchProducts } from "../api/search.js";
import MediaImage from "../components/common/MediaImage.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import PageLoader from "../components/common/PageLoader.jsx";
import Pagination from "../components/common/Pagination.jsx";
import {
  ArrowLeftIcon,
  BagIcon,
  ChevronRightIcon,
  UsersIcon,
} from "../components/common/icons.jsx";

// 摘要檢視每區塊顯示的筆數；全部商品檢視的每頁筆數
const PREVIEW_LIMIT = 6;
const PAGE_SIZE = 20;

function ProductGrid({ products }) {
  return (
    <div className="sr-product-grid">
      {products.map((product) => (
        <Link key={product.id} className="sr-product" to={`/products/${product.id}`}>
          <MediaImage
            className="sr-product-image"
            src={product.primary_image_url}
            alt={product.name}
            loading="lazy"
          />
          <span className="sr-product-name">{product.name}</span>
        </Link>
      ))}
    </div>
  );
}

/** 全部商品檢視：只顯示商品，一頁 20 筆並提供頁碼；不顯示角色區塊。 */
function AllProductsView({ q, characterId, characterName, backTo }) {
  const [page, setPage] = useState(1);
  const [products, setProducts] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setPage(1);
  }, [q, characterId]);

  function load() {
    setError(false);
    setProducts(null);
    searchProducts(q, { characterId, page, pageSize: PAGE_SIZE })
      .then((response) => {
        setProducts(response.data);
        setPagination(response.pagination);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, characterId, page]);

  return (
    <section className="sr-section">
      <div className="sr-section-head">
        <h2 className="sr-section-title">
          <span className="sr-section-icon">
            <BagIcon />
          </span>
          商品
          {pagination && <span className="sr-section-count">{pagination.total_items} 件結果</span>}
        </h2>
        <Link className="sr-more" to={backTo}>
          <ArrowLeftIcon />
          返回搜尋結果
        </Link>
      </div>

      {characterName && (
        <p className="sr-filter-note">目前顯示包含角色「{characterName}」的所有商品。</p>
      )}

      {error ? (
        <ErrorState onRetry={load} />
      ) : products === null ? (
        <PageLoader />
      ) : products.length === 0 ? (
        <EmptyState title="沒有符合的商品。" />
      ) : (
        <>
          <ProductGrid products={products} />
          <Pagination
            page={pagination.page}
            totalPages={pagination.total_pages}
            onPageChange={setPage}
          />
        </>
      )}
    </section>
  );
}

/** 摘要檢視：商品前 6 筆（可查看更多）＋角色區塊。 */
function SummaryView({ q }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(false);

  function load() {
    setError(false);
    setResult(null);
    // 活動區段依 2026-07-23 決議不顯示（API 仍會回傳，前台忽略）
    globalSearchPreview(q, PREVIEW_LIMIT)
      .then((response) => setResult(response.data))
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  if (error) return <ErrorState onRetry={load} />;
  if (result === null) return <PageLoader />;

  const { products, characters } = result;

  return (
    <>
      <section className="sr-section">
        <div className="sr-section-head">
          <h2 className="sr-section-title">
            <span className="sr-section-icon">
              <BagIcon />
            </span>
            商品
            <span className="sr-section-count">{products.total_count} 件結果</span>
          </h2>
          {products.has_more && (
            <Link className="sr-more" to={`/search?q=${encodeURIComponent(q)}&view=products`}>
              查看更多
              <ChevronRightIcon />
            </Link>
          )}
        </div>
        {products.items.length === 0 ? (
          <EmptyState title="沒有符合的商品。" />
        ) : (
          <ProductGrid products={products.items} />
        )}
      </section>

      <section className="sr-section">
        <div className="sr-section-head">
          <h2 className="sr-section-title">
            <span className="sr-section-icon">
              <UsersIcon />
            </span>
            角色
            <span className="sr-section-count">{characters.total_count} 件結果</span>
          </h2>
        </div>
        {characters.items.length === 0 ? (
          <EmptyState title="沒有符合的角色。" />
        ) : (
          <div className="sr-character-list">
            {characters.items.map((character) => (
              <Link
                key={character.id}
                className="sr-character"
                to={`/search?character_id=${character.id}&name=${encodeURIComponent(character.name)}`}
              >
                <span className="sr-character-name">{character.name}</span>
                <span className="sr-character-count">
                  關聯商品 {character.related_product_count} 件
                </span>
                <span className="sr-character-arrow">
                  <ChevronRightIcon />
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

export default function SearchPage() {
  const [searchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const characterId = searchParams.get("character_id") ?? undefined;
  const characterName = searchParams.get("name") ?? "";
  const view = searchParams.get("view") ?? "";

  // 直接以網址進入 /search 但沒有任何搜尋條件時導回首頁。
  // （Header 搜尋框在關鍵字空白時本來就不會送出，不會走到這裡。）
  if (!q && !characterId) {
    return <Navigate to="/" replace />;
  }

  // 帶 character_id，或從商品區塊點「查看更多」進來，都走全部商品檢視
  const showAllProducts = Boolean(characterId) || view === "products";

  return (
    <>
      <div className="sr-head">
        <h1>搜尋結果</h1>
        {q ? (
          <p>
            關鍵字：<strong>{q}</strong>
          </p>
        ) : (
          characterName && (
            <p>
              角色：<strong>{characterName}</strong>
            </p>
          )
        )}
      </div>

      {showAllProducts ? (
        <AllProductsView
          q={q}
          characterId={characterId}
          characterName={characterName}
          backTo={q ? `/search?q=${encodeURIComponent(q)}` : "/"}
        />
      ) : (
        <SummaryView q={q} />
      )}
    </>
  );
}
