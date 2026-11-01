/**
 * LeadPilot AI — API client
 */
const BASE = '';   // same origin

export const api = {
  async get(path) {
    const res = await fetch(BASE + path);
    if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
    return res.json();
  },

  async post(path, body) {
    const res = await fetch(BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `API ${path} → ${res.status}`);
    }
    return res.json();
  },

  async put(path, body) {
    const res = await fetch(BASE + path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
    return res.json();
  },

  async delete(path) {
    const res = await fetch(BASE + path, { method: 'DELETE' });
    if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
    return res.json();
  },

  streamSSE(path, onMessage, onDone) {
    const es = new EventSource(path);
    es.onmessage = e => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'done') {
          es.close();
          onDone(data);
        } else {
          onMessage(data);
        }
      } catch (err) {
        console.error('SSE JSON parse error:', err);
      }
    };
    es.onerror = () => {
      es.close();
      onDone({ status: 'error', error: 'Connection lost' });
    };
    return es;
  },
};

