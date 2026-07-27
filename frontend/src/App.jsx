import { BrowserRouter } from "react-router-dom";
import AppRoutes from "./routes/AppRoutes.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import { CartProvider } from "./context/CartContext.jsx";
import { NotificationProvider } from "./context/NotificationContext.jsx";

export default function App() {
  return (
    <BrowserRouter>
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
