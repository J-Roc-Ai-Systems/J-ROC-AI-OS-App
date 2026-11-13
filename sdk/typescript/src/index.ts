/** J-ROC AI platform client shared by browser and server-side TypeScript applications. */
export type JsonObject = Record<string, unknown>;
export class JrocAiPlatformError extends Error {
  constructor(public readonly status: number, message: string) { super(message); }
}
export class JrocAiPlatformClient {
  private readonly baseUrl: string;
  constructor(baseUrl: string, private readonly accessToken: string, private readonly fetcher: typeof fetch = fetch) {
    const parsed = new URL(baseUrl);
    if (parsed.protocol !== "https:" && parsed.hostname !== "localhost" && parsed.hostname !== "127.0.0.1") {
      throw new Error("Use HTTPS except for loopback development.");
    }
    if (!accessToken) throw new Error("A gateway access token is required.");
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }
  async request<T>(method: string, path: string, payload?: JsonObject): Promise<T> {
    if (!path.startsWith("/") || path.split("/").includes("..")) throw new Error("Invalid API path.");
    const response = await this.fetcher(this.baseUrl + path, {
      method,
      headers: { Authorization: `Bearer ${this.accessToken}`, Accept: "application/json", ...(payload ? {"Content-Type":"application/json"} : {}) },
      body: payload ? JSON.stringify(payload) : undefined,
      credentials: "omit",
      cache: "no-store"
    });
    const text = await response.text();
    if (!response.ok) throw new JrocAiPlatformError(response.status, text.slice(0, 2048));
    return (text ? JSON.parse(text) : null) as T;
  }
  health<T = JsonObject>() { return this.request<T>("GET", "/health"); }
  waves<T = JsonObject>() { return this.request<T>("GET", "/platform/v1/waves"); }
  domainCatalog<T = JsonObject>() { return this.request<T>("GET", "/platform/v1/domain/catalog"); }
  listDomainRecords<T = JsonObject>(domain: string, limit = 100) {
    return this.request<T>("GET", `/platform/v1/domain/${encodeURIComponent(domain)}/records?limit=${Math.max(1, Math.min(limit, 500))}`);
  }
  createDomainRecord<T = JsonObject>(domain: string, payload: JsonObject) {
    return this.request<T>("POST", `/platform/v1/domain/${encodeURIComponent(domain)}/records`, payload);
  }
}
