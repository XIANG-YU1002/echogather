import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getGroupBuyDetail } from "../api/groupBuys.js";
import { ApiError } from "../api/client.js";
import Breadcrumb from "../components/common/Breadcrumb.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import MediaImage from "../components/common/MediaImage.jsx";
import PageLoader from "../components/common/PageLoader.jsx";

/**
 * 某一次開團接單的所有商品。
 *
 * 從團主公開頁點活動進來，用意是先看完整的接單商品清單再挑一項下單；
 * 點單一商品才進開團詳情頁（該頁一次只處理一項商品的購買流程）。
 * 以開團 id 作為路由參數而非活動 id——商品是掛在「某一次開團」上，
 * 同一活動的不同輪次接單商品可能不同。
 */
export default function GroupBuyProductsPage() {
  const { groupBuyId } = useParams();
  const [groupBuy, setGroupBuy] = useState(null);
  const [error, setError] = useState(null);

  async function load() {
    setError(null);
    setGroupBuy(null);
    try {
      const response = await getGroupBuyDetail(groupBuyId);
      setGroupBuy(response.data);
    } catch (err) {
      setError(err);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupBuyId]);

  if (error) {
    if (error instanceof ApiError && error.status === 404) {
      return <ErrorState title="找不到此開團" description="此開團不存在或已被移除。" />;
    }
    return <ErrorState onRetry={load} />;
  }

  if (!groupBuy) {
    return <PageLoader />;
  }

  const leaderName = groupBuy.group_leader.display_name;
  const activityName = groupBuy.activity.name;

  return (
    <>
      <Breadcrumb
        items={[
          { label: "首頁", to: "/" },
          { label: "團主", to: "/group-leaders" },
          { label: leaderName, to: `/group-leaders/${groupBuy.group_leader.id}` },
          { label: `${leaderName} ${activityName}` },
        ]}
      />

      <section className="section">
        <h2 className="section-title">
          接單商品
          <span className="gbp-count">共 {groupBuy.products.length} 項</span>
        </h2>

        {/* 已停止接單時仍要提醒，否則使用者點進商品才發現不能下單 */}
        {!groupBuy.is_available && (
          <p className="gbp-closed-note">此開團目前已停止接受新的訂單。</p>
        )}

        {groupBuy.products.length === 0 ? (
          <EmptyState title="此開團沒有接單商品。" />
        ) : (
          <div className="gbp-grid">
            {groupBuy.products.map((item) => (
              <Link
                key={item.group_buy_product_id}
                className="gbp-card"
                to={`/group-buys/${groupBuy.id}?product=${item.group_buy_product_id}`}
              >
                <MediaImage
                  className="gbp-card-image"
                  src={item.product.primary_image_url}
                  alt={item.product.name}
                  loading="lazy"
                />
                <div className="gbp-card-body">
                  <h3>{item.product.name}</h3>
                  <p className="gbp-card-price">
                    <span>團購價</span>
                    <strong>NT$ {item.unit_price}</strong>
                  </p>
                  <p
                    className={`gbp-card-stock${item.is_available ? "" : " is-out"}`}
                  >
                    {item.is_available ? `剩餘 ${item.available_quantity} 個` : "已額滿"}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
