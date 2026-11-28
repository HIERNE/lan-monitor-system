/**
 * services/api.js - Lớp gọi REST API sang FastAPI Backend (TV4) kèm mock fallback
 * theo đúng hợp đồng dữ liệu của backend/models/* và protocol/messages.md.
 */

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/monitor';

export const STATUS_ONLINE = 'online';
export const STATUS_OFFLINE = 'offline';

export const COMMAND_TYPES = {
  PING_TEST: 'PING_TEST',
  GET_CONFIG: 'GET_CONFIG',
  SCREEN: 'SCREEN',
  RESTART: 'RESTART',
  SHUTDOWN: 'SHUTDOWN',
};

// Theo backend/server/command_manager.py (ALLOWED_COMMAND_TYPES) bản giữa kỳ
export const MIDTERM_ALLOWED_COMMANDS = [COMMAND_TYPES.PING_TEST];

export const COMMAND_META = [
  {
    type: COMMAND_TYPES.PING_TEST,
    label: 'Ping Test',
    desc: 'Kiểm tra kết nối và độ trễ Agent',
    icon: 'wifi',
    tone: 'primary',
    midtermAllowed: true,
    needsConfirm: false,
  },
  {
    type: COMMAND_TYPES.GET_CONFIG,
    label: 'Lấy cấu hình',
    desc: 'Đọc thông số phần cứng & HĐH',
    icon: 'cpu',
    tone: 'neutral',
    midtermAllowed: false,
    needsConfirm: false,
  },
  {
    type: COMMAND_TYPES.SCREEN,
    label: 'Giám sát Screen',
    desc: 'Xem khung hình máy trạm (Demo)',
    icon: 'monitor',
    tone: 'violet',
    midtermAllowed: false,
    needsConfirm: false,
  },
  {
    type: COMMAND_TYPES.RESTART,
    label: 'Khởi động lại',
    desc: 'Restart thiết bị từ xa (Demo)',
    icon: 'restart',
    tone: 'amber',
    midtermAllowed: false,
    needsConfirm: true,
  },
  {
    type: COMMAND_TYPES.SHUTDOWN,
    label: 'Tắt máy',
    desc: 'Shutdown an toàn (Demo)',
    icon: 'power',
    tone: 'danger',
    midtermAllowed: false,
    needsConfirm: true,
  },
];

// ---------------------------------------------------------------------------
// Formatters cho đơn vị chuẩn của backend/models/metrics_model.py (byte, giây, ISO-8601)
// ---------------------------------------------------------------------------
export function formatBytes(bytes) {
  if (bytes === null || bytes === undefined || Number.isNaN(Number(bytes))) return '—';
  const num = Number(bytes);
  if (num === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const idx = Math.min(Math.floor(Math.log(num) / Math.log(1024)), units.length - 1);
  const val = num / Math.pow(1024, idx);
  return `${val >= 100 ? val.toFixed(0) : val.toFixed(1)} ${units[idx]}`;
}

export function formatUptime(uptimeSeconds) {
  if (!uptimeSeconds || uptimeSeconds <= 0) return '—';
  const total = Math.floor(uptimeSeconds);
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const mins = Math.floor((total % 3600) / 60);
  if (days > 0) return `${days} ngày ${String(hours).padStart(2, '0')} giờ`;
  if (hours > 0) return `${hours} giờ ${String(mins).padStart(2, '0')} phút`;
  return `${mins} phút`;
}

export function formatClockTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString('vi-VN', { hour12: false });
}

export function formatRelativeTime(iso) {
  if (!iso) return 'Chưa có';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const diffSec = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
  if (diffSec < 10) return 'Vừa xong';
  if (diffSec < 60) return `${diffSec} giây trước`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} phút trước`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr} giờ trước`;
  return `${Math.floor(diffHr / 24)} ngày trước`;
}

// ---------------------------------------------------------------------------
// Mock data theo đúng schema ClientModel + MetricsModel + CommandModel
// ---------------------------------------------------------------------------
const GB = 1024 ** 3;
const nowIso = (offsetSec = 0) => new Date(Date.now() + offsetSec * 1000).toISOString();

