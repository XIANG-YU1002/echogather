import { Route, Routes } from "react-router-dom";
import MainLayout from "../layouts/MainLayout.jsx";
import AdminLayout from "../layouts/AdminLayout.jsx";
import MemberLayout from "../layouts/MemberLayout.jsx";
import GroupLeaderLayout from "../layouts/GroupLeaderLayout.jsx";
import HomePage from "../pages/HomePage.jsx";
import SearchPage from "../pages/SearchPage.jsx";
import ActivityDetailPage from "../pages/ActivityDetailPage.jsx";
import ProductDetailPage from "../pages/ProductDetailPage.jsx";
import GroupBuyDetailPage from "../pages/GroupBuyDetailPage.jsx";
import GroupBuyProductsPage from "../pages/GroupBuyProductsPage.jsx";
import GroupLeaderListPage from "../pages/GroupLeaderListPage.jsx";
import GroupLeaderProfilePage from "../pages/GroupLeaderProfilePage.jsx";
import LoginPage from "../pages/LoginPage.jsx";
import ForgotPasswordPage from "../pages/ForgotPasswordPage.jsx";
import ResetPasswordPage from "../pages/ResetPasswordPage.jsx";
import RegisterPage from "../pages/RegisterPage.jsx";
import NotFoundPage from "../pages/NotFoundPage.jsx";
import AdminDashboardPage from "../pages/admin/AdminDashboardPage.jsx";
import ProfilePage from "../pages/member/ProfilePage.jsx";
import FavoritesPage from "../pages/member/FavoritesPage.jsx";
import NotificationsPage from "../pages/member/NotificationsPage.jsx";
import GroupLeaderApplicationPage from "../pages/member/GroupLeaderApplicationPage.jsx";
import FollowListPage from "../pages/member/FollowListPage.jsx";
import OrderConfirmPage from "../pages/member/OrderConfirmPage.jsx";
import OrdersPage from "../pages/member/OrdersPage.jsx";
import OrderDetailPage from "../pages/member/OrderDetailPage.jsx";
import CancellationRequestPage from "../pages/member/CancellationRequestPage.jsx";
import GroupLeaderDashboardPage from "../pages/group-leader/DashboardPage.jsx";
import GroupLeaderOwnProfilePage from "../pages/group-leader/ProfilePage.jsx";
import GroupLeaderGroupBuyListPage from "../pages/group-leader/GroupBuyListPage.jsx";
import GroupLeaderGroupBuyCreatePage from "../pages/group-leader/GroupBuyCreatePage.jsx";
import GroupLeaderGroupBuyEditPage from "../pages/group-leader/GroupBuyEditPage.jsx";
import GroupLeaderProductOrdersPage from "../pages/group-leader/ProductOrdersPage.jsx";
import GroupLeaderOrderListPage from "../pages/group-leader/OrderListPage.jsx";
import GroupLeaderOrderDetailPage from "../pages/group-leader/OrderDetailPage.jsx";
import GroupLeaderAnnouncementListPage from "../pages/group-leader/AnnouncementListPage.jsx";
import AdminActivityListPage from "../pages/admin/ActivityListPage.jsx";
import AdminActivityFormPage from "../pages/admin/ActivityFormPage.jsx";
import AdminProductListPage from "../pages/admin/ProductListPage.jsx";
import AdminProductFormPage from "../pages/admin/ProductFormPage.jsx";
import AdminProductBatchCreatePage from "../pages/admin/ProductBatchCreatePage.jsx";
import AdminGroupLeaderApplicationListPage from "../pages/admin/GroupLeaderApplicationListPage.jsx";
import AdminGroupLeaderApplicationDetailPage from "../pages/admin/GroupLeaderApplicationDetailPage.jsx";
import AdminAnnouncementListPage from "../pages/admin/AnnouncementListPage.jsx";

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/activities/:activityId" element={<ActivityDetailPage />} />
        <Route path="/products/:productId" element={<ProductDetailPage />} />
        <Route path="/group-buys/:groupBuyId" element={<GroupBuyDetailPage />} />
        <Route path="/group-buys/:groupBuyId/products" element={<GroupBuyProductsPage />} />
        <Route path="/group-leaders" element={<GroupLeaderListPage />} />
        <Route path="/group-leaders/:groupLeaderId" element={<GroupLeaderProfilePage />} />

        <Route element={<MemberLayout />}>
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/favorites" element={<FavoritesPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/group-leader-application" element={<GroupLeaderApplicationPage />} />
          <Route path="/follow-list" element={<FollowListPage />} />
          <Route path="/orders/confirm" element={<OrderConfirmPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/orders/:orderId" element={<OrderDetailPage />} />
          <Route path="/orders/:orderId/cancel" element={<CancellationRequestPage />} />
        </Route>

        <Route element={<GroupLeaderLayout />}>
          <Route path="/group-leader" element={<GroupLeaderDashboardPage />} />
          <Route path="/group-leader/profile" element={<GroupLeaderOwnProfilePage />} />
          <Route path="/group-leader/group-buys" element={<GroupLeaderGroupBuyListPage />} />
          <Route path="/group-leader/group-buys/new" element={<GroupLeaderGroupBuyCreatePage />} />
          <Route path="/group-leader/group-buys/:groupBuyId" element={<GroupLeaderGroupBuyEditPage />} />
          <Route
            path="/group-leader/group-buys/:groupBuyId/product-orders"
            element={<GroupLeaderProductOrdersPage />}
          />
          <Route path="/group-leader/orders" element={<GroupLeaderOrderListPage />} />
          <Route path="/group-leader/orders/:orderId" element={<GroupLeaderOrderDetailPage />} />
          <Route path="/group-leader/announcements" element={<GroupLeaderAnnouncementListPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<AdminDashboardPage />} />
        <Route path="/admin/group-leader-applications" element={<AdminGroupLeaderApplicationListPage />} />
        <Route
          path="/admin/group-leader-applications/:applicationId"
          element={<AdminGroupLeaderApplicationDetailPage />}
        />
        <Route path="/admin/activities" element={<AdminActivityListPage />} />
        <Route path="/admin/activities/new" element={<AdminActivityFormPage />} />
        <Route path="/admin/activities/:activityId" element={<AdminActivityFormPage />} />
        <Route path="/admin/products" element={<AdminProductListPage />} />
        {/* 新增走批次頁（可一次建立多項）；編輯仍是單項表單頁 */}
        <Route path="/admin/products/new" element={<AdminProductBatchCreatePage />} />
        <Route path="/admin/products/:productId" element={<AdminProductFormPage />} />
        <Route path="/admin/announcements" element={<AdminAnnouncementListPage />} />
      </Route>
    </Routes>
  );
}
