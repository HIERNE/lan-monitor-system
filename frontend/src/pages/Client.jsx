import React from 'react';
import { Brand, Icon } from '../components/Icons';
import ClientTable from '../components/clients/ClientTable';
import { useApp } from '../context/AppContext';
import {
  COMMAND_TYPES,
  STATUS_ONLINE,
  formatBytes,
  formatRelativeTime,
  formatUptime,
} from '../services/api';

/**
 * pages/Client.jsx - Trang quản lý danh sách thiết bị LAN (dùng ClientTable).
 * Đồng thời export ClientAgentView mô phỏng giao diện Agent máy trạm (tray_app / system_info).
 */
export default function Client() {
  const { clients, openClientDetail, executeCommand, refreshAll } = useApp();

  return (
    <div className="dashboard-content page-content">
      <div className="page-intro">
        <div>
          <h2>Danh sách thiết bị trong mạng LAN</h2>
          <p>Dữ liệu đồng bộ từ bảng clients & client_metrics qua TCP Server (cổng 9000).</p>
        </div>
        <button className="primary-button" onClick={() => refreshAll(false)}>
          <Icon name="refresh" size={15} /> Làm mới danh sách
        </button>
      </div>

      <ClientTable
        clients={clients}
        onSelectClient={openClientDetail}
        onQuickPing={executeCommand}
      />
    </div>
  );
}

export function ClientAgentView() {
  const { selectedClient, clients, setActivePage, toggleClientMockStatus, executeCommand } = useApp();
  const agent = selectedClient || clients[0];

  if (!agent) return null;
  const connected = agent.status === STATUS_ONLINE;

  const ringStyle = (pct, color) => ({
    color,
    background: `radial-gradient(closest-side, #fff 78%, transparent 80% 99%), conic-gradient(${color} ${Math.min(
      100,
      Math.max(0, Number(pct || 0))
    )}%, #e7edf5 0)`,
  });

  return (
    <div className="client-shell">
      <div className="client-glow one"></div>
      <div className="client-glow two"></div>

      <header className="client-header">
        <Brand />
        <button className="back-admin" onClick={() => setActivePage('dashboard')}>
          <Icon name="grid" size={16} /> Quay lại Admin Dashboard
        </button>
      </header>

      <main className="client-main">
        <section className="agent-card">
          <div className="agent-hero">
            <div className="agent-device">
              <span className={connected ? 'connected' : ''}>
                <Icon name="desktop" size={36} />
              </span>
              <i className={connected ? '' : 'off'}></i>
            </div>

            <div className={`connection-label ${connected ? '' : 'disconnected'}`}>
              <i></i>
              {connected ? 'Đang kết nối TCP Server' : 'Mất kết nối TCP Server'}
            </div>

            <h1>{agent.hostname}</h1>
            <p>
              {agent.ip_address} · {agent.network_name || 'LAN'} · {agent.os_name}
            </p>
          </div>

          <div className="privacy-note">
            <span>
              <Icon name="lock" size={17} />
            </span>
            <div>
              <strong>Chế độ Agent thu thập thông tin</strong>
              <p>Gửi gói tin monitor & heartbeat JSON UTF-8 định kỳ mỗi 5 giây tới cổng TCP Server.</p>
            </div>
          </div>

          <div className="agent-stats">
            <div>
              <span className="mini-ring" style={ringStyle(agent.cpu_usage, '#397ce4')}>
                {Math.round(agent.cpu_usage)}
                <small>%</small>
              </span>
              <p>CPU</p>
            </div>
            <div>
              <span className="mini-ring" style={ringStyle(agent.ram_usage, '#7559dd')}>
                {Math.round(agent.ram_usage)}
                <small>%</small>
              </span>
              <p>RAM</p>
            </div>
            <div>
              <span className="mini-ring" style={ringStyle(agent.disk_usage, '#1ba4bc')}>
                {Math.round(agent.disk_usage)}
                <small>%</small>
              </span>
              <p>Ổ đĩa</p>
            </div>
          </div>

          <div className="agent-info">
            <div>
              <span>
                <Icon name="server" size={16} /> Client ID (MAC)
              </span>
              <strong className="mono">{agent.client_id}</strong>
            </div>
            <div>
              <span>
                <Icon name="clock" size={16} /> Uptime
              </span>
              <strong>{formatUptime(agent.uptime_seconds)}</strong>
            </div>
            <div>
              <span>
                <Icon name="activity" size={16} /> Bộ nhớ RAM
              </span>
              <strong>
                {formatBytes(agent.ram_used)} / {formatBytes(agent.ram_total)}
              </strong>
            </div>
            <div>
              <span>
                <Icon name="refresh" size={16} /> Last seen
              </span>
              <strong>{formatRelativeTime(agent.last_seen)}</strong>
            </div>
          </div>

          <div className="agent-actions">
            <button onClick={() => toggleClientMockStatus(agent.client_id)}>
              <Icon name="power" size={15} /> {connected ? 'Giả lập mất kết nối' : 'Kết nối lại'}
            </button>
            <button
              disabled={!connected}
              onClick={() =>
                executeCommand({
                  client_id: agent.client_id,
                  command_type: COMMAND_TYPES.PING_TEST,
                  parameter: { echo: 'pong' },
                })
              }
            >
              <Icon name="wifi" size={15} /> Test PING_TEST
            </button>
          </div>

          <div className="agent-footer">
            <span>
              <i className={connected ? '' : 'off'}></i>
              {connected ? 'Heartbeat 5s bình thường' : 'Timeout sau 30s không phản hồi'}
            </span>
            <span className="mono">TCP :9000</span>
          </div>
        </section>

        <p className="client-caption">
          <Icon name="shield" size={14} /> LAN Monitoring System · Giao thức protocol/messages.md
        </p>
      </main>
    </div>
  );
}
