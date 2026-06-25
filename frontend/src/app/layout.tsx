import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Compliance QnA Assistant",
  description: "AI-powered compliance assistant for SOC2 document analysis",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-white text-gray-900 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
