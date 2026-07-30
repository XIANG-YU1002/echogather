import { useState } from "react";
import { ApiError } from "../../api/client.js";
import { createUnmergeRequest } from "../../api/orders.js";
import { useAuth } from "../../context/AuthContext.jsx";
import Alert from "./Alert.jsx";
import Button from "./Button.jsx";
import FormField from "./FormField.jsx";
import Modal from "./Modal.jsx";

/**
 * 會員提出取消合併（拆單）申請的燈窗。
 *
 * 兩個入口共用：通知中心「訂單已合併」通知底下的按鈕，以及會員訂單詳情頁
 * （使用者 2026-07-30 要求訂單頁也要有入口——通知一多就找不到那則通知了）。
 *
 * onSubmitted 在送出成功後呼叫，讓呼叫端重新載入資料，
 * 好讓按鈕消失、改顯示「等待團主處理」。
 */
export default function UnmergeRequestModal({ orderId, onClose, onSubmitted }) {
  const { token } = useAuth();
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      await createUnmergeRequest(orderId, reason, token);
      setDone(true);
      onSubmitted?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "送出失敗，請稍後再試。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      title={done ? "已送出取消合併申請" : "取消合併訂單"}
      onClose={onClose}
      footer={
        done ? (
          <Button onClick={onClose}>關閉</Button>
        ) : (
          <>
            <Button variant="muted" onClick={onClose}>
              取消
            </Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? "送出中…" : "送出申請"}
            </Button>
          </>
        )
      }
    >
      {done ? (
        <p className="nc-unmerge-note">
          已通知團主。團主確認後訂單會拆回合併前的狀態，屆時你會再收到一則通知；
          若團主不同意，也會說明原因。
        </p>
      ) : (
        <>
          <p className="nc-unmerge-note">
            送出後由團主確認才會拆回原本的多張訂單，訂單金額與狀態會回到合併前。
            如果只是想詢問內容，建議先直接聯絡團主。
          </p>
          <FormField label="想告知團主的原因（選填）">
            <textarea
              rows={3}
              maxLength={500}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="例如：想分開付款、其中一筆想改數量"
            />
          </FormField>
          {error && <Alert type="error">{error}</Alert>}
        </>
      )}
    </Modal>
  );
}