export const INITIAL_CLIENTS = [
  {
    client_id: '8C:16:45:A2:9F:01',
    hostname: 'PC-LAB-01',
    ip_address: '192.168.1.21',
    mac_address: '8C:16:45:A2:9F:01',
    network_name: 'Ethernet',
    os_name: 'Windows 11 Pro (10.0.22631)',
    cpu_name: 'Intel(R) Core(TM) i5-12400',
    cpu_cores: 6,
    cpu_threads: 12,
    ram_total: 16 * GB,
    ram_used: Math.round(9.9 * GB),
    ram_free: Math.round(6.1 * GB),
    ram_usage: 61.9,
    disk_total: 512 * GB,
    disk_used: Math.round(297 * GB),
    disk_free: Math.round(215 * GB),
    disk_usage: 58.0,
    cpu_usage: 34.2,
    boot_time: nowIso(-1065600),
    uptime_seconds: 1065600,
    status: STATUS_ONLINE,
    last_seen: nowIso(-2),
    collected_at: nowIso(-2),
  },
  {
    client_id: '8C:16:45:A2:9F:02',
    hostname: 'PC-LAB-02',
    ip_address: '192.168.1.22',
    mac_address: '8C:16:45:A2:9F:02',
    network_name: 'Ethernet',
    os_name: 'Windows 10 Pro (10.0.19045)',
    cpu_name: 'Intel(R) Core(TM) i5-11400',
    cpu_cores: 6,
    cpu_threads: 12,
    ram_total: 16 * GB,
    ram_used: Math.round(7.2 * GB),
    ram_free: Math.round(8.8 * GB),
    ram_usage: 45.0,
    disk_total: 512 * GB,
    disk_used: Math.round(215 * GB),
    disk_free: Math.round(297 * GB),
    disk_usage: 42.0,
    cpu_usage: 18.4,
    boot_time: nowIso(-406800),
    uptime_seconds: 406800,
    status: STATUS_ONLINE,
    last_seen: nowIso(-4),
    collected_at: nowIso(-4),
  },
  {
    client_id: '8C:16:45:A2:9F:03',
    hostname: 'LAPTOP-HR-01',
    ip_address: '192.168.1.35',
    mac_address: '8C:16:45:A2:9F:03',
    network_name: 'Wi-Fi',
    os_name: 'Windows 11 Pro (10.0.22631)',
    cpu_name: 'AMD Ryzen 7 5800H',
    cpu_cores: 8,
    cpu_threads: 16,
    ram_total: 16 * GB,
    ram_used: Math.round(13.0 * GB),
    ram_free: Math.round(3.0 * GB),
    ram_usage: 81.3,
    disk_total: 512 * GB,
    disk_used: Math.round(358 * GB),
    disk_free: Math.round(154 * GB),
    disk_usage: 69.9,
    cpu_usage: 71.8,
    boot_time: nowIso(-190800),
    uptime_seconds: 190800,
    status: STATUS_ONLINE,
    last_seen: nowIso(-1),
    collected_at: nowIso(-1),
  },
  {
    client_id: '8C:16:45:A2:9F:04',
    hostname: 'PC-KT-03',
    ip_address: '192.168.1.48',
    mac_address: '8C:16:45:A2:9F:04',
    network_name: 'Ethernet',
    os_name: 'Ubuntu 22.04 LTS',
    cpu_name: 'Intel(R) Core(TM) i7-10700',
    cpu_cores: 8,
    cpu_threads: 16,
    ram_total: 32 * GB,
    ram_used: Math.round(12.5 * GB),
    ram_free: Math.round(19.5 * GB),
    ram_usage: 39.1,
    disk_total: 1024 * GB,
    disk_used: Math.round(358 * GB),
    disk_free: Math.round(666 * GB),
    disk_usage: 35.0,
    cpu_usage: 12.6,
    boot_time: nowIso(-30360),
    uptime_seconds: 30360,
    status: STATUS_ONLINE,
    last_seen: nowIso(-5),
    collected_at: nowIso(-5),
  },
  {
    client_id: '8C:16:45:A2:9F:05',
    hostname: 'PC-KHO-01',
    ip_address: '192.168.1.60',
    mac_address: '8C:16:45:A2:9F:05',
    network_name: 'Ethernet',
    os_name: 'Windows 10 Pro (10.0.19045)',
    cpu_name: 'Intel(R) Core(TM) i3-10100',
    cpu_cores: 4,
    cpu_threads: 8,
    ram_total: 8 * GB,
    ram_used: 0,
    ram_free: 8 * GB,
    ram_usage: 0,
    disk_total: 256 * GB,
    disk_used: Math.round(110 * GB),
    disk_free: Math.round(146 * GB),
    disk_usage: 43.0,
    cpu_usage: 0,
    boot_time: null,
    uptime_seconds: 0,
    status: STATUS_OFFLINE,
    last_seen: nowIso(-10800),
    collected_at: nowIso(-10800),
  },
];

