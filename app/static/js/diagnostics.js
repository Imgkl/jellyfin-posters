(() => {
  const MAX_ENTRIES = 3000;
  const entries = [];
  const bootTime = performance.now();
  let sequence = 0;

  function round(value) {
    return Number.isFinite(value) ? Math.round(value * 10) / 10 : null;
  }

  function log(event, details = {}) {
    const record = {
      sequence: ++sequence,
      timestamp: new Date().toISOString(),
      since_boot_ms: round(performance.now() - bootTime),
      event,
      ...details,
    };
    entries.push(record);
    if (entries.length > MAX_ENTRIES) entries.splice(0, entries.length - MAX_ENTRIES);
    console.info(`[JP-DIAG] ${event}`, record);
    return record;
  }

  function snapshot() {
    return {
      generated_at: new Date().toISOString(),
      user_agent: navigator.userAgent,
      visibility_state: document.visibilityState,
      entries: entries.slice(),
    };
  }

  async function copy() {
    const text = JSON.stringify(snapshot(), null, 2);
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      console.info(`[JP-DIAG] copied ${entries.length} diagnostic entries to clipboard`);
      return entries.length;
    }
    console.warn("[JP-DIAG] Clipboard API unavailable; use jpDiagnostics.download() instead");
    return text;
  }

  function exportText() {
    return JSON.stringify(snapshot(), null, 2);
  }

  function download() {
    const blob = new Blob([exportText()], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `jellyfin-posters-diagnostics-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    console.info(`[JP-DIAG] downloaded ${entries.length} diagnostic entries`);
    return entries.length;
  }

  function clear() {
    entries.length = 0;
    sequence = 0;
    log("diagnostics.cleared");
  }

  window.jpDiagnostics = { log, snapshot, copy, download, export: exportText, clear };

  if ("PerformanceObserver" in window) {
    try {
      const observer = new PerformanceObserver((list) => {
        for (const resource of list.getEntries()) {
          const path = new URL(resource.name, window.location.href).pathname;
          if (path !== "/api/proxy-image") continue;
          log("image.resource.complete", {
            path,
            protocol: resource.nextHopProtocol || "unknown",
            start_ms: round(resource.startTime),
            fetch_start_ms: round(resource.fetchStart),
            request_start_ms: round(resource.requestStart),
            response_start_ms: round(resource.responseStart),
            response_end_ms: round(resource.responseEnd),
            queue_before_request_ms: round(resource.requestStart - resource.startTime),
            server_wait_ms: round(resource.responseStart - resource.requestStart),
            download_ms: round(resource.responseEnd - resource.responseStart),
            duration_ms: round(resource.duration),
            transfer_size: resource.transferSize,
          });
        }
      });
      observer.observe({ type: "resource", buffered: true });
    } catch {
      log("performance_observer.error");
    }
  }

  document.addEventListener("visibilitychange", () => {
    log("document.visibility", { state: document.visibilityState });
  });

  log("diagnostics.ready", { max_entries: MAX_ENTRIES });
})();
