"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Zap, Search, Globe, Play, Terminal, Shield } from "lucide-react";

type ToolType = "search" | "scrape";

export default function PlaygroundPage() {
  const [tool, setTool] = useState<ToolType>("search");
  const [query, setQuery] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load API key from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("lightsERP_api_key");
    if (saved) setApiKey(saved);
  }, []);

  const handleRun = async () => {
    if (!query.trim()) return;
    if (!apiKey.trim()) {
      setError("Enter your API key first");
      return;
    }

    setError(null);
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch(`/api/${tool === "search" ? "search" : "scrape"}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey.trim(),
        },
        body: JSON.stringify({
          query: tool === "search" ? query : query,
          ...(tool === "scrape" && { url: query }),
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Request failed" }));
        throw new Error(err.error || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
      localStorage.setItem("lightsERP_api_key", apiKey.trim());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <Link href="/dashboard" className="flex items-center gap-2 font-bold text-lg">
            <Zap className="h-5 w-5 text-primary" />
            <span>LightSerp</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-sm font-medium">
              Dashboard
            </Link>
            <Link href="/settings" className="text-sm font-medium hover:text-primary">
              Settings
            </Link>
            <Link href="/login">
              <span className="text-sm text-muted-foreground hover:text-foreground">
                Log out
              </span>
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold">MCP Playground</h1>
          <p className="text-muted-foreground mt-1">
            Test search and scrape tool calls directly from your browser.
          </p>
        </div>

        {/* API Key Input */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <label className="text-sm font-medium">API Key</label>
          </div>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk_live_..."
            className="w-full px-3 py-2 rounded-md border bg-background text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
          <Link href="/settings" className="mt-1 text-xs text-primary hover:underline">
            Manage API keys
          </Link>
        </div>

        {/* Tool Selector */}
        <div className="mb-6">
          <label className="text-sm font-medium mb-2 block">Tool</label>
          <div className="flex gap-3">
            <button
              onClick={() => setTool("search")}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition ${
                tool === "search"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              <Search className="h-4 w-4" />
              Search
            </button>
            <button
              onClick={() => setTool("scrape")}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition ${
                tool === "scrape"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              <Globe className="h-4 w-4" />
              Scrape
            </button>
          </div>
        </div>

        {/* Input */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <Terminal className="h-4 w-4 text-muted-foreground" />
            <label className="text-sm font-medium">
              {tool === "search" ? "Search Query" : "URL"}
            </label>
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={tool === "search" ? "latest AI news" : "https://example.com"}
            className="w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            onKeyDown={(e) => e.key === "Enter" && handleRun()}
          />
        </div>

        {/* Run Button */}
        <button
          onClick={handleRun}
          disabled={loading || !query.trim() || !apiKey.trim()}
          className="flex items-center gap-2 rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition disabled:opacity-50 disabled:cursor-not-allowed mb-6"
        >
          <Play className="h-4 w-4" />
          {loading ? "Running..." : "Run"}
        </button>

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="glass-card overflow-hidden">
            <div className="flex items-center gap-2 border-b px-4 py-2">
              <Terminal className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Response</span>
            </div>
            <pre className="p-4 text-xs overflow-x-auto max-h-96 overflow-y-auto">
              <code className="text-muted-foreground">{result}</code>
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
