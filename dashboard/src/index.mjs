// Neon Function: backend API + dashboard page. Reads only saved, processed results from Postgres
// (DATABASE_URL is injected by Neon). No model calls happen here.
import pg from "pg";
import PAGE from "./page.html";

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 5 });
pool.on("error", () => {}); // idle-client drops (scale-to-zero) are expected; next query reconnects

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "public, max-age=60" },
  });

const q = async (sql, params = []) => (await pool.query(sql, params)).rows;

const TOPICS = ["access", "usability", "playback", "downloads", "catalog", "billing", "support", "other"];
const INTENTS = ["cancellation", "complaint", "request", "praise", "unclear"];

const routes = {
  "/api/summary": async () => {
    const kv = Object.fromEntries((await q("SELECT key, value FROM run_summary")).map((r) => [r.key, r.value]));
    const quarantine = await q("SELECT reason, n FROM quarantine_summary ORDER BY n DESC");
    const evaluation = Object.fromEntries((await q("SELECT key, value FROM evaluation")).map((r) => [r.key, r.value]));
    const [agg] = await q(`SELECT COUNT(*)::int AS completed,
        COUNT(*) FILTER (WHERE intent IN ('complaint','cancellation'))::int AS complaints,
        COUNT(*) FILTER (WHERE intent = 'cancellation')::int AS cancellations,
        COUNT(*) FILTER (WHERE needs_review)::int AS needs_review,
        COUNT(*) FILTER (WHERE cache_source_id IS NOT NULL)::int AS cache_reused,
        ROUND(AVG(severity) FILTER (WHERE intent IN ('complaint','cancellation')), 3)::float AS mean_complaint_severity,
        ROUND(AVG(sentiment)::numeric, 3)::float AS mean_sentiment FROM reviews`);
    return { ...kv, quarantine, evaluation, aggregates: agg };
  },
  "/api/issues": async () => ({
    issues: await q("SELECT * FROM issues ORDER BY rank"),
    claims: await q("SELECT * FROM claims ORDER BY claim_id"),
  }),
  "/api/memo": async () => (await q("SELECT recommended_issue_id, markdown, check_problems FROM memo WHERE id = 1"))[0],
  "/api/distribution": async () =>
    q("SELECT topic, intent, COUNT(*)::int AS n, ROUND(AVG(severity),2)::float AS mean_severity FROM reviews GROUP BY 1,2"),
  "/api/trend": async () =>
    q(`SELECT month, SUM(n)::int AS total,
          SUM(n) FILTER (WHERE intent IN ('complaint','cancellation'))::int AS complaints
       FROM topic_month GROUP BY month ORDER BY month`),
};

async function reviewsFor(url) {
  const p = url.searchParams;
  const where = [], params = [];
  const issue = p.get("issue"), topic = p.get("topic"), intent = p.get("intent");
  if (issue) { params.push(issue); where.push(`issue_id = $${params.length}`); }
  if (topic && TOPICS.includes(topic)) { params.push(topic); where.push(`topic = $${params.length}`); }
  if (intent && INTENTS.includes(intent)) { params.push(intent); where.push(`intent = $${params.length}`); }
  const limit = Math.min(Math.max(parseInt(p.get("limit") || "25", 10) || 25, 1), 100);
  params.push(limit);
  return q(`SELECT review_id, review_text, review_rating, review_timestamp, topic, intent, severity, sentiment,
                   needs_review, evidence_quote, issue_id, cache_source_id, decided_by
            FROM reviews ${where.length ? "WHERE " + where.join(" AND ") : ""}
            ORDER BY severity DESC, md5(review_id) LIMIT $${params.length}`, params);
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    try {
      if (url.pathname === "/" || url.pathname === "/index.html")
        return new Response(PAGE, { headers: { "content-type": "text/html; charset=utf-8" } });
      if (url.pathname === "/api/reviews") return json(await reviewsFor(url));
      if (url.pathname === "/api/health") return json({ ok: true, db: (await q("SELECT 1 AS ok"))[0].ok === 1 });
      const handler = routes[url.pathname];
      if (handler) return json(await handler());
      return json({ error: "not found" }, 404);
    } catch (e) {
      return json({ error: String(e.message || e) }, 500);
    }
  },
};
