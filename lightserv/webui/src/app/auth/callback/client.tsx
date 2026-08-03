"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";

export default function AuthCallbackClient() {
  const { setCredentials } = useAuth();
  const searchParams = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    async function handleCallback() {
      const code = searchParams.get("code");
      const state = searchParams.get("state");

      if (!code) {
        setError("No authorization code received from Keycloak");
        return;
      }

      try {
        const res = await fetch("/api/auth?path=/api/auth/keycloak/callback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code, state }),
        });

        const data = await res.json();
        if (!res.ok) {
          setError(data.error || "Authentication failed");
          return;
        }

        const user = {
          id: data.user.id,
          username: data.user.username,
          email: data.user.email,
        };
        setCredentials(data.token, user);
        window.location.href = "/dashboard";
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Authentication failed");
      }
    }

    handleCallback();
  }, [searchParams, setCredentials]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        {error ? (
          <>
            <div className="mx-auto w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6 text-destructive">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-destructive">{error}</h2>
            <p className="text-sm text-muted-foreground mt-2">
              Redirecting back to login...
            </p>
            <button
              onClick={() => (window.location.href = "/login")}
              className="mt-4 text-sm text-primary hover:underline"
            >
              Go to login
            </button>
          </>
        ) : (
          <>
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6 text-primary animate-spin">
                <path d="M21 12a9 9 0 11-6.219-8.56" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold">Authenticating with Keycloak...</h2>
            <p className="text-sm text-muted-foreground mt-2">
              Please wait while we verify your identity.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
