import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cyclope Central",
  description: "Security-first self-hosted MSP/RMM platform foundation"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
