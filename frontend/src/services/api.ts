import { TelemetrySnapshot, InvestigationResult, GrafanaHealth, ChaosState } from "../types/telemetry";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://continuity-api-121300560395.us-central1.run.app";
const DEMO_KEY = process.env.NEXT_PUBLIC_DEMO_KEY || "continuity-demo-secret-2026";

export class ApiService {
  private static async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    try {
      const res = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          "X-Continuity-Demo-Key": DEMO_KEY,
          ...(options?.headers || {}),
        },
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      return await res.json();
    } catch (err) {
      console.warn(`API request to ${endpoint} failed:`, err);
      throw err;
    }
  }

  // Telemetry APIs
  static async getCurrentTelemetry(): Promise<TelemetrySnapshot> {
    return this.request<TelemetrySnapshot>("/api/telemetry/current");
  }

  static async getTelemetryHistory(): Promise<TelemetrySnapshot[]> {
    return this.request<TelemetrySnapshot[]>("/api/telemetry/history");
  }

  static async getGrafanaHealth(): Promise<GrafanaHealth> {
    return this.request<GrafanaHealth>("/api/telemetry/grafana-health");
  }

  // Agent APIs
  static async getAgentStatus(): Promise<any> {
    return this.request<any>("/api/agent/status");
  }

  static async investigateAndRemediate(): Promise<InvestigationResult> {
    return this.request<InvestigationResult>("/api/agent/investigate-and-remediate", {
      method: "POST",
    });
  }

  static async getInvestigationHistory(): Promise<InvestigationResult[]> {
    return this.request<InvestigationResult[]>("/api/agent/history");
  }

  // Chaos APIs
  static async getChaosState(): Promise<ChaosState> {
    return this.request<ChaosState>("/api/chaos/state");
  }

  static async injectCdnOutage(): Promise<ChaosState> {
    return this.request<ChaosState>("/api/chaos/inject-cdn-outage", { method: "POST" });
  }

  static async injectDrmTimeout(): Promise<ChaosState> {
    return this.request<ChaosState>("/api/chaos/inject-drm-timeout", { method: "POST" });
  }

  static async injectIspDrop(): Promise<ChaosState> {
    return this.request<ChaosState>("/api/chaos/inject-isp-drop", { method: "POST" });
  }

  static async remediate(): Promise<ChaosState> {
    return this.request<ChaosState>("/api/chaos/remediate", { method: "POST" });
  }

  static async resetChaos(): Promise<ChaosState> {
    return this.request<ChaosState>("/api/chaos/reset", { method: "POST" });
  }

  // SSE Stream Generator with auto-reconnect
  static createTelemetryEventSource(onMessage: (data: TelemetrySnapshot) => void, onError?: (err: any) => void): () => void {
    let eventSource: EventSource | null = null;
    let isCancelled = false;

    const connect = () => {
      if (isCancelled) return;
      try {
        eventSource = new EventSource(`${API_BASE_URL}/api/telemetry/stream`);

        eventSource.onmessage = (event) => {
          try {
            const data: TelemetrySnapshot = JSON.parse(event.data);
            onMessage(data);
          } catch (e) {
            console.error("Failed to parse SSE telemetry packet", e);
          }
        };

        eventSource.onerror = (err) => {
          if (onError) onError(err);
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          if (!isCancelled) {
            setTimeout(connect, 2000);
          }
        };
      } catch (e) {
        if (!isCancelled) {
          setTimeout(connect, 3000);
        }
      }
    };

    connect();

    return () => {
      isCancelled = true;
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
    };
  }
}
