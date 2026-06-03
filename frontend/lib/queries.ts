import { supabase } from "./supabase";
import type {
    Paper,
    Unit,
    Topic,
    FormulaSheet,
    ProblemSet,
} from "@/types/database";
import type { RealtimeChannel } from "@supabase/supabase-js";

// ─────────────────────────────────────────
// READS
// ─────────────────────────────────────────

export async function getPaper(upc: string): Promise<Paper | null> {
    try {
        const res = await fetch(`/api/paper/${upc}`, { cache: "no-store" });
        if (res.status === 404) return null;
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            console.error("[getPaper] error:", body.error ?? res.statusText);
            return null;
        }
        return (await res.json()) as Paper;
    } catch (err) {
        console.error("[getPaper] fetch error:", err);
        return null;
    }
}

export async function getUnitsForPaper(upc: string): Promise<Unit[]> {
    try {
        const res = await fetch(`/api/paper/${upc}/units`, { cache: "no-store" });
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            console.error("[getUnitsForPaper] error:", body.error ?? res.statusText);
            return [];
        }
        return (await res.json()) as Unit[];
    } catch (err) {
        console.error("[getUnitsForPaper] fetch error:", err);
        return [];
    }
}

export async function getTopicsForUnit(unitId: string): Promise<Topic[]> {
    try {
        const res = await fetch(`/api/unit/${unitId}/topics`, { cache: "no-store" });
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            console.error("[getTopicsForUnit] error:", body.error ?? res.statusText);
            return [];
        }
        return (await res.json()) as Topic[];
    } catch (err) {
        console.error("[getTopicsForUnit] fetch error:", err);
        return [];
    }
}

export async function getFormulaSheetsForUnit(
    unitId: string
): Promise<FormulaSheet[]> {
    const { data, error } = await supabase
        .from("formula_sheets")
        .select("*")
        .eq("unit_id", unitId);

    if (error) {
        console.error("[getFormulaSheetsForUnit] error:", error.message);
        return [];
    }
    return (data ?? []) as FormulaSheet[];
}

export async function getProblemSetForUnit(
    unitId: string
): Promise<ProblemSet | null> {
    const { data, error } = await supabase
        .from("problem_sets")
        .select("*")
        .eq("unit_id", unitId)
        .maybeSingle();

    if (error) {
        console.error("[getProblemSetForUnit] error:", error.message);
        return null;
    }
    return data as ProblemSet;
}

// ─────────────────────────────────────────
// REALTIME SUBSCRIPTIONS
// ─────────────────────────────────────────

export function subscribeToUnitStatus(
    upc: string,
    onUpdate: (unit: Unit) => void
): RealtimeChannel {
    const channel = supabase
        .channel(`units:upc:${upc}`)
        .on(
            "postgres_changes",
            {
                event: "*",
                schema: "public",
                table: "units",
                filter: `upc=eq.${upc}`,
            },
            (payload) => {
                if (payload.new) {
                    onUpdate(payload.new as Unit);
                }
            }
        )
        .subscribe();

    return channel;
}

export function subscribeToTopicStatus(
    unitId: string,
    onUpdate: (topic: Topic) => void
): RealtimeChannel {
    const channel = supabase
        .channel(`topics:unit_id:${unitId}`)
        .on(
            "postgres_changes",
            {
                event: "*",
                schema: "public",
                table: "topics",
                filter: `unit_id=eq.${unitId}`,
            },
            (payload) => {
                if (payload.new) {
                    onUpdate(payload.new as Topic);
                }
            }
        )
        .subscribe();

    return channel;
}

// ─────────────────────────────────────────
// WRITES
// ─────────────────────────────────────────

interface FlagFieldParams {
    topicId: string;
    fieldName: string;
    issue: string;
    sessionId: string;
}

export async function flagField(params: FlagFieldParams): Promise<void> {
    const { error } = await supabase.from("field_flags").insert({
        topic_id: params.topicId,
        field_name: params.fieldName,
        flag_type: params.issue,
        session_id: params.sessionId,
        status: "open",
    });

    if (error) {
        console.error("[flagField] error:", error.message);
        throw new Error(error.message);
    }
}

interface SubmitPYQParams {
    upc: string;
    yearTaggedByStudent: number;
    fileUrl: string;
    sessionId: string;
    rewardType: "early_access" | "cross_paper_credit";
    rewardPaperUpc?: string;
}

export async function submitPYQ(params: SubmitPYQParams): Promise<void> {
    const { error } = await supabase.from("pyq_submissions").insert({
        upc: params.upc,
        year_tagged_by_student: params.yearTaggedByStudent,
        file_url: params.fileUrl,
        reward_type: params.rewardType,
        reward_paper_upc: params.rewardPaperUpc ?? null,
        verification_status: "pending",
        reward_issued: false,
        file_deleted: false,
    });

    if (error) {
        console.error("[submitPYQ] error:", error.message);
        throw new Error(error.message);
    }
}