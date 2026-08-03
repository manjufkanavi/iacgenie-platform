import Link from "next/link";
import { Zap, Search, Globe, Shield, Terminal, Code } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-hero-gradient">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            <Zap className="h-5 w-5 text-primary" />
            <span>LightSerp</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-medium hover:text-primary">
              Log in
            </Link>
            <Link href="/signup">
              <Button size="sm">Sign Up</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative px-6 pt-20 pb-16 text-center">
        <div className="mx-auto max-w-4xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary">
            <Terminal className="h-3.5 w-3.5" />
            Self-hosted MCP server for web search &amp; scraping
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Search &amp; Scrape the{" "}
            <span className="text-primary">live web</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            Configure LightSerp as your MCP provider and give any AI agent the
            ability to search the web and scrape any URL with one API key.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link href="/signup">
              <Button size="lg" className="gap-2">
                Get Started Free
                <Zap className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="#setup">
              <Button size="lg" variant="outline" className="gap-2">
                <Terminal className="h-4 w-4" />
                Setup Guide
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Cards */}
      <section className="px-6 py-16">
        <div className="mx-auto max-w-5xl">
          <div className="grid gap-6 md:grid-cols-3">
            {/* Search */}
            <div className="glass-card p-6">
              <Search className="mb-3 h-6 w-6 text-primary" />
              <h3 className="text-lg font-semibold">Web Search</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Fresh, structured search results via SearXNG. No cached data —
                always from the live web.
              </p>
              <Link href="/signup" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
                Try now <span aria-hidden="true">&rarr;</span>
              </Link>
            </div>

            {/* Scrape */}
            <div className="glass-card p-6">
              <Globe className="mb-3 h-6 w-6 text-primary" />
              <h3 className="text-lg font-semibold">URL Scraping</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Extract clean, token-efficient content from any URL. Renders in
                a real browser for dynamic pages.
              </p>
              <Link href="/signup" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
                Try now <span aria-hidden="true">&rarr;</span>
              </Link>
            </div>

            {/* Self-Hosted */}
            <div className="glass-card p-6">
              <Shield className="mb-3 h-6 w-6 text-primary" />
              <h3 className="text-lg font-semibold">Self-Hosted</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Your data stays on your machine. Run it locally or on your
                server — full control over proxies and rate limits.
              </p>
              <Link href="/signup" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
                Deploy now <span aria-hidden="true">&rarr;</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Code Example Section */}
      <section className="px-6 py-16">
        <div className="mx-auto max-w-4xl">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold">Use in any MCP client</h2>
            <p className="mt-2 text-muted-foreground">
              One API key. Works with Claude Code, Cursor, Warp, and more.
            </p>
          </div>
          <div className="glass-card overflow-hidden">
            <div className="flex items-center gap-2 border-b px-4 py-2">
              <div className="h-3 w-3 rounded-full bg-red-400" />
              <div className="h-3 w-3 rounded-full bg-yellow-400" />
              <div className="h-3 w-3 rounded-full bg-green-400" />
              <span className="ml-2 text-xs text-muted-foreground">bash</span>
            </div>
            <pre className="p-4 text-sm">
              <code className="text-muted-foreground">
{`# Install LightSerp CLI
npm install -g lightserp

# Configure your API key
lightserp configure --key YOUR_API_KEY

# Search the web
lightserp search "latest AI news"

# Scrape a URL
lightserp scrape https://example.com`}
              </code>
            </pre>
          </div>
        </div>
      </section>

      {/* MCP Setup Guide */}
      <section id="setup" className="px-6 py-16">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-2xl font-bold text-center mb-8">
            <Terminal className="inline h-5 w-5 mr-2 text-primary" />
            Configure as MCP Provider
          </h2>

          <div className="space-y-4">
            {/* Step 1 */}
            <div className="glass-card p-5">
              <div className="flex items-start gap-3">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                  1
                </div>
                <div>
                  <h4 className="font-semibold">Start the LightSerp server</h4>
                  <pre className="mt-2 rounded-lg bg-muted p-3 text-xs overflow-x-auto">
                    <code>{`docker compose -f docker-compose.lightserp-web.yml up -d`}</code>
                  </pre>
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="glass-card p-5">
              <div className="flex items-start gap-3">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                  2
                </div>
                <div>
                  <h4 className="font-semibold">Add to your MCP client config</h4>
                  <pre className="mt-2 rounded-lg bg-muted p-3 text-xs overflow-x-auto">
                    <code>{`{
  "mcpServers": {
    "lightserp": {
      "url": "http://localhost:3001"
    }
  }
}`}</code>
                  </pre>
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div className="glass-card p-5">
              <div className="flex items-start gap-3">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                  3
                </div>
                <div>
                  <h4 className="font-semibold">Connect with your API key</h4>
                  <pre className="mt-2 rounded-lg bg-muted p-3 text-xs overflow-x-auto">
                    <code>{`export LIGHTSERP_API_KEY=sk_you...`}</code>
                  </pre>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Create your key at{" "}
                    <Link href="/signup" className="text-primary underline">
                      lightserp.iacgenie.com/signup
                    </Link>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-6 py-20 text-center">
        <div className="mx-auto max-w-2xl">
          <h2 className="text-3xl font-bold">Ready to get started?</h2>
          <p className="mt-3 text-muted-foreground">
            Sign up for free and get your first API key in seconds.
          </p>
          <Link href="/signup" className="mt-6 inline-block">
            <Button size="lg" className="gap-2">
              Sign Up Free
              <Zap className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t px-6 py-8">
        <div className="mx-auto max-w-7xl flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            <span>LightSerp &copy; 2026</span>
          </div>
          <div className="flex gap-6">
            <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
            <Link href="/terms" className="hover:text-foreground">Terms</Link>
            <a href="https://github.com/manjufkanavi/LightSerp" target="_blank" rel="noopener" className="hover:text-foreground">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
