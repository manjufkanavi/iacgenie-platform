"use client";

import { AuthProvider } from "@/contexts/auth-context";
import { LoginPageInner } from "./login-inner";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  return (
    <AuthProvider>
      <LoginPageInner />
    </AuthProvider>
  );
}
