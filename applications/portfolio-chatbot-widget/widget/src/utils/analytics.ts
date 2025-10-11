/**
 * Analytics tracking utilities
 */

export interface AnalyticsEvent {
  event: string;
  properties?: Record<string, any>;
  timestamp: number;
}

export class Analytics {
  private events: AnalyticsEvent[] = [];
  private sessionId?: string;

  constructor(sessionId?: string) {
    this.sessionId = sessionId;
  }

  track(event: string, properties?: Record<string, any>): void {
    const analyticsEvent: AnalyticsEvent = {
      event,
      properties: {
        ...properties,
        session_id: this.sessionId,
      },
      timestamp: Date.now(),
    };

    this.events.push(analyticsEvent);

    // Console log in development
    if (process.env.NODE_ENV !== "production") {
      console.log("[Analytics]", event, properties);
    }

    // In production, you could send to analytics service
    // e.g., Google Analytics, Mixpanel, Segment, etc.
  }

  setSessionId(sessionId: string): void {
    this.sessionId = sessionId;
  }

  getEvents(): AnalyticsEvent[] {
    return this.events;
  }

  clearEvents(): void {
    this.events = [];
  }
}

// Singleton instance
export const analytics = new Analytics();
