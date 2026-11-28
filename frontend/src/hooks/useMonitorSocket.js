import { useEffect, useRef, useState } from 'react';
import { WS_URL } from '../services/api';

/**
 * hooks/useMonitorSocket.js - Kết nối WebSocket thời gian thực với FastAPI (TV4).
 * Hỗ trợ các event từ Server Core: monitor, heartbeat, command_result,
 * client_connected, client_disconnected, client_timeout.
 * Tự fallback sang chu kỳ mô phỏng 5s khi backend WebSocket chưa bật.
 */
export function useMonitorSocket({ onEvent, onMockTick, intervalMs = 5000 } = {}) {
  const [connectionMode, setConnectionMode] = useState('mock');
  const [lastSyncAt, setLastSyncAt] = useState(() => new Date().toISOString());

  const onEventRef = useRef(onEvent);
  const onMockTickRef = useRef(onMockTick);
  onEventRef.current = onEvent;
  onMockTickRef.current = onMockTick;

  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;
    let mockTimer = null;
    let disposed = false;
    let retryDelay = 3000;

    const startMockLoop = () => {
      if (mockTimer || disposed) return;
      mockTimer = window.setInterval(() => {
        if (disposed) return;
        const ts = new Date().toISOString();
        setLastSyncAt(ts);
        onMockTickRef.current?.(ts);
      }, intervalMs);
    };

    const stopMockLoop = () => {
      if (mockTimer) {
        window.clearInterval(mockTimer);
        mockTimer = null;
      }
    };

    const connect = () => {
      if (disposed) return;
      try {
        ws = new WebSocket(WS_URL);
      } catch {
        setConnectionMode('mock');
        startMockLoop();
        return;
      }

      ws.onopen = () => {
        if (disposed) return;
        retryDelay = 3000;
        stopMockLoop();
        setConnectionMode('live');
        setLastSyncAt(new Date().toISOString());
      };

      ws.onmessage = (evt) => {
        if (disposed) return;
        try {
          const parsed = JSON.parse(evt.data);
          setLastSyncAt(parsed.received_at || new Date().toISOString());
          onEventRef.current?.(parsed);
        } catch {
          // Bỏ qua payload lỗi định dạng, không làm sập UI
        }
      };

      ws.onerror = () => {
        ws?.close();
      };

      ws.onclose = () => {
        if (disposed) return;
        setConnectionMode('mock');
        startMockLoop();
        reconnectTimer = window.setTimeout(() => {
          retryDelay = Math.min(retryDelay * 1.5, 15000);
          connect();
        }, retryDelay);
      };
    };

    connect();

    return () => {
      disposed = true;
      stopMockLoop();
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;
        ws.close();
      }
    };
  }, [intervalMs]);

  return { connectionMode, lastSyncAt };
}
