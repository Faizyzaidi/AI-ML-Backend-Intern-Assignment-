"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchRoles, startSession, RoleInfo } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [rolesLoading, setRolesLoading] = useState(true);
  const [rolesError, setRolesError] = useState<string | null>(null);

  const [selectedRole, setSelectedRole] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRoles()
      .then((data) => {
        setRoles(data);
        if (data.length > 0) setSelectedRole(data[0].role);
      })
      .catch((err) => setRolesError(err.message))
      .finally(() => setRolesLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!selectedRole) {
      setError("Please select a target role.");
      return;
    }
    if (!resumeFile) {
      setError("Please upload your resume (PDF or TXT).");
      return;
    }

    setSubmitting(true);
    try {
      const result = await startSession(selectedRole, resumeFile);
      sessionStorage.setItem("session_id", result.session_id);
      sessionStorage.setItem("role", result.role);
      sessionStorage.setItem(
        "resume_profile",
        JSON.stringify(result.resume_profile)
      );
      router.push("/interview");
    } catch (err: any) {
      setError(err.message || "Something went wrong starting the session.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="space-y-6">
      <div className="card">
        <h1 className="text-xl font-semibold">Start a screening interview</h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload a resume and pick a target role. Questions are generated
          dynamically from a role-specific knowledge base and personalized to
          the resume.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div>
            <label className="mb-1.5 block text-sm font-medium">
              Target role
            </label>
            {rolesLoading ? (
              <p className="text-sm text-slate-400">Loading roles…</p>
            ) : rolesError ? (
              <p className="text-sm text-red-600">
                Could not load roles: {rolesError}. Is the backend running at
                the configured API URL?
              </p>
            ) : roles.length === 0 ? (
              <p className="text-sm text-amber-600">
                No roles found. Ingest a knowledge base first (see backend
                README, `python -m app.rag.ingest`).
              </p>
            ) : (
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
              >
                {roles.map((r) => (
                  <option key={r.role} value={r.role}>
                    {r.display_name} ({r.document_count} indexed chunks)
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium">
              Resume (PDF or TXT, max 5MB)
            </label>
            <input
              type="file"
              accept=".pdf,.txt"
              onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
            />
            {resumeFile && (
              <p className="mt-1 text-xs text-slate-500">
                Selected: {resumeFile.name}
              </p>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={submitting || rolesLoading || roles.length === 0}
            className="btn-primary w-full"
          >
            {submitting ? "Preparing your interview…" : "Start interview"}
          </button>
        </form>
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold text-slate-700">How it works</h2>
        <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-sm text-slate-600">
          <li>Your resume is parsed to extract skills, technologies, and domains.</li>
          <li>
            Those signals, combined with the selected role, generate targeted
            retrieval queries against a role-specific knowledge base.
          </li>
          <li>
            Retrieved passages ground a set of interview questions — no
            generic templates.
          </li>
          <li>You answer questions one at a time in a structured flow.</li>
          <li>You get a final structured summary of the session.</li>
        </ol>
      </div>
    </main>
  );
}
