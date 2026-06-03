import { NextRequest, NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase-server";

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ upc: string }> }
) {
    try {
        const { upc } = await params;
        const supabase = createServerSupabaseClient();

        const { data, error } = await supabase
            .from("papers")
            .select("*")
            .eq("upc", upc)
            .maybeSingle();

        if (error) {
            return NextResponse.json({ error: error.message }, { status: 500 });
        }

        if (!data) {
            return NextResponse.json({ error: "Paper not found" }, { status: 404 });
        }

        return NextResponse.json(data);
    } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Internal server error";
        return NextResponse.json({ error: message }, { status: 500 });
    }
}
