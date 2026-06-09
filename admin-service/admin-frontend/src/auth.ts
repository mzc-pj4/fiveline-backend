const TOKEN_KEY = "fiveline_admin_token";
const USER_KEY = "fiveline_admin_user";

export type AdminUser = { name: string; role: string };

export function setAdminSession(token: string, user: AdminUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getAdminToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getAdminUser(): AdminUser | null {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as AdminUser) : null;
}

export function clearAdminSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAdminAuthenticated(): boolean {
  return getAdminToken() !== null;
}
