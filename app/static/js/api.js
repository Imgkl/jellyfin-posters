const api = {
  async request(method, url, body) {
    const requestId = `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    const startedAt = performance.now();
    const path = new URL(url, window.location.href).pathname;
    const headers = { "X-JP-Diagnostic-ID": requestId };
    const options = { method, headers };

    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }

    jpDiagnostics.log("api.request.start", { request_id: requestId, method, path });
    try {
      const resp = await fetch(url, options);
      jpDiagnostics.log("api.response.headers", {
        request_id: requestId,
        server_request_id: resp.headers.get("X-JP-Diagnostic-ID"),
        method,
        path,
        status: resp.status,
        elapsed_ms: Math.round((performance.now() - startedAt) * 10) / 10,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || "Request failed");
      }
      const data = await resp.json();
      jpDiagnostics.log("api.request.complete", {
        request_id: requestId,
        method,
        path,
        elapsed_ms: Math.round((performance.now() - startedAt) * 10) / 10,
      });
      return data;
    } catch (error) {
      jpDiagnostics.log("api.request.error", {
        request_id: requestId,
        method,
        path,
        elapsed_ms: Math.round((performance.now() - startedAt) * 10) / 10,
      });
      throw error;
    }
  },

  async post(url, body) {
    return this.request("POST", url, body);
  },

  async get(url) {
    return this.request("GET", url);
  },

  proxyUrl(url) {
    return `/api/proxy-image?url=${encodeURIComponent(url)}`;
  },
};
