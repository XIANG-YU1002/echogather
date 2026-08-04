# EchoGather

《鳴潮》官方周邊開團資訊整合與跟團管理平台。

- **前端：** React + Vite + JavaScript（`frontend/`）
- **後端：** FastAPI + SQLAlchemy + Alembic（`backend/`）
- **資料庫：** PostgreSQL
- **規格文件：** `docs/`（含需求追蹤矩陣 `00_Requirements_Traceability_Matrix.md`）

## 開發環境設定

### 後端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # 依實際資料庫（本機 PostgreSQL 或 Supabase）修改 DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## 目前進度

第一版依 `docs/` 內規格分階段開發，目前完成階段請見對話紀錄／commit 歷史。
