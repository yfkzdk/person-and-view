import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "记忆回声 — AI Voice Chat",
  description: "暗紫LED风格AI语音对话系统，粒子成像，沉浸回忆感",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
