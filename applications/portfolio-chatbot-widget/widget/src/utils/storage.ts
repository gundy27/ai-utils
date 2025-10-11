/**
 * Storage utilities for widget state persistence
 */

const STORAGE_KEY = "portfolio_chatbot_session";

export interface StoredSession {
  sessionId: string;
  lastActivity: number;
  messageCount: number;
}

export function getStoredSession(): StoredSession | null {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) return null;

    const session: StoredSession = JSON.parse(data);

    // Expire session after 24 hours of inactivity
    const now = Date.now();
    const maxAge = 24 * 60 * 60 * 1000; // 24 hours

    if (now - session.lastActivity > maxAge) {
      clearStoredSession();
      return null;
    }

    return session;
  } catch (error) {
    console.error("Failed to get stored session:", error);
    return null;
  }
}

export function saveStoredSession(session: StoredSession): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch (error) {
    console.error("Failed to save session:", error);
  }
}

export function updateSessionActivity(sessionId: string): void {
  const session = getStoredSession();
  if (session && session.sessionId === sessionId) {
    session.lastActivity = Date.now();
    session.messageCount += 1;
    saveStoredSession(session);
  } else {
    saveStoredSession({
      sessionId,
      lastActivity: Date.now(),
      messageCount: 1,
    });
  }
}

export function clearStoredSession(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error("Failed to clear session:", error);
  }
}
