import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { clearAdminSession, getAdminUser } from "../auth";

type DashboardData = {
  total_orders: number; total_revenue: number;
  total_users: number; total_products: number;
  orders_by_status: { status: string; count: number }[];
  top_products: { name: string; sold_count: number }[];
  recent_orders: AdminOrder[];
};
type AdminOrder = { id: number; total_price: number; status: string; created_at: string; email: string; user_name: string };
type AdminUser = { id: number; email: string; name: string; role: string; phone: string | null; created_at: string };
type AdminProduct = { id: number; name: string; category: string; brand: string | null; price: number; stock_quantity: number };

const TABS = ["대시보드", "주문관리", "사용자", "상품관리"] as const;
type Tab = typeof TABS[number];

const STATUS_LABEL: Record<string, string> = { SUCCESS: "결제완료", FAILED: "결제실패", PENDING: "처리중" };
const STATUS_COLOR: Record<string, { background: string; color: string }> = {
  SUCCESS: { background: "#ecfdf5", color: "#065f46" },
  FAILED: { background: "#fef2f2", color: "#991b1b" },
  PENDING: { background: "#fffbeb", color: "#92400e" },
};

function useDebounce(value: string, delay = 400) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("대시보드");
  const user = getAdminUser();

  function handleLogout() {
    clearAdminSession();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen" style={{ background: "#f9fafb" }}>
      <div className="border-b bg-white px-6 py-3 flex items-center justify-between" style={{ borderColor: "#e5e7eb" }}>
        <h1 className="text-base font-black tracking-widest" style={{ color: "#111" }}>FIVELINE 운영자 포털</h1>
        <div className="flex items-center gap-4">
          <span className="text-xs" style={{ color: "#666" }}>{user?.name}님</span>
          <button onClick={handleLogout} className="text-xs px-3 py-1.5 border rounded-sm" style={{ borderColor: "#ddd", color: "#555" }}>로그아웃</button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-0 mb-6 border-b" style={{ borderColor: "#e5e7eb" }}>
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className="px-5 py-2.5 text-sm font-medium transition-colors"
              style={{ borderBottom: tab === t ? "2px solid #111" : "2px solid transparent", color: tab === t ? "#111" : "#888", marginBottom: "-1px" }}>
              {t}
            </button>
          ))}
        </div>

        {tab === "대시보드" && <DashboardTab />}
        {tab === "주문관리" && <OrdersTab />}
        {tab === "사용자" && <UsersTab />}
        {tab === "상품관리" && <ProductsTab />}
      </div>
    </div>
  );
}

function SearchInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div className="relative">
      <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style={{ color: "#aaa" }} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
        <circle cx={11} cy={11} r={8} /><path d="m21 21-4.35-4.35" />
      </svg>
      <input
        type="text" value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pl-8 pr-3 py-1.5 text-sm border rounded-sm outline-none w-64"
        style={{ borderColor: value ? "#111" : "#ddd", color: "#333" }}
        onFocus={(e) => (e.currentTarget.style.borderColor = "#111")}
        onBlur={(e) => (e.currentTarget.style.borderColor = value ? "#111" : "#ddd")}
      />
      {value && (
        <button onClick={() => onChange("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-xs" style={{ color: "#aaa" }}>✕</button>
      )}
    </div>
  );
}

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white border p-5" style={{ borderColor: "#e5e7eb" }}>
      <p className="text-xs font-medium mb-1" style={{ color: "#999" }}>{label}</p>
      <p className="text-2xl font-black" style={{ color: "#111" }}>{value}</p>
    </div>
  );
}

function DashboardTab() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<DashboardData>("/api/admin/dashboard").then((r) => setData(r.data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm" style={{ color: "#bbb" }}>불러오는 중...</p>;
  if (!data) return <p className="text-sm" style={{ color: "#f00" }}>데이터를 불러올 수 없습니다.</p>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="총 주문 수" value={data.total_orders.toLocaleString()} />
        <KpiCard label="총 매출" value={`${Math.round(data.total_revenue).toLocaleString()}원`} />
        <KpiCard label="회원 수" value={data.total_users.toLocaleString()} />
        <KpiCard label="상품 수" value={data.total_products.toLocaleString()} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div className="bg-white border p-5" style={{ borderColor: "#e5e7eb" }}>
          <h3 className="text-sm font-bold mb-4" style={{ color: "#111" }}>주문 상태별 현황</h3>
          <div className="space-y-2">
            {data.orders_by_status.map((s) => (
              <div key={s.status} className="flex items-center justify-between">
                <span className="text-xs px-2 py-0.5 font-medium rounded-sm" style={STATUS_COLOR[s.status] ?? { background: "#f3f4f6", color: "#555" }}>
                  {STATUS_LABEL[s.status] ?? s.status}
                </span>
                <span className="text-sm font-bold" style={{ color: "#111" }}>{s.count}건</span>
              </div>
            ))}
            {data.orders_by_status.length === 0 && <p className="text-xs" style={{ color: "#bbb" }}>주문 없음</p>}
          </div>
        </div>

        <div className="bg-white border p-5" style={{ borderColor: "#e5e7eb" }}>
          <h3 className="text-sm font-bold mb-4" style={{ color: "#111" }}>인기 상품 Top 5</h3>
          <ol className="space-y-2">
            {data.top_products.map((p, i) => (
              <li key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="w-5 text-xs font-bold" style={{ color: i < 3 ? "#f59e0b" : "#bbb" }}>{i + 1}</span>
                  <span className="line-clamp-1" style={{ color: "#333", maxWidth: 180 }}>{p.name}</span>
                </div>
                <span className="font-medium" style={{ color: "#666" }}>{p.sold_count}개</span>
              </li>
            ))}
            {data.top_products.length === 0 && <p className="text-xs" style={{ color: "#bbb" }}>판매 데이터 없음</p>}
          </ol>
        </div>
      </div>

      <div className="bg-white border" style={{ borderColor: "#e5e7eb" }}>
        <div className="px-5 py-3 border-b" style={{ borderColor: "#f0f0f0", background: "#fafafa" }}>
          <h3 className="text-sm font-bold" style={{ color: "#111" }}>최근 주문 10건</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "#f9f9f9", borderBottom: "1px solid #f0f0f0" }}>
                {["주문ID", "회원", "금액", "상태", "주문일시"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-medium" style={{ color: "#888" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.recent_orders.map((o) => (
                <tr key={o.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                  <td className="px-4 py-2.5 font-medium" style={{ color: "#111" }}>#{o.id}</td>
                  <td className="px-4 py-2.5" style={{ color: "#444" }}>
                    <div>{o.user_name}</div>
                    <div className="text-xs" style={{ color: "#aaa" }}>{o.email}</div>
                  </td>
                  <td className="px-4 py-2.5 font-medium" style={{ color: "#111" }}>{Number(o.total_price).toLocaleString()}원</td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs px-2 py-0.5 rounded-sm font-medium" style={STATUS_COLOR[o.status] ?? { background: "#f3f4f6", color: "#555" }}>
                      {STATUS_LABEL[o.status] ?? o.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs" style={{ color: "#aaa" }}>{new Date(o.created_at).toLocaleString("ko-KR")}</td>
                </tr>
              ))}
              {data.recent_orders.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-xs" style={{ color: "#bbb" }}>주문 없음</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function OrdersTab() {
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(true);
  const q = useDebounce(searchInput);
  const SIZE = 20;

  useEffect(() => { setPage(1); }, [q, status]);

  useEffect(() => {
    setLoading(true);
    api.get<{ items: AdminOrder[]; total: number }>("/api/admin/orders", {
      params: { page, size: SIZE, ...(status ? { status } : {}), ...(q ? { q } : {}) },
    }).then((r) => { setOrders(r.data.items); setTotal(r.data.total); }).finally(() => setLoading(false));
  }, [page, status, q]);

  const totalPages = Math.ceil(total / SIZE);
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <SearchInput value={searchInput} onChange={setSearchInput} placeholder="이름 또는 이메일 검색" />
        <select value={status} onChange={(e) => setStatus(e.target.value)}
          className="text-sm px-3 py-1.5 border rounded-sm outline-none" style={{ borderColor: "#ddd", color: "#333" }}>
          <option value="">전체 상태</option>
          <option value="SUCCESS">결제완료</option>
          <option value="FAILED">결제실패</option>
          <option value="PENDING">처리중</option>
        </select>
        <span className="text-xs" style={{ color: "#888" }}>총 {total.toLocaleString()}건</span>
      </div>
      <OrderTable orders={orders} loading={loading} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}

function OrderTable({ orders, loading }: { orders: AdminOrder[]; loading: boolean }) {
  return (
    <div className="bg-white border" style={{ borderColor: "#e5e7eb" }}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr style={{ background: "#f9f9f9", borderBottom: "1px solid #f0f0f0" }}>
              {["주문ID", "회원", "금액", "상태", "주문일시"].map((h) => (
                <th key={h} className="px-4 py-2 text-left text-xs font-medium" style={{ color: "#888" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? <tr><td colSpan={5} className="px-4 py-8 text-center text-xs" style={{ color: "#bbb" }}>불러오는 중...</td></tr>
              : orders.map((o) => (
                <tr key={o.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                  <td className="px-4 py-2.5 font-medium" style={{ color: "#111" }}>#{o.id}</td>
                  <td className="px-4 py-2.5" style={{ color: "#444" }}>
                    <div>{o.user_name}</div>
                    <div className="text-xs" style={{ color: "#aaa" }}>{o.email}</div>
                  </td>
                  <td className="px-4 py-2.5 font-medium" style={{ color: "#111" }}>{Number(o.total_price).toLocaleString()}원</td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs px-2 py-0.5 rounded-sm font-medium" style={STATUS_COLOR[o.status] ?? { background: "#f3f4f6", color: "#555" }}>
                      {STATUS_LABEL[o.status] ?? o.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs" style={{ color: "#aaa" }}>{new Date(o.created_at).toLocaleString("ko-KR")}</td>
                </tr>
              ))}
            {!loading && orders.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-xs" style={{ color: "#bbb" }}>검색 결과 없음</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UsersTab() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(true);
  const q = useDebounce(searchInput);
  const SIZE = 20;

  useEffect(() => { setPage(1); }, [q]);

  useEffect(() => {
    setLoading(true);
    api.get<{ items: AdminUser[]; total: number }>("/api/admin/users", {
      params: { page, size: SIZE, ...(q ? { q } : {}) },
    }).then((r) => { setUsers(r.data.items); setTotal(r.data.total); }).finally(() => setLoading(false));
  }, [page, q]);

  const totalPages = Math.ceil(total / SIZE);
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <SearchInput value={searchInput} onChange={setSearchInput} placeholder="이름 또는 이메일 검색" />
        <span className="text-xs" style={{ color: "#888" }}>총 {total.toLocaleString()}명</span>
      </div>
      <div className="bg-white border" style={{ borderColor: "#e5e7eb" }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "#f9f9f9", borderBottom: "1px solid #f0f0f0" }}>
                {["ID", "이름", "이메일", "권한", "연락처", "가입일"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-medium" style={{ color: "#888" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? <tr><td colSpan={6} className="px-4 py-8 text-center text-xs" style={{ color: "#bbb" }}>불러오는 중...</td></tr>
                : users.map((u) => (
                  <tr key={u.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                    <td className="px-4 py-2.5 text-xs" style={{ color: "#888" }}>{u.id}</td>
                    <td className="px-4 py-2.5 font-medium" style={{ color: "#111" }}>{u.name}</td>
                    <td className="px-4 py-2.5" style={{ color: "#444" }}>{u.email}</td>
                    <td className="px-4 py-2.5">
                      <span className="text-xs px-2 py-0.5 rounded-sm font-medium"
                        style={u.role === "admin" ? { background: "#eff6ff", color: "#1d4ed8" } : { background: "#f3f4f6", color: "#555" }}>
                        {u.role === "admin" ? "관리자" : "고객"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs" style={{ color: "#666" }}>{u.phone ?? "-"}</td>
                    <td className="px-4 py-2.5 text-xs" style={{ color: "#aaa" }}>{new Date(u.created_at).toLocaleDateString("ko-KR")}</td>
                  </tr>
                ))}
              {!loading && users.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-xs" style={{ color: "#bbb" }}>검색 결과 없음</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}

function ProductsTab() {
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [editStock, setEditStock] = useState<Record<number, string>>({});
  const [saving, setSaving] = useState<number | null>(null);
  const q = useDebounce(searchInput);
  const SIZE = 20;

  useEffect(() => { setPage(1); }, [q]);

  useEffect(() => {
    setLoading(true);
    api.get<{ items: AdminProduct[]; total: number }>("/api/admin/products", {
      params: { page, size: SIZE, ...(q ? { q } : {}) },
    }).then((r) => { setProducts(r.data.items); setTotal(r.data.total); }).finally(() => setLoading(false));
  }, [page, q]);

  async function handleStockSave(productId: number) {
    const val = parseInt(editStock[productId] ?? "");
    if (isNaN(val) || val < 0) return;
    setSaving(productId);
    try {
      await api.patch(`/api/admin/products/${productId}/stock`, null, { params: { stock_quantity: val } });
      setProducts((prev) => prev.map((p) => p.id === productId ? { ...p, stock_quantity: val } : p));
      setEditStock((prev) => { const n = { ...prev }; delete n[productId]; return n; });
    } finally {
      setSaving(null);
    }
  }

  const totalPages = Math.ceil(total / SIZE);
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <SearchInput value={searchInput} onChange={setSearchInput} placeholder="상품명 또는 브랜드 검색" />
        <span className="text-xs" style={{ color: "#888" }}>총 {total.toLocaleString()}개 상품</span>
      </div>
      <div className="bg-white border" style={{ borderColor: "#e5e7eb" }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "#f9f9f9", borderBottom: "1px solid #f0f0f0" }}>
                {["ID", "상품명", "브랜드", "카테고리", "가격", "재고", ""].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-medium" style={{ color: "#888" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? <tr><td colSpan={7} className="px-4 py-8 text-center text-xs" style={{ color: "#bbb" }}>불러오는 중...</td></tr>
                : products.map((p) => (
                  <tr key={p.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                    <td className="px-4 py-2.5 text-xs" style={{ color: "#888" }}>{p.id}</td>
                    <td className="px-4 py-2.5 font-medium" style={{ color: "#111", maxWidth: 200 }}>
                      <span className="line-clamp-1">{p.name}</span>
                    </td>
                    <td className="px-4 py-2.5 text-xs" style={{ color: "#666" }}>{p.brand ?? "-"}</td>
                    <td className="px-4 py-2.5 text-xs" style={{ color: "#666" }}>{p.category}</td>
                    <td className="px-4 py-2.5 font-medium" style={{ color: "#111" }}>{Number(p.price).toLocaleString()}원</td>
                    <td className="px-4 py-2.5">
                      <input type="number" min={0}
                        value={editStock[p.id] ?? p.stock_quantity}
                        onChange={(e) => setEditStock((prev) => ({ ...prev, [p.id]: e.target.value }))}
                        className="w-20 px-2 py-1 text-xs border rounded-sm outline-none text-center"
                        style={{ borderColor: editStock[p.id] !== undefined ? "#111" : "#e5e7eb" }} />
                    </td>
                    <td className="px-4 py-2.5">
                      {editStock[p.id] !== undefined && (
                        <button onClick={() => handleStockSave(p.id)} disabled={saving === p.id}
                          className="px-3 py-1 text-xs font-bold rounded-sm disabled:opacity-50"
                          style={{ background: "#111", color: "#fff" }}>
                          {saving === p.id ? "저장중" : "저장"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              {!loading && products.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-xs" style={{ color: "#bbb" }}>검색 결과 없음</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}

function Pagination({ page, totalPages, onPageChange }: { page: number; totalPages: number; onPageChange: (p: number) => void }) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-center gap-2">
      <button onClick={() => onPageChange(Math.max(1, page - 1))} disabled={page === 1}
        className="px-3 py-1 text-xs border rounded-sm disabled:opacity-40" style={{ borderColor: "#ddd" }}>이전</button>
      <span className="text-xs" style={{ color: "#666" }}>{page} / {totalPages}</span>
      <button onClick={() => onPageChange(Math.min(totalPages, page + 1))} disabled={page === totalPages}
        className="px-3 py-1 text-xs border rounded-sm disabled:opacity-40" style={{ borderColor: "#ddd" }}>다음</button>
    </div>
  );
}
