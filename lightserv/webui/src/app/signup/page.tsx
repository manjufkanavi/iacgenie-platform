"use client";

import { AuthProvider } from "@/contexts/auth-context";
import { SignupPageInner } from "./signup-inner";

export const dynamic = "force-dynamic";

export default function SignupPage() {
  return (
    <AuthProvider>
      <SignupPageInner />
    </AuthProvider>
  );
}
