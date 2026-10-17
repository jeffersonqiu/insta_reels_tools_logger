const HEALTH_URL = "https://instareelstoolslogger-production.up.railway.app/health/db";
const TIMEOUT_MS = 12_000;

// Single health-check implementation shared by the fetch and scheduled handlers.
// Resolves on any 2xx; throws otherwise. Never logs the response body.
async function checkDatabaseHealth() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(HEALTH_URL, { signal: controller.signal });
    if (!res.ok) throw new Error(`Database health check failed: HTTP ${res.status}`);
    console.log("Database health check OK");
  } finally {
    clearTimeout(timer);
  }
}

export default {
  async scheduled(_event, _env, ctx) {
    // Rejection is logged by the runtime and marks the cron invocation as failed.
    ctx.waitUntil(checkDatabaseHealth().catch((err) => {
      console.error(err instanceof Error && err.name === "AbortError" ? "Database health check timed out" : String(err));
      throw err;
    }));
  },

  async fetch() {
    try {
      await checkDatabaseHealth();
      return Response.json({ status: "ok" });
    } catch (err) {
      console.error(err instanceof Error && err.name === "AbortError" ? "Database health check timed out" : String(err));
      return Response.json({ status: "unavailable" }, { status: 503 });
    }
  },
};
