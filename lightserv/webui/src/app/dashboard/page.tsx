import Link from "next/link";
import { Zap, Key, Activity, Shield, ArrowRight } from "lucide-react";

export default function DashboardPage() {
  // Placeholder stats — will be fetched from API in production
  const stats = {
    totalKeys: 1,
    requestsToday: 0,
    keysUsed: 1,
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
      <div className="mx-auto max-w-5xl px-6 py-8">
        {/* Welcome */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold">Welcome to LightSerp</h1>
          <p className="text-muted-foreground mt-1">
            Manage your API keys and configure your MCP clients.
          </p>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3 mb-8">
          <div className="glass-card p-5">
            <Key className="h-5 w-5 text-primary mb-2" />
            <div className="text-2xl font-bold">{stats.totalKeys}</div>
            <div className="text-xs text-muted-foreground mt-1">API Keys</div>
          </div>
          <div className="glass-card p-5">
            <Activity className="h-5 w-5 text-primary mb-2" />
            <div className="text-2xl font-bold">{stats.requestsToday}</div>
            <div className="text-xs text-muted-foreground mt-1">Requests Today</div>
          </div>
          <div className="glass-card p-5">
            <Shield className="h-5 w-5 text-primary mb-2" />
            <div className="text-2xl font-bold">{stats.keysUsed}</div>
            <div className="text-xs text-muted-foreground mt-1">Active Keys</div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid gap-4 md:grid-cols-2">
          <Link href="/settings" className="glass-card p-6 hover:border-primary/30 transition group">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Create API Key</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Generate a new API key for your MCP clients.
                </p>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition" />
            </div>
          </Link>

          <Link href="/playground" className="glass-card p-6 hover:border-primary/30 transition group">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">MCP Playground</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Test search and scrape tool calls directly.
                </p>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition" />
            </div>
          </Link>

          <Link href="/dashboard/mcp-setup" className="glass-card p-6 hover:border-primary/30 transition group">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">MCP Setup Guide</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Step-by-step instructions for popular MCP clients.
                </p>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition" />
            </div>
          </Link>
        </div>

        {/* Quick Start Code */}
        <div className="mt-8 glass-card p-5">
          <h3 className="font-semibold mb-3">Quick Start</h3>
          <pre className="rounded-lg bg-muted p-4 text-xs overflow-x-auto">
            <code>{`# Use your API key with curl
curl -H "X-API-Key: ***" \\
  http://lightserp.iacgenie.com/search?q=hello

# Or configure as MCP server
cat > ~/.config/mcp/lightserp.json <<EOF
{
  "mcpServers": {
    "lightserp": {
      "url": "http://lightserp.iacgenie.com",
      "headers": {
        "X-API-Key": "***"
      }
    }
  }
}
EOF`}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
