import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

type IngestEvent = {
  user_id: string;
  device_id?: string;
  client_name?: string;
  source: string;
  event_type: string;
  url?: string | null;
  title?: string | null;
  category?: string | null;
  selected_text?: string | null;
  content_text?: string | null;
  process_name?: string | null;
  timestamp?: string;
};

function json(status: number, payload: Record<string, unknown>) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-ingest-key",
    },
  });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-ingest-key",
      },
    });
  }

  if (req.method !== "POST") {
    return json(405, { error: "Method not allowed" });
  }

  const ingestKey = Deno.env.get("NEUROWEAVE_INGEST_KEY");
  const requestKey = req.headers.get("x-ingest-key") || "";
  if (!ingestKey || requestKey !== ingestKey) {
    return json(401, { error: "Invalid ingest key" });
  }

  let payload: IngestEvent;
  try {
    payload = await req.json();
  } catch {
    return json(400, { error: "Invalid JSON payload" });
  }

  if (!payload?.user_id || !payload?.source || !payload?.event_type) {
    return json(400, { error: "Missing required fields: user_id, source, event_type" });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  const supabase = createClient(supabaseUrl, serviceRoleKey, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  });

  const createdAt = payload.timestamp || new Date().toISOString();
  const dedupeRaw = [
    payload.user_id,
    payload.device_id || "",
    payload.event_type,
    payload.title || "",
    createdAt.slice(0, 16),
  ].join("|");
  const hashBuffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(dedupeRaw));
  const dedupeKey = Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  const eventRow = {
    dedupe_key: dedupeKey,
    user_id: payload.user_id,
    device_id: payload.device_id || null,
    client_name: payload.client_name || null,
    source: payload.source,
    event_type: payload.event_type,
    url: payload.url || null,
    title: payload.title || null,
    category: payload.category || null,
    selected_text: payload.selected_text || null,
    content_text: payload.content_text || null,
    process_name: payload.process_name || null,
    created_at: createdAt,
    received_at: new Date().toISOString(),
  };

  const { error: eventError } = await supabase
    .from("events_raw")
    .insert(eventRow, { returning: "minimal" });

  if (eventError && !String(eventError.message).toLowerCase().includes("duplicate key")) {
    return json(500, { error: "Failed to insert event", details: eventError.message });
  }

  if (payload.device_id && payload.client_name) {
    const { error: deviceError } = await supabase
      .from("devices_state")
      .upsert(
        {
          user_id: payload.user_id,
          device_id: payload.device_id,
          client_name: payload.client_name,
          last_seen_at: new Date().toISOString(),
        },
        { onConflict: "user_id,device_id", ignoreDuplicates: false }
      );
    if (deviceError) {
      return json(500, { error: "Failed to upsert device", details: deviceError.message });
    }
  }

  return json(202, { accepted: true, dedupe_key: dedupeKey });
});
