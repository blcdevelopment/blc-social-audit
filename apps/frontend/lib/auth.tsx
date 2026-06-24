import { createContext, useContext, type ReactNode } from "react";

import { ClerkProvider, SignedIn, SignedOut, useAuth } from "@clerk/nextjs";

import Welcome from "../components/Welcome";

// Clerk is enabled only when a publishable key is present. With no key (local dev / docker),
// the UI runs in OPEN mode — mirroring the API being open when CLERK_ISSUER is empty.
export const CLERK_ENABLED = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

type GetToken = () => Promise<string | null>;

const nullToken: GetToken = async () => null;
const AuthTokenContext = createContext<GetToken>(nullToken);

export function useAuthToken(): GetToken {
  return useContext(AuthTokenContext);
}

function ClerkTokenBridge({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();
  return <AuthTokenContext.Provider value={getToken}>{children}</AuthTokenContext.Provider>;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function AppAuthProvider({ children, pageProps }: { children: ReactNode; pageProps: any }) {
  if (!CLERK_ENABLED) {
    return <>{children}</>;
  }
  return (
    <ClerkProvider {...pageProps}>
      <SignedIn>
        <ClerkTokenBridge>{children}</ClerkTokenBridge>
      </SignedIn>
      <SignedOut>
        <Welcome />
      </SignedOut>
    </ClerkProvider>
  );
}
