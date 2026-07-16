import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import GlobalIngestProgress from "@/components/GlobalIngestProgress";
import { AuthProvider } from "@/components/AuthProvider";

export const metadata: Metadata = {
  title: "Codebase Intelligence",
  description: "AI-powered architecture analysis for codebases",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Nav />
          <GlobalIngestProgress />
          <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
