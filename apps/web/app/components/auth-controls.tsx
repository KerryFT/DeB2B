"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiBase, apiFetch } from "../lib/api";

export default function AuthControls() {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    apiFetch("/api/v1/me")
      .then((response) => setAuthenticated(response.ok))
      .catch(() => setAuthenticated(false));
  }, []);

  async function logout() {
    const response = await apiFetch("/api/v1/auth/microsoft/logout", { method: "POST" });
    if (response.ok) {
      setAuthenticated(false);
      router.push("/");
      router.refresh();
    }
  }

  if (authenticated === null) return <span className="auth-state">Đang kiểm tra phiên…</span>;
  if (!authenticated) {
    return <a className="button auth-button" href={`${apiBase}/api/v1/auth/microsoft/login`}>Đăng nhập Microsoft</a>;
  }
  return <button className="button secondary auth-button" onClick={logout}>Đăng xuất</button>;
}
