"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle, XCircle, Loader2, Mail } from "lucide-react";

export default function VerifyEmailClient() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");
  const [resent, setResent] = useState(false);

  async function verify() {
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      setMessage("Invalid verification link. The token is missing.");
      return;
    }

    try {
      const res = await fetch(`/api/auth?path=/api/auth/verify-email&token=${token}`, {
        method: "GET",
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus("error");
        setMessage(data.error || "Verification failed");
      } else {
        setStatus("success");
        setMessage(data.message || "Email verified successfully!");
      }
    } catch {
      setStatus("error");
      setMessage("Failed to verify email. Please try again.");
    }
  }

  async function resend() {
    setResent(false);
    try {
      const res = await fetch("/api/auth?path=/api/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: localStorage.getItem("pending_email") || "" }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessage(data.error || "Failed to resend");
      } else {
        setResent(true);
        setMessage("Verification email resent! Check your inbox.");
      }
    } catch {
      setMessage("Failed to resend verification email.");
    }
  }

  useEffect(() => {
    verify();
  }, [searchParams]);

  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex lg:w-1/2 bg-hero-gradient relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent" />
        <div className="relative z-10 flex flex-col justify-center px-12">
          <Link href="/" className="flex items-center gap-2 font-bold text-xl text-foreground mb-8">
            <div className="h-6 w-6 text-primary">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
              </svg>
            </div>
            <span>LightSerp</span>
          </Link>
          <h2 className="text-3xl font-bold leading-tight">
            Verify your
            <br />
            <span className="text-primary">email</span>
          </h2>
          <p className="mt-4 text-muted-foreground text-lg max-w-md">
            We sent a verification link to your email address. Click it to activate your account.
          </p>
        </div>
      </div>

      <div className="flex w-full lg:w-1/2 items-center justify-center p-8">
        <div className="w-full max-w-sm text-center">
          <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
            {status === "loading" && <Loader2 className="h-8 w-8 text-primary animate-spin" />}
            {status === "success" && <CheckCircle className="h-8 w-8 text-green-600" />}
            {status === "error" && <XCircle className="h-8 w-8 text-destructive" />}
          </div>

          <h1 className="text-2xl font-bold mb-2">
            {status === "loading"
              ? "Verifying your email..."
              : status === "success"
              ? "Email verified!"
              : "Verification failed"}
          </h1>
          <p className="text-sm text-muted-foreground mb-6">
            {message}
          </p>

          {status === "success" && (
            <Link
              href="/login"
              className="inline-block rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition"
            >
              Go to login →
            </Link>
          )}

          {status === "error" && (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground">
                Did not receive the email? Check your spam folder.
              </p>
              <button
                onClick={resend}
                disabled={resent}
                className="text-sm text-primary font-medium hover:underline disabled:opacity-50"
              >
                {resent ? "Email resent! ✓" : "Resend verification email"}
              </button>
              <div>
                <Link
                  href="/login"
                  className="text-sm text-muted-foreground hover:text-foreground"
                >
                  Back to login
                </Link>
              </div>
            </div>
          )}

          {status === "loading" && (
            <Link
              href="/login"
              className="text-sm text-muted-foreground hover:text-foreground mt-4 inline-block"
            >
              Cancel
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
