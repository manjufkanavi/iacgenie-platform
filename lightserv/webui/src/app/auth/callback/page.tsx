import AuthCallbackClient from "./client";

// This route should never be prerendered — it requires runtime auth flow
export const dynamic = "force-dynamic";

export default function AuthCallbackPage() {
  return <AuthCallbackClient />;
}
