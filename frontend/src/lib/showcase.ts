// What the start page shows before anyone types: REAL outputs and REAL measured results, never
// invented ones. Update these when the evaluations are re-run.
import type { Category, Language, Priority } from "@/lib/types";

export interface ShowcaseExample {
  question: string;
  category: Category;
  priority: Priority;
  topScore: number;
  minScore: number;
  reply: string;
  sourceSection: string;
  sourceTitle: string;
}

// From the dev run of 2026-10-23: eval/results_high.json (labels, run 1) and
// eval/pipeline_results_dev.json (score, reply, source); tickets tr-023 and en-003. The replies
// are shortened to their main sentences (the polite closing line is left out); nothing is added.
export const EXAMPLES: Record<Language, ShowcaseExample> = {
  tr: {
    question: "Kaydımı sildirdim, bu dönem ödediğim harcın iadesini alabilir miyim?",
    category: "billing",
    priority: "low",
    topScore: 0.81,
    minScore: 0.65,
    reply:
      "Kayıt yaptırıp kendi isteğiyle kaydını sildiren öğrencilerin katkı payı ve öğrenim ücretleri geri ödenmemektedir. Dolayısıyla, bu dönem ödemiş olduğunuz harç ücretinin iadesi yapılmamaktadır.",
    sourceSection: "Kayıt sildirince iade",
    sourceTitle: "Katkı Payı, Öğrenim Ücreti ve İadeler",
  },
  en: {
    question: "How can I get an official transcript? I need it for an internship application.",
    category: "academic_records",
    priority: "low",
    topScore: 0.77,
    minScore: 0.65,
    reply:
      "You can obtain your official transcript by applying with a petition to the student affairs office of your academic unit, or you can get it directly through e-Devlet.",
    sourceSection: "Student certificate and transcript",
    sourceTitle: "Student Number, OBS Password, Documents and the Student ID Card",
  },
};

// Measured results (README "Gerçekçi talepler (Phase 8)"; eval/*_phase8.json, eval/retrieval_results.json).
export const RESULTS = {
  missedEscalations: { missed: 0, of: 11 }, // locked realistic set, both runs
  rightDocumentTop3: { hits: 30, of: 30 }, // Phase 8 retrieval, hit@3
  unsafeAutoSends: { unsafe: 0, of: 40 }, // Phase 8 pipeline
  documents: 24, // data/knowledge_base: 12 topics x TR + EN
};
