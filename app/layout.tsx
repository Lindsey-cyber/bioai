import type { Metadata } from "next";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI × BIO — Personal News Feed",
  description: "A private, focused AI × Bio news reader for the US and Europe.",
  icons: {
    icon: [{ url: "/favicon.svg?v=scroll", type: "image/svg+xml" }],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
