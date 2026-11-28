import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  COMMAND_TYPES,
  INITIAL_CLIENTS,
  INITIAL_COMMANDS,
  STATUS_OFFLINE,
  STATUS_ONLINE,
  buildInitialMetricsHistory,
  getClients,
  getCommands,
  normalizeClient,
  normalizeCommand,
  sendCommand,
} from '../services/api';
import { useMonitorSocket } from '../hooks/useMonitorSocket';

const AppContext = createContext(null);
const MAX_HISTORY_POINTS = 20;

export function AppProvider({ children }) {
  const [clients, setClients] = useState(INITIAL_CLIENTS);
  const [metricsHistory, setMetricsHistory] = useState(() => buildInitialMetricsHistory(INITIAL_CLIENTS));
  const [commands, setCommands] = useState(INITIAL_COMMANDS);
  const [selectedClientId, setSelectedClientId] = useState(INITIAL_CLIENTS[0].client_id);
  const [activePage, setActivePage] = useState('dashboard'); // dashboard | clients | clientDetail | history | clientAgent
  const [searchQuery, setSearchQuery] = useState('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [screenModalClient, setScreenModalClient] = useState(null);
  const [notice, setNotice] = useState('');

  const notify = useCallback((message) => {
    setNotice(message);
    window.setTimeout(() => {
      setNotice((prev) => (prev === message ? '' : prev));
    }, 3000);
  }, []);

  // Nạp dữ liệu ban đầu từ FastAPI nếu TV4 đã chạy server
  const refreshAll = useCallback(async (silent = false) => {
    const [clientsRes, commandsRes] = await Promise.all([getClients(), getCommands()]);
    if (clientsRes.live && clientsRes.data) {
      setClients(clientsRes.data);
      if (clientsRes.data.length > 0) {
        setSelectedClientId((cur) =>
          clientsRes.data.some((c) => c.client_id === cur) ? cur : clientsRes.data[0].client_id
        );
      }
    }
    if (commandsRes.live && commandsRes.data) {
      setCommands(commandsRes.data);
    }
    if (!silent) {
      notify(clientsRes.live ? 'Đã đồng bộ dữ liệu trực tiếp từ Server' : 'Đã làm mới dữ liệu giám sát (Mô phỏng)');
    }
  }, [notify]);

  useEffect(() => {
    refreshAll(true);
  }, [refreshAll]);

  // Xử lý sự kiện WebSocket theo đúng event schema của Server Core
  const handleSocketEvent = useCallback((event) => {
    const type = event?.type;
    const data = event?.data || event;
    if (!type || !data) return;

    const receivedAt = event.received_at || new Date().toISOString();

    if (type === 'monitor' && data.client_id) {
      const updated = normalizeClient({ ...data, status: STATUS_ONLINE, last_seen: receivedAt });
      setClients((prev) => {
        const exists = prev.some((c) => c.client_id === updated.client_id);
        return exists
          ? prev.map((c) => (c.client_id === updated.client_id ? { ...c, ...updated } : c))
          : [...prev, updated];
      });
      setMetricsHistory((prev) => {
        const list = prev[updated.client_id] || [];
        const sample = {
          client_id: updated.client_id,
          collected_at: data.collected_at || receivedAt,
          cpu_usage: updated.cpu_usage,
          ram_usage: updated.ram_usage,
          disk_usage: updated.disk_usage,
          ram_total: updated.ram_total,
          ram_used: updated.ram_used,
          ram_free: updated.ram_free,
          disk_total: updated.disk_total,
          disk_used: updated.disk_used,
          disk_free: updated.disk_free,
          uptime_seconds: updated.uptime_seconds,
        };
        return {
          ...prev,
          [updated.client_id]: [...list, sample].slice(-MAX_HISTORY_POINTS),
        };
      });
      return;
    }

    if (type === 'heartbeat' && data.client_id) {
      setClients((prev) =>
        prev.map((c) =>
          c.client_id === data.client_id ? { ...c, status: STATUS_ONLINE, last_seen: receivedAt } : c
        )
      );
      return;
    }

    if ((type === 'client_disconnected' || type === 'client_timeout') && data.client_id) {
      setClients((prev) =>
        prev.map((c) =>
          c.client_id === data.client_id ? { ...c, status: STATUS_OFFLINE, last_seen: data.last_seen || receivedAt } : c
        )
      );
      return;
    }

    if (type === 'command_result' && data.command_id) {
      setCommands((prev) => {
        const exists = prev.some((cmd) => cmd.command_id === data.command_id);
        if (!exists) return [normalizeCommand(data), ...prev];
        return prev.map((cmd) =>
          cmd.command_id === data.command_id
            ? {
                ...cmd,
                status: data.status || cmd.status,
                result_message: data.result_message ?? cmd.result_message,
                exit_code: data.exit_code ?? cmd.exit_code,
                finished_at: data.finished_at || receivedAt,
              }
            : cmd
        );
      });
    }
  }, []);

  // Nhịp mô phỏng mỗi 5s (khớp chu kỳ monitor mặc định) khi TV4 WebSocket chưa online
  const handleMockTick = useCallback((timestamp) => {
    setClients((prev) => {
      const nextClients = prev.map((c) => {
        if (c.status !== STATUS_ONLINE) return c;
        const deltaCpu = (Math.random() - 0.5) * 6;
        const deltaRam = (Math.random() - 0.5) * 2;
        const cpu_usage = Number(Math.max(2, Math.min(98, c.cpu_usage + deltaCpu)).toFixed(1));
        const ram_usage = Number(Math.max(10, Math.min(96, c.ram_usage + deltaRam)).toFixed(1));
        const ram_used = Math.round((c.ram_total * ram_usage) / 100);
        const ram_free = Math.max(0, c.ram_total - ram_used);
        return {
          ...c,
          cpu_usage,
          ram_usage,
          ram_used,
          ram_free,
          uptime_seconds: (c.uptime_seconds || 0) + 5,
          last_seen: timestamp,
          collected_at: timestamp,
        };
      });

      setMetricsHistory((hist) => {
        const updated = { ...hist };
        for (const c of nextClients) {
          if (c.status !== STATUS_ONLINE) continue;
          const prevList = updated[c.client_id] || [];
          updated[c.client_id] = [
            ...prevList,
            {
              client_id: c.client_id,
              collected_at: timestamp,
              cpu_usage: c.cpu_usage,
              ram_usage: c.ram_usage,
              disk_usage: c.disk_usage,
              ram_total: c.ram_total,
              ram_used: c.ram_used,
              ram_free: c.ram_free,
              disk_total: c.disk_total,
              disk_used: c.disk_used,
              disk_free: c.disk_free,
              uptime_seconds: c.uptime_seconds,
            },
          ].slice(-MAX_HISTORY_POINTS);
        }
        return updated;
      });

      return nextClients;
    });
  }, []);

  const { connectionMode, lastSyncAt } = useMonitorSocket({
    onEvent: handleSocketEvent,
    onMockTick: handleMockTick,
    intervalMs: 5000,
  });

  const selectedClient = useMemo(
    () => clients.find((c) => c.client_id === selectedClientId) || clients[0] || null,
    [clients, selectedClientId]
  );

  const openClientDetail = useCallback((clientId) => {
    setSelectedClientId(clientId);
    setActivePage('clientDetail');
    setMobileNavOpen(false);
  }, []);

  const executeCommand = useCallback(
    async ({ client_id, command_type, parameter = {} }) => {
      const target = clients.find((c) => c.client_id === client_id) || null;
      const { command } = await sendCommand({ client_id, command_type, parameter }, target);
      setCommands((prev) => [command, ...prev]);

      if (command_type === COMMAND_TYPES.SCREEN && target && target.status === STATUS_ONLINE) {
        setScreenModalClient(target);
      }

      const label = target?.hostname || client_id;
      notify(
        command.status === 'SUCCESS'
          ? `${command_type} → ${label}: ${command.result_message || 'SUCCESS'}`
          : `${command_type} → ${label}: ${command.status} (${command.result_message || ''})`
      );
      return command;
    },
    [clients, notify]
  );

  const toggleClientMockStatus = useCallback((clientId) => {
    setClients((prev) =>
      prev.map((c) =>
        c.client_id === clientId
          ? {
              ...c,
              status: c.status === STATUS_ONLINE ? STATUS_OFFLINE : STATUS_ONLINE,
              last_seen: new Date().toISOString(),
            }
          : c
      )
    );
  }, []);

  const value = {
    clients,
    metricsHistory,
    commands,
    selectedClientId,
    setSelectedClientId,
    selectedClient,
    activePage,
    setActivePage,
    searchQuery,
    setSearchQuery,
    mobileNavOpen,
    setMobileNavOpen,
    darkMode,
    toggleDarkMode: () => setDarkMode((d) => !d),
    screenModalClient,
    setScreenModalClient,
    notice,
    notify,
    connectionMode,
    lastSyncAt,
    refreshAll,
    openClientDetail,
    executeCommand,
    toggleClientMockStatus,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp phải được dùng bên trong AppProvider');
  return ctx;
}
