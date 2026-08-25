import type { Metadata } from "next";
import AppShell from "./components/app-shell";
import "./globals.css";

export const metadata: Metadata = { title: "AR Operations", description: "Evidence-first receivables operations" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="vi"><body><AppShell>{children}</AppShell></body></html>;
}
