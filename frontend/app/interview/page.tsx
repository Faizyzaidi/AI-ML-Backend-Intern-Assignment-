"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getNextQuestion, submitAnswer, QuestionOut } from "@/lib/api";

const difficultyColor: Record<string, string> = {
  conceptual: "bg-blue-50 text-blue-700",
  applied: "bg-amber-50 text-amber-700",
  advanced: "bg-purple-50 text-purple-700",
};

export default function InterviewPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [role, setRole] = useState<string>("");

  const [question, setQuestion] = useState<QuestionOut | null>(null);
  const [progress, setProgress] = useState({ answered: 0, total: 0 });
  const [answerText, setAnswerText] = useState("");

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const sid = sessionStorage.getItem("session_id");
    const r = sessionStorage.getItem("role");
    if (!sid) {
      router.replace("/");
      return;
    }
    setSessionId(sid);
    setRole(r || "");
    loadNext(sid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadNext(sid: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await getNextQuestion(sid);
      setProgress(res.progress);
      if (res.done) {
        router.push("/summary");
        return;
      }
      setQuestion(res.question);
      setAnswerText("");
    } catch (err: any) {
      setError(err.message || "Failed to load the next question.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!sessionId || !question || !answerText.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await submitAnswer(sessionId, question.id, answerText.trim());
      await loadNext(sessionId);
    } catch (err: any) {
      setError(err.message || "Failed to submit your answer.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading && !question) {
    return (
      <main className="card">
        <p className="text-sm text-slate-500">Loading your next question…</p>
      </main>
    );
  }

  if (error && !question) {
    return (
      <main className="card">
        <p className="text-sm text-red-600">{error}</p>
        <button className="btn-secondary mt-4" onClick={() => router.push("/")}>
          Back to start
        </button>
      </main>
    );
  }

  const pct =
    progress.total > 0 ? Math.round((progress.answered / progress.total) * 100) : 0;

  return (
    <main className="space-y-4">
      <div className="flex items-center justify-between text-sm text-slate-500">
        <span className="tag">{role}</span>
        <span>
          Question {progress.answered + 1} of {progress.total}
        </span>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-brand-600 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>

      {question && (
        <div className="card">
          <div className="mb-3 flex items-center gap-2">
            {question.difficulty && (
              <span
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                  difficultyColor[question.difficulty] || "bg-slate-100 text-slate-700"
                }`}
              >
                {question.difficulty}
              </span>
            )}
          </div>
          <p className="text-base leading-relaxed">{question.text}</p>

          <form onSubmit={handleSubmit} className="mt-5 space-y-3">
            <textarea
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              rows={6}
              placeholder="Type your answer here…"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={submitting || !answerText.trim()}
              className="btn-primary w-full"
            >
              {submitting ? "Submitting…" : "Submit answer"}
            </button>
          </form>
        </div>
      )}
    </main>
  );
}
