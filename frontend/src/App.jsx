import { BrowserRouter } from "react-router-dom";
import AppRoutes from "./routes/AppRoutes.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import { CartProvider } from "./context/CartContext.jsx";
import { NotificationProvider } from "./context/NotificationContext.jsx";

export default function App() {
  return (
    // basename 取自 vite 的 base：本機為 "/"，GitHub Pages build 為 "/WuWaGroup/"。
    // 沒設的話部署後所有路由都會對不上。
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <AuthProvider>
        <CartProvider>
          <NotificationProvider>
            <AppRoutes />
          </NotificationProvider>
        </CartProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
