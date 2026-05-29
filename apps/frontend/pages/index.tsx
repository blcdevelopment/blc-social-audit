import Head from "next/head";
import Link from "next/link";

export default function Home() {
  return (
    <>
      <Head>
        <title>BLC Website Audit</title>
      </Head>
      <main className="shell">
        <section className="panel">
          <p className="eyebrow">Phase 1 Local Operator UI</p>
          <h1>BLC Website Audit</h1>
          <p>
            Frontend scaffold is ready. Audit submission, progress, and history screens are
            implemented in Epic P1-E5.
          </p>
          <nav className="actions" aria-label="Audit navigation">
            <Link href="/audits">Audit History</Link>
          </nav>
        </section>
      </main>
    </>
  );
}