export function buildInitialMetricsHistory(clients = INITIAL_CLIENTS) {
  const history = {};
  for (const c of clients) {
    const samples = [];
    for (let i = 9; i >= 0; i--) {
      const jitterCpu = c.status === STATUS_ONLINE ? (Math.sin(i * 1.1) * 5 + (i % 3) - 1) : 0;
      const jitterRam = c.status === STATUS_ONLINE ? (Math.cos(i * 0.8) * 2.5) : 0;
      samples.push({
        client_id: c.client_id,
        collected_at: nowIso(-i * 5),
        cpu_usage: Number(Math.max(0, Math.min(100, (c.cpu_usage || 0) + jitterCpu)).toFixed(1)),
        ram_usage: Number(Math.max(0, Math.min(100, (c.ram_usage || 0) + jitterRam)).toFixed(1)),
        disk_usage: Number((c.disk_usage || 0).toFixed(1)),
        ram_total: c.ram_total,
        ram_used: c.ram_used,
        ram_free: c.ram_free,
        disk_total: c.disk_total,
        disk_used: c.disk_used,
        disk_free: c.disk_free,
        uptime_seconds: Math.max(0, (c.uptime_seconds || 0) - i * 5),
      });
    }
    history[c.client_id] = samples;
  }
  return history;
}

export const INITIAL_COMMANDS = [
  {
    command_id: 'cmd-20261128-001',
    client_id: '8C:16:45:A2:9F:01',
    command_type: COMMAND_TYPES.PING_TEST,
    parameter: { echo: 'pong' },
    status: 'SUCCESS',
    result_message: 'pong',
    exit_code: 0,
    created_at: nowIso(-120),
    sent_at: nowIso(-120),
    finished_at: nowIso(-119),
  },
  {
    command_id: 'cmd-20261128-002',
    client_id: '8C:16:45:A2:9F:02',
    command_type: COMMAND_TYPES.GET_CONFIG,
    parameter: {},
    status: 'SUCCESS',
    result_message: '{"hostname":"PC-LAB-02","os_name":"Windows 10 Pro (10.0.19045)","cpu_cores":6}',
    exit_code: 0,
    created_at: nowIso(-960),
    sent_at: nowIso(-960),
    finished_at: nowIso(-959),
  },
  {
    command_id: 'cmd-20261128-003',
    client_id: '8C:16:45:A2:9F:03',
    command_type: COMMAND_TYPES.SCREEN,
    parameter: {},
    status: 'SUCCESS',
    result_message: 'Mô phỏng: Chụp ảnh màn hình đã được xử lý (Demo mode)',
    exit_code: 0,
    created_at: nowIso(-2100),
    sent_at: nowIso(-2100),
    finished_at: nowIso(-2098),
  },
  {
    command_id: 'cmd-20261128-004',
    client_id: '8C:16:45:A2:9F:05',
    command_type: COMMAND_TYPES.PING_TEST,
    parameter: {},
    status: 'FAILED',
    result_message: 'client offline hoặc chưa kết nối',
    exit_code: 1,
    created_at: nowIso(-3600),
    sent_at: nowIso(-3600),
    finished_at: nowIso(-3595),
  },
];

// Chuẩn hóa bản ghi client/command phòng trường hợp TV4 trả status viết hoa ("Online") hoặc params thay vì parameter
export function normalizeClient(raw) {
  const statusRaw = String(raw.status || STATUS_OFFLINE).toLowerCase();
  return {
    ...raw,
    status: statusRaw === 'online' ? STATUS_ONLINE : STATUS_OFFLINE,
    cpu_usage: Number(raw.cpu_usage ?? 0),
    ram_usage: Number(raw.ram_usage ?? 0),
    disk_usage: Number(raw.disk_usage ?? 0),
    ram_total: Number(raw.ram_total ?? 0),
    ram_used: Number(raw.ram_used ?? 0),
    ram_free: Number(raw.ram_free ?? 0),
    disk_total: Number(raw.disk_total ?? 0),
    disk_used: Number(raw.disk_used ?? 0),
    disk_free: Number(raw.disk_free ?? 0),
    uptime_seconds: Number(raw.uptime_seconds ?? 0),
  };
}

