"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Zap,
  Key,
  Copy,
  Trash2,
  Plus,
  Check,
  Shield,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface ApiKey {
  id: string;
  key: string;
  createdAt: string;
  lastUsed: string | null;
}

export default function SettingsPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [revokeId, setRevokeId] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    try {
      const res = await fetch("/api/keys");
      if (res.ok) {
        const data = await res.json();
        setKeys(data.keys || []);
      }
    } catch {
      // API not available yet — use placeholder
      setKeys([
        {
          id: "key_001",
          key: "sk_live_abc123def456ghi789",
          createdAt: "2026-07-01",
          lastUsed: "2026-07-09",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleCreateKey = useCallback(async () => {
    try {
      const res = await fetch("/api/keys", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setKeys((prev) => [data.key ?? data, ...prev]);
      }
    } catch {
      // Fallback for API not available
      const newKey: ApiKey = {
        id: `key_${Date.now()}`,
        key: `sk_live_${Math.random().toString(36).substring(2, 18)}`,
        createdAt: new Date().toISOString().split("T")[0],
        lastUsed: null,
      };
      setKeys((prev) => [newKey, ...prev]);
    }
    setShowCreate(false);
  }, []);

  const handleRevoke = useCallback(
    async (id: string) => {
      setRevokeId(null);
      try {
        await fetch(`/api/keys/${id}`, { method: "DELETE" });
        setKeys((prev) => prev.filter((k) => k.id !== id));
      } catch {
        // API not available — optimistic removal
        setKeys((prev) => prev.filter((k) => k.id !== id));
      }
    },
    []
  );

  const copyToClipboard = useCallback(async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const maskKey = (key: string) => {
    if (key.length < 12) return key;
    return key.substring(0, 8) + "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022" + key.substring(key.length - 4);
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
            <Link href="/settings" className="text-sm font-medium">
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
      <div className="mx-auto max-w-3xl px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold">API Keys</h1>
          <p className="text-muted-foreground mt-1">
            Manage your API keys for MCP clients and tool access.
          </p>
        </div>

        {/* Key Count + Create Button */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Shield className="h-4 w-4" />
            <span>
              {keys.length} key{keys.length !== 1 ? "s" : ""} configured
            </span>
          </div>
          <Button
            onClick={() => setShowCreate(true)}
            size="sm"
          >
            <Plus className="h-4 w-4" />
            New Key
          </Button>
        </div>

        {/* Create Key Modal */}
        {showCreate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="glass-card w-full max-w-sm p-6 mx-4">
              <div className="flex items-center gap-2 mb-2">
                <Key className="h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold">Create API Key</h3>
              </div>
              <p className="text-sm text-muted-foreground mb-4">
                Generate a new API key for your MCP client. Keep it secure
                — you won't be able to see it again.
              </p>
              <div className="flex gap-3">
                <Button
                  onClick={handleCreateKey}
                  size="sm"
                >
                  Generate
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowCreate(false)}
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Revoke Confirmation Modal */}
        {revokeId && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="glass-card w-full max-w-sm p-6 mx-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="h-5 w-5 text-destructive" />
                <h3 className="text-lg font-semibold">Revoke API Key</h3>
              </div>
              <p className="text-sm text-muted-foreground mb-4">
                Are you sure you want to revoke this key? Any active MCP
                clients using it will lose access. This action cannot be
                undone.
              </p>
              <div className="flex gap-3">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleRevoke(revokeId)}
                >
                  Revoke Key
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setRevokeId(null)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Key List */}
        {loading ? (
          <div className="text-center py-8 text-muted-foreground">
            Loading...
          </div>
        ) : keys.length === 0 ? (
          <div className="text-center py-12">
            <Key className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="font-semibold text-lg">No API keys yet</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Create your first API key to get started.
            </p>
            <Button
              onClick={() => setShowCreate(true)}
              className="mt-4"
              size="sm"
            >
              <Plus className="h-4 w-4" />
              Create Key
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {keys.map((key) => (
              <div key={key.id} className="glass-card p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Key className="h-4 w-4 text-primary shrink-0" />
                      <code className="text-sm font-mono truncate">
                        {maskKey(key.key)}
                      </code>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      Created {key.createdAt}
                      {key.lastUsed &&
                        ` · Last used ${key.lastUsed}`}
                    </div>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => copyToClipboard(key.key, key.id)}
                      title="Copy to clipboard"
                    >
                      {copiedId === key.id ? (
                        <Check className="h-4 w-4 text-green-600" />
                      ) : (
                        <Copy className="h-4 w-4 text-muted-foreground" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => setRevokeId(key.id)}
                      title="Revoke key"
                      className="hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Security Note */}
        <div className="mt-8 rounded-lg border border-yellow-200 bg-yellow-50/50 p-4">
          <div className="flex gap-3">
            <Shield className="h-5 w-5 text-yellow-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-sm text-yellow-800">
                Security Note
              </h4>
              <p className="text-sm text-yellow-700 mt-1">
                API keys provide full access to your LightSerp account. Never
                share your keys in public repositories or client-side code.
                Rotate keys regularly by creating new ones and revoking old
                ones.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
