"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Zap } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

interface RegisterResult {
  message?: string;
  requiresVerification?: boolean;
}

// --- Validation helpers (adapted from TerraGenius) ---
function isValidEmail(val: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
}

function getPasswordStrength(pw: string): { label: string; level: 0 | 1 | 2 | 3 } {
  if (pw.length < 8) return { label: "Too short", level: 0 };
  const score =
    (pw.length >= 8 ? 1 : 0) +
    (/[A-Z]/.test(pw) ? 1 : 0) +
    (/[0-9]/.test(pw) ? 1 : 0) +
    (/[^A-Za-z0-9]/.test(pw) ? 1 : 0);
  if (score <= 2) return { label: "Weak", level: 1 };
  if (score <= 3) return { label: "Fair", level: 2 };
  return { label: "Strong", level: 3 };
}

const colorMap: Record<number, string> = {
  0: "bg-gray-300",
  1: "bg-red-500",
  2: "bg-yellow-500",
  3: "bg-green-500",
};

export function SignupPageInner() {
  const { register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [clientSideError, setClientSideError] = useState<string | null>(null);

  const pwStrength = getPasswordStrength(password);
  const passwordMatch = confirmPassword.length > 0 && password === confirmPassword;
  const passwordConfirmed = confirmPassword.length > 0 && passwordMatch;
  const emailValid = email.length === 0 || isValidEmail(email);

  // Form is valid: all fields filled, email format ok, pw >= 8, confirm matches
  const isValid =
    name.trim().length > 0 &&
    emailValid &&
    isValidEmail(email) &&
    password.length >= 8 &&
    passwordMatch &&
    confirmPassword.length > 0;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setClientSideError(null);

    // Client-side validation
    if (!name.trim()) {
      setClientSideError("Please enter your name");
      return;
    }
    if (!emailValid || !isValidEmail(email)) {
      setClientSideError("Please enter a valid email address");
      return;
    }
    if (password.length < 8) {
      setClientSideError("Password must be at least 8 characters long");
      return;
    }
    if (!passwordMatch || confirmPassword.length === 0) {
      setClientSideError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      const data: RegisterResult = await register(name.trim(), email.trim(), password);
      const msg =
        data.message ||
        (data.requiresVerification
          ? "Account created! Please check your email to verify your account."
          : "Account created successfully!");
      setSuccess(msg);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Registration failed";
      // If the server returns a "not found" error (from the old nginx proxy issue),
      // show a helpful message
      if (msg.includes("NOT FOUND") || msg.includes("404")) {
        setError(
          "The API endpoint could not be reached. Please try again later."
        );
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left side - branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-hero-gradient relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent" />
        <div className="relative z-10 flex flex-col justify-center px-12">
          <Link href="/" className="flex items-center gap-2 font-bold text-xl text-foreground mb-8">
            <Zap className="h-6 w-6 text-primary" />
            <span>LightSerp</span>
          </Link>
          <h2 className="text-3xl font-bold leading-tight">
            AI agents deserve
            <br />
            <span className="text-primary">real-time web access</span>
          </h2>
          <p className="mt-4 text-muted-foreground text-lg max-w-md">
            Sign up for free. Get an API key. Configure your MCP client in 60 seconds.
          </p>
          <div className="mt-12 grid grid-cols-2 gap-4">
            <div className="rounded-lg border bg-card/50 backdrop-blur p-4">
              <div className="text-2xl font-bold text-primary">5+</div>
              <div className="text-xs text-muted-foreground mt-1">Proxy Providers</div>
            </div>
            <div className="rounded-lg border bg-card/50 backdrop-blur p-4">
              <div className="text-2xl font-bold text-primary">24/7</div>
              <div className="text-xs text-muted-foreground mt-1">Uptime SLA</div>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - form */}
      <div className="flex w-full lg:w-1/2 items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold">Create your account</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Start with a free API key
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm">
              {error}
            </div>
          )}

          {clientSideError && (
            <div className="mb-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm">
              {clientSideError}
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 rounded-md bg-green-100 text-green-800 text-sm">
              {success}
              {success.includes("check your email") && (
                <div className="mt-2">
                  <Link
                    href="/login"
                    className="text-primary font-medium underline"
                  >
                    Go to login →
                  </Link>
                </div>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {/* Full Name */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Full Name</label>
              <input
                type="text"
                name="name"
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
                required
                className="w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            {/* Email */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Email</label>
              <input
                type="email"
                name="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className={`w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 ${
                  email && !emailValid ? "border-red-500" : ""
                }`}
              />
              {email && !emailValid && (
                <p className="text-xs text-red-500">Please enter a valid email address</p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Password</label>
              <input
                type="password"
                name="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 8 characters"
                required
                minLength={8}
                className="w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              {password.length > 0 && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <div className={`h-1.5 flex-1 rounded-full ${colorMap[pwStrength.level]}`} />
                  <span>{pwStrength.label}</span>
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Confirm Password</label>
              <input
                type="password"
                name="confirmPassword"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
                required
                className={`w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 ${
                  confirmPassword && !passwordConfirmed ? "border-red-500" : ""
                }`}
              />
              {confirmPassword && !passwordConfirmed && (
                <p className="text-xs text-red-500">Passwords do not match</p>
              )}
              {passwordConfirmed && (
                <p className="text-xs text-green-500">Passwords match</p>
              )}
            </div>

            <button
              type="submit"
              disabled={!isValid || loading}
              className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition disabled:opacity-50"
            >
              {loading ? "Creating account..." : "Create Account"}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-primary font-medium hover:underline">
              Log in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