export function normalizeCommand(raw) {
  return {
    command_id: raw.command_id || `cmd-${Date.now()}`,
    client_id: raw.client_id || '',
    command_type: raw.command_type || COMMAND_TYPES.PING_TEST,
    parameter: raw.parameter ?? raw.params ?? {},
    status: raw.status || 'pending',
    result_message: raw.result_message ?? raw.detail ?? '',
    exit_code: raw.exit_code ?? null,
    created_at: raw.created_at || nowIso(),
    sent_at: raw.sent_at || null,
    finished_at: raw.finished_at || null,
  };
}

async function fetchJson(path, options = {}, timeoutMs = 1800) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    window.clearTimeout(timer);
  }
}

export async function getClients() {
  try {
    const data = await fetchJson('/api/clients');
    const list = Array.isArray(data) ? data : data.clients || data.items || [];
    return { live: true, data: list.map(normalizeClient) };
  } catch {
    return { live: false, data: null };
  }
}

export async function getClientMetrics(clientId, limit = 20) {
  try {
    const data = await fetchJson(`/api/clients/${encodeURIComponent(clientId)}/metrics?limit=${limit}`);
    const list = Array.isArray(data) ? data : data.metrics || data.items || [];
    return { live: true, data: list };
  } catch {
    return { live: false, data: null };
  }
}

export async function getCommands(clientId = null) {
  try {
    const query = clientId ? `?client_id=${encodeURIComponent(clientId)}` : '';
    const data = await fetchJson(`/api/commands${query}`);
    const list = Array.isArray(data) ? data : data.commands || data.items || [];
    return { live: true, data: list.map(normalizeCommand) };
  } catch {
    return { live: false, data: null };
  }
}

/**
 * Gửi lệnh theo đúng hợp đồng: { client_id, command_type, parameter }
 * Nếu FastAPI chưa chạy, mô phỏng phản hồi y hệt backend/agent/command_handler.py.
 */
export async function sendCommand({ client_id, command_type, parameter = {} }, clientSnapshot = null) {
  const payload = { client_id, command_type, parameter };
  try {
    const res = await fetchJson('/api/commands', {
      method: 'POST',
      body: JSON.stringify(payload),
    }, 2500);
    return { live: true, command: normalizeCommand(res) };
  } catch {
    const createdAt = nowIso();
    const commandId = `cmd-${Date.now().toString(36)}`;
    const isOffline = clientSnapshot && clientSnapshot.status !== STATUS_ONLINE;

    if (isOffline) {
      return {
        live: false,
        command: {
          command_id: commandId,
          client_id,
          command_type,
          parameter,
          status: 'FAILED',
          result_message: 'client offline hoặc chưa kết nối',
          exit_code: 1,
          created_at: createdAt,
          sent_at: createdAt,
          finished_at: nowIso(0.2),
        },
      };
    }

    let resultMessage = 'pong';
    if (command_type === COMMAND_TYPES.PING_TEST) {
      resultMessage = String(parameter?.echo || 'pong');
    } else if (command_type === COMMAND_TYPES.GET_CONFIG) {
      resultMessage = JSON.stringify({
        hostname: clientSnapshot?.hostname || client_id,
        ip_address: clientSnapshot?.ip_address || '',
        mac_address: clientSnapshot?.mac_address || client_id,
        os_name: clientSnapshot?.os_name || '',
        cpu_name: clientSnapshot?.cpu_name || '',
        cpu_cores: clientSnapshot?.cpu_cores ?? null,
        ram_total: clientSnapshot?.ram_total ?? 0,
        disk_total: clientSnapshot?.disk_total ?? 0,
      });
    } else if (command_type === COMMAND_TYPES.SCREEN) {
      resultMessage = 'Mô phỏng: Chụp ảnh màn hình đã được xử lý (Demo mode)';
    } else if (command_type === COMMAND_TYPES.RESTART) {
      resultMessage = 'Mô phỏng: Lệnh khởi động lại đã được tiếp nhận an toàn (Demo mode)';
    } else if (command_type === COMMAND_TYPES.SHUTDOWN) {
      resultMessage = 'Mô phỏng: Lệnh tắt máy đã được tiếp nhận an toàn (Demo mode)';
    }

    return {
      live: false,
      command: {
        command_id: commandId,
        client_id,
        command_type,
        parameter,
        status: 'SUCCESS',
        result_message: resultMessage,
        exit_code: 0,
        created_at: createdAt,
        sent_at: createdAt,
        finished_at: nowIso(0.25),
      },
    };
  }
}
