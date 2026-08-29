"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getSummary, SessionSummaryResponse } from "@/lib/api";

export default function SummaryPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<SessionSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const sid = sessionStorage.getItem("session_id");
    if (!sid) {
      router.replace("/");
      return;
    }
    getSummary(sid)
      .then(setSummary)
      .catch((err) => setError(err.message || "Failed to load summary."))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function startOver() {
    sessionStorage.removeItem("session_id");
    sessionStorage.removeItem("role");
    sessionStorage.removeItem("resume_profile");
    router.push("/");
  }

  if (loading) {
    return (
      <main className="card">
        <p className="text-sm text-slate-500">Building your summary…</p>
      </main>
    );
  }

  if (error || !summary) {
    return (
      <main className="card">
        <p className="text-sm text-red-600">{error || "No summary available."}</p>
        <button className="btn-secondary mt-4" onClick={startOver}>
          Back to start
        </button>
      </main>
    );
  }

  return (
    <main className="space-y-6">
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Interview summary</h1>
            <p className="text-sm text-slate-500">
              Role: <span className="tag">{summary.role}</span>
            </p>
          </div>
          {summary.average_quality_score != null && (
            <div className="text-right">
              <p className="text-2xl font-semibold text-brand-700">
                {Math.round(summary.average_quality_score)}
              </p>
              <p className="text-xs text-slate-500">avg. answer signal</p>
            </div>
          )}
        </div>

        <div className="mt-4 flex flex-wrap gap-1.5">
          {summary.resume_profile.skills.map((s) => (
            <span key={s} className="tag">{s}</span>
          ))}
          {summary.resume_profile.technologies.map((t) => (
            <span key={t} className="tag">{t}</span>
          ))}
        </div>
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold text-slate-700">Insights</h2>
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-slate-700">
          {summary.insights.map((insight, i) => (
            <li key={i}>{insight}</li>
          ))}
        </ul>

        {summary.topics_covered.length > 0 && (
          <>
            <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Topics covered
            </h3>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {summary.topics_covered.map((t) => (
                <span key={t} className="tag">{t}</span>
              ))}
            </div>
          </>
        )}
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-700">
          Full transcript
        </h2>
        {summary.qa_pairs.map((qa, i) => (
          <div key={i} className="card">
            <p className="text-sm font-medium">{qa.question}</p>
            <p className="mt-2 text-sm text-slate-600">
              {qa.answer || <span className="italic text-slate-400">No answer recorded</span>}
            </p>
            {qa.quality_score != null && (
              <p className="mt-2 text-xs text-slate-400">
                Answer signal score: {qa.quality_score}/100
              </p>
            )}
          </div>
        ))}
      </div>

      <button className="btn-secondary w-full" onClick={startOver}>
        Start a new interview
      </button>
    </main>
  );
}
