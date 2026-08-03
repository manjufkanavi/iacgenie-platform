import type { Metadata } from "next";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: "LightSerp — Web Search & Scrape API",
  description: "Configure LightSerp as your MCP provider and give any AI agent the ability to search the web and scrape any URL with one API key.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background text-foreground font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
