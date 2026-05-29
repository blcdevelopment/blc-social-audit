import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";

export default function AuditDetail() {
  const router = useRouter();
  const { id } = router.query;

  return (
    <>
      <Head>
        <title>Audit Detail | BLC Website Audit</title>
      </Head>
      <main className="shell">
        <section className="panel">
          <p className="eyebrow">Audit Detail</p>
          <h1>{typeof id === "string" ? id : "Loading audit"}</h1>
          <p>The progress and PDF download experience is implemented in Epic P1-E5.</p>
          <nav className="actions" aria-label="Page navigation">
            <Link href="/audits">Back to Audit History</Link>
          </nav>
        </section>
      </main>
    </>
  );
}
