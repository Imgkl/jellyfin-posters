const api = {
  async post(url, body) {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "Request failed");
    }
    return resp.json();
  },

  async get(url) {
    const resp = await fetch(url);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "Request failed");
    }
    return resp.json();
  },

  proxyUrl(url) {
    return `/api/proxy-image?url=${encodeURIComponent(url)}`;
  },
};
