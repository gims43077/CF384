/** Integration helper for an extension service worker/page; not a complete extension. */
export async function predictBlob(blob, {
  apiKey,
  baseUrl = 'http://127.0.0.1:8000',
  model = 'adapted',
  timeoutMs = 30000,
} = {}) {
  if (!apiKey) throw new Error('API key is required');
  if (!['original', 'adapted', 'lowres'].includes(model)) throw new Error('Invalid model');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const body = new FormData();
    body.append('file', blob, 'image');
    const response = await fetch(`${baseUrl.replace(/\/$/, '')}/v1/predict?model=${model}`, {
      method: 'POST', headers: { 'X-API-Key': apiKey }, body, signal: controller.signal,
    });
    const text = await response.text();
    let payload;
    try { payload = JSON.parse(text); }
    catch { throw new Error(`Unexpected server response: HTTP ${response.status}`); }
    if (!response.ok) {
      const error = new Error(payload.error?.message ?? `HTTP ${response.status}`);
      error.status = response.status;
      error.code = payload.error?.code;
      error.retryAfter = Number(response.headers.get('Retry-After') || '1');
      throw error;
    }
    return payload;
  } finally { clearTimeout(timeout); }
}
