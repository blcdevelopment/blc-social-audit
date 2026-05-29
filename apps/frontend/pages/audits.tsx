import Head from "next/head";
import Link from "next/link";

export default function Audits() {
  return (
    <>
      <Head>
        <title>Audit History | BLC Website Audit</title>
      </Head>
      <main className="shell">
        <section className="panel">
          <p className="eyebrow">Audit History</p>
          <h1>Recent Audits</h1>
          <p>The API lifecycle is available now. The operator history table arrives in P1-E5.</p>
          <nav className="actions" aria-label="Page navigation">
            <Link href="/">Back to Submission</Link>
          </nav>
        </section>
      </main>
    </>
  );
}
