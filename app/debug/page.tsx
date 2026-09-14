"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type DebugData = {
  configured?: boolean;
  error?: string;
  generatedAt?: string;
  runs?: Record<string, unknown>[];
  stories?: Record<string, unknown>[];
  failures?: Record<string, unknown>[];
  preference?: Record<string, unknown> | null;
  feedback?: Record<string, unknown>[];
};

function JsonBlock({ value }: { value: unknown }) {
  return <pre>{JSON.stringify(value, null, 2)}</pre>;
}

export default function DebugPage() {
  const [data, setData] = useState<DebugData | null>(null);

  useEffect(() => {
    fetch("/api/debug", { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "debug_unavailable");
        return body;
      })
      .then(setData)
      .catch((error) => setData({ error: String(error) }));
  }, []);

  if (!data) return <main className="debug-page">loading debug data…</main>;

  return (
    <main className="debug-page">
      <header>
        <div>
          <Link href="/">← feed</Link>
          <h1>AI × BIO / debug</h1>
        </div>
        <time>{data.generatedAt || "not available"}</time>
      </header>

      {data.error ? <section><h2>error</h2><JsonBlock value={data} /></section> : null}

      <section>
        <h2>processing failures ({data.failures?.length || 0})</h2>
        <JsonBlock value={data.failures || []} />
      </section>

      <section>
        <h2>preference profile</h2>
        <JsonBlock value={data.preference} />
      </section>

      <section>
        <h2>published stories ({data.stories?.length || 0})</h2>
        <JsonBlock value={data.stories || []} />
      </section>

      <section>
        <h2>pipeline runs ({data.runs?.length || 0})</h2>
        <JsonBlock value={data.runs || []} />
      </section>

      <section>
        <h2>feedback events ({data.feedback?.length || 0})</h2>
        <JsonBlock value={data.feedback || []} />
      </section>
    </main>
  );
}
