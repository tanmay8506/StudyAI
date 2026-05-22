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
    const { data, error } = await supabase
        .from("papers")
        .select("*")
        .eq("upc", upc)
        .single();

    if (error) {
        console.error("[getPaper] error:", error.message);
        return null;
    }
    return data as Paper;
}

export async function getUnitsForPaper(upc: string): Promise<Unit[]> {
    const { data, error } = await supabase
        .from("units")
        .select("*")
        .eq("upc", upc)
        .order("unit_number", { ascending: true });

    if (error) {
        console.error("[getUnitsForPaper] error:", error.message);
        return [];
    }
    return (data ?? []) as Unit[];
}

export async function getTopicsForUnit(unitId: string): Promise<Topic[]> {
    const { data, error } = await supabase
        .from("topics")
        .select("*")
        .eq("unit_id", unitId)
        .order("topic_number", { ascending: true });

    if (error) {
        console.error("[getTopicsForUnit] error:", error.message);
        return [];
    }
    return (data ?? []) as Topic[];
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
        .limit(1)
        .single();

    if (error) {
        if (error.code === "PGRST116") return null;
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