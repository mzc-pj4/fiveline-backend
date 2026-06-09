import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { setAdminSession } from "../auth";

export default function AdminRegister() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/api/auth/admin/register", { name, employee_id: employeeId });
      setAdminSession(res.data.access_token, { name: res.data.name, role: res.data.role });
      navigate("/", { replace: true });
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "등록에 실패했습니다");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "#f5f5f5" }}>
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-black tracking-[0.2em]" style={{ color: "#111" }}>FIVELINE</h1>
          <p className="text-xs mt-1 tracking-widest font-medium" style={{ color: "#999" }}>관리자 포털</p>
        </div>
        <div className="bg-white p-8" style={{ border: "1px solid #e5e7eb" }}>
          <h2 className="text-base font-bold mb-6" style={{ color: "#111" }}>관리자 등록</h2>
          {error && (
            <div className="mb-4 px-4 py-3 text-sm rounded-sm" style={{ background: "#fef2f2", color: "#991b1b", border: "1px solid #fecaca" }}>
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "#555" }}>이름</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} required placeholder="홍길동"
                className="w-full px-3 py-2.5 text-sm outline-none border rounded-sm"
                style={{ borderColor: "#ddd", color: "#111" }}
                onFocus={(e) => (e.currentTarget.style.borderColor = "#111")}
                onBlur={(e) => (e.currentTarget.style.borderColor = "#ddd")} />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "#555" }}>사원번호</label>
              <input type="text" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} required placeholder="사원번호 입력"
                className="w-full px-3 py-2.5 text-sm outline-none border rounded-sm"
                style={{ borderColor: "#ddd", color: "#111" }}
                onFocus={(e) => (e.currentTarget.style.borderColor = "#111")}
                onBlur={(e) => (e.currentTarget.style.borderColor = "#ddd")} />
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-3 text-sm font-bold tracking-widest disabled:opacity-50"
              style={{ background: "#111", color: "#fff" }}>
              {loading ? "등록 중..." : "관리자 등록"}
            </button>
          </form>
          <p className="mt-4 text-center text-xs" style={{ color: "#aaa" }}>
            이미 등록됐나요? <Link to="/login" className="underline" style={{ color: "#555" }}>로그인</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
