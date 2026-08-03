"use client";

import { useState } from "react";
import Link from "next/link";
import { Zap, Copy, Check } from "lucide-react";

type McpConfig = {
  name: string;
  icon: string;
  description: string;
  config: string;
  instructions: string[];
};

const MCP_CONFIGS: McpConfig[] = [
  {
    name: "Claude Code",
    icon: "🤖",
    description: "Configure LightSerp as an MCP server for Claude Code CLI.",
    instructions: [
      "Open your MCP config file at ~/.claude/mcp.json",
      "Add the lightserp configuration below",
      "Restart Claude Code",
    ],
    config: `{
  "mcpServers": {
    "lightserp": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/claude-code"],
      "env": {
        "LIGHTSERP_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}`,
  },
  {
    name: "Cursor",
    icon: "✍️",
    description: "Add LightSerp as an MCP server in Cursor.",
    instructions: [
      "Open Cursor Settings → Features → MCP",
      "Click 'Add Server' and enter the configuration below",
      "Save and restart the MCP server",
    ],
    config: `{
  "mcpServers": {
    "lightserp": {
      "url": "http://lightserp.iacgenie.com"
    }
  }
}`,
  },
  {
    name: "Warp",
    icon: "⚡",
    description: "Configure LightSerp in Warp's MCP settings.",
    instructions: [
      "Open Warp Settings → Integrations → MCP",
      "Add a new server with the configuration below",
      "Save the configuration",
    ],
    config: `{
  "mcpServers": {
    "lightserp": {
      "url": "http://lightserp.iacgenie.com",
      "headers": {
        "X-API-Key": "YOUR_API_KEY"
      }
    }
  }
}`,
  },
  {
    name: "Windsurf",
    icon: "🌊",
    description: "Configure LightSerp in Windsurf's MCP servers.",
    instructions: [
      "Open Windsurf Settings → MCP Servers",
      "Click 'Add Server' and paste the configuration",
      "Save and verify connection",
    ],
    config: `{
  "mcpServers": {
    "lightserp": {
      "url": "http://lightserp.iacgenie.com",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}`,
  },
  {
    name: "Claude Desktop",
    icon: "🖥️",
    description: "Configure LightSerp in Claude Desktop app.",
    instructions: [
      "Open Claude Desktop config at ~/Library/Application Support/Claude/claude_desktop_config.json",
      "Add the lightserp configuration",
      "Restart Claude Desktop",
    ],
    config: `{
  "mcpServers": {
    "lightserp": {
      "url": "http://lightserp.iacgenie.com"
    }
  }
}`,
  },
];

export default function McpSetupPage() {
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState(false);

  const current = MCP_CONFIGS[activeTab];

  const copyConfig = async () => {
    await navigator.clipboard.writeText(current.config);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
          <h1 className="text-2xl font-bold">MCP Setup Guide</h1>
          <p className="text-muted-foreground mt-1">
            Configure LightSerp as your MCP provider. Choose your client below.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {MCP_CONFIGS.map((config, idx) => (
            <button
              key={idx}
              onClick={() => { setActiveTab(idx); setCopied(false); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition whitespace-nowrap ${
                idx === activeTab
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              <span>{config.icon}</span>
              <span>{config.name}</span>
            </button>
          ))}
        </div>

        {/* Description */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold">{current.name}</h2>
          <p className="text-muted-foreground">{current.description}</p>
        </div>

        {/* Instructions */}
        <div className="mb-6">
          <h3 className="font-semibold text-sm mb-3">Instructions</h3>
          <ol className="space-y-2">
            {current.instructions.map((step, idx) => (
              <li key={idx} className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                  {idx + 1}
                </span>
                <span className="text-sm">{step}</span>
              </li>
            ))}
          </ol>
        </div>

        {/* Config Code Block */}
        <div className="glass-card overflow-hidden">
          <div className="flex items-center justify-between border-b px-4 py-2">
            <span className="text-xs text-muted-foreground">JSON Config</span>
            <button
              onClick={copyConfig}
              className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  Copy
                </>
              )}
            </button>
          </div>
          <pre className="p-4 text-xs overflow-x-auto">
            <code className="text-muted-foreground">{current.config}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
