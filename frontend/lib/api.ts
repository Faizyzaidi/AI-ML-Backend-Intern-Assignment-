export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ResumeProfile {
  skills: string[];
  technologies: string[];
  domains: string[];
  experience_level: string;
}

export interface QuestionOut {
  id: string;
  order_index: number;
  text: string;
  topic?: string | null;
  difficulty?: string | null;
}

export interface SessionStartResponse {
  session_id: string;
  role: string;
  resume_profile: ResumeProfile;
  total_questions: number;
  first_question: QuestionOut | null;
}

export interface NextQuestionResponse {
  done: boolean;
  question: QuestionOut | null;
  progress: { answered: number; total: number };
}

export interface QAPair {
  question: string;
  topic?: string | null;
  difficulty?: string | null;
  answer?: string | null;
  quality_score?: number | null;
}

export interface SessionSummaryResponse {
  session_id: string;
  role: string;
  resume_profile: ResumeProfile;
  status: string;
  started_at: string;
  completed_at?: string | null;
  qa_pairs: QAPair[];
  topics_covered: string[];
  average_quality_score?: number | null;
  insights: string[];
}

export interface RoleInfo {
  role: string;
  display_name: string;
  document_count: number;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore parse errors, use default detail
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function fetchRoles(): Promise<RoleInfo[]> {
  const res = await fetch(`${API_URL}/api/roles`, { cache: "no-store" });
  return handleResponse<RoleInfo[]>(res);
}

export async function startSession(
  role: string,
  resumeFile: File
): Promise<SessionStartResponse> {
  const formData = new FormData();
  formData.append("role", role);
  formData.append("resume", resumeFile);

  const res = await fetch(`${API_URL}/api/session/start`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<SessionStartResponse>(res);
}

export async function getNextQuestion(
  sessionId: string
): Promise<NextQuestionResponse> {
  const res = await fetch(`${API_URL}/api/session/${sessionId}/next-question`, {
    cache: "no-store",
  });
  return handleResponse<NextQuestionResponse>(res);
}

export async function submitAnswer(
  sessionId: string,
  questionId: string,
  answerText: string
): Promise<void> {
  const res = await fetch(`${API_URL}/api/session/${sessionId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId, answer_text: answerText }),
  });
  await handleResponse(res);
}

export async function getSummary(
  sessionId: string
): Promise<SessionSummaryResponse> {
  const res = await fetch(`${API_URL}/api/session/${sessionId}/summary`, {
    cache: "no-store",
  });
  return handleResponse<SessionSummaryResponse>(res);
}
