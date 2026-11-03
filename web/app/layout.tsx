import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Đánh giá nguy cơ sức khỏe bằng AI",
  description: "Hệ thống hỗ trợ đánh giá nguy cơ sức khỏe bằng mô hình học máy, bằng chứng và luật an toàn.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
