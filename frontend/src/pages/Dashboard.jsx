import React from 'react';
import { Icon } from '../components/Icons';
import StatCard from '../components/dashboard/StatCard';
import ResourceChart from '../components/dashboard/ResourceChart';
import ClientStatus from '../components/clients/ClientStatus';
import CommandForm from '../components/commands/CommandForm';
import { useApp } from '../context/AppContext';
import {
  STATUS_ONLINE,
  formatBytes,
  formatRelativeTime,
  formatUptime,
} from '../services/api';

function ResourceCard({ icon, label, value, detail, color }) {
  return (
    <div className="resource-card">
      <div className="resource-top">
        <span className={`resource-icon ${color}`}>
          <Icon name={icon} size={17} />
        </span>
        <b>{Number(value ?? 0).toFixed(1)}%</b>
      </div>
      <p>{label}</p>
      <div className="progress">
        <i className={color} style={{ width: `${Math.min(100, Math.max(0, Number(value ?? 0)))}%` }}></i>
      </div>
      <small>{detail}</small>
    </div>
  );
}

export default function Dashboard() {
  const {
    clients,
    metricsHistory,
    commands,
    selectedClient,
    setSelectedClientId,
    searchQuery,
    setSearchQuery,
    setActivePage,
    openClientDetail,
    refreshAll,
    executeCommand,
  } = useApp();

  const onlineClients = clients.filter((c) => c.status === STATUS_ONLINE);
  const offlineCount = clients.length - onlineClients.length;
  const onlinePct = clients.length ? Math.round((onlineClients.length / clients.length) * 100) : 0;
  const avgCpu = onlineClients.length
    ? (onlineClients.reduce((sum, c) => sum + Number(c.cpu_usage || 0), 0) / onlineClients.length).toFixed(1)
    : '0.0';

  const q = searchQuery.trim().toLowerCase();
  const filtered = clients.filter(
    (c) =>
      !q ||
      (c.hostname || '').toLowerCase().includes(q) ||
      (c.ip_address || '').includes(q) ||
      (c.client_id || '').toLowerCase().includes(q)
  );

  const current = selectedClient || clients[0];
  const currentSamples = current ? metricsHistory[current.client_id] || [] : [];

  return (
    <div className="dashboard-content page-content">
      <section className="stat-grid">
        <StatCard
          icon="desktop"
          color="blue"
          label="Tổng thiết bị"
          value={clients.length}
          subtext="Đăng ký trên TCP Server"
        />
        <StatCard
          icon="wifi"
          color="green"
          label="Đang trực tuyến"
          value={onlineClients.length}
          subtext={`${onlinePct}% tổng thiết bị`}
        />
        <StatCard
          icon="power"
          color="red"
          label="Ngoại tuyến"
          value={offlineCount}
          subtext="Quá hạn heartbeat (30s)"
        />
        <StatCard
          icon="activity"
          color="violet"
          label="CPU trung bình"
          value={`${avgCpu}%`}
          subtext={`${commands.length} lệnh đã ghi nhận`}
        />
      </section>

      <section className="workspace-grid">
        {/* Danh sách rút gọn thiết bị */}
        <div className="device-panel panel">
          <div className="panel-heading">
            <div>
              <h2>Thiết bị trong mạng</h2>
              <p>Cập nhật mỗi 5 giây</p>
            </div>
            <button className="text-button" onClick={() => refreshAll(false)}>
              <Icon name="refresh" size={14} /> Làm mới
            </button>
          </div>

          <label className="search-box">
            <Icon name="search" size={16} />
            <input
              placeholder="Tìm hostname, IP hoặc MAC..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </label>

          <div className="device-list">
            {filtered.map((client) => (
              <button
                key={client.client_id}
                className={`device-row ${current?.client_id === client.client_id ? 'selected' : ''}`}
                onClick={() => setSelectedClientId(client.client_id)}
              >
                <span className={`device-symbol ${client.status}`}>
                  <Icon name="desktop" size={18} />
                </span>
                <span className="device-name">
                  <strong>{client.hostname}</strong>
                  <small>{client.ip_address}</small>
                </span>
                <ClientStatus status={client.status} />
                <Icon name="chevron" size={15} />
              </button>
            ))}
          </div>

          <button className="all-devices" onClick={() => setActivePage('clients')}>
            Quản lý tất cả thiết bị <Icon name="chevron" size={14} />
          </button>
        </div>

        {/* Chi tiết nhanh + biểu đồ + lệnh */}
        {current && (
          <div className="details-column">
            <div className="detail-panel panel">
              <div className="machine-header">
                <div className="machine-title">
                  <span className={`device-symbol ${current.status} large`}>
                    <Icon name="desktop" />
                  </span>
                  <div>
                    <span className={`status-line ${current.status}`}>
                      <i></i>
                      {current.status === STATUS_ONLINE ? 'ĐANG TRỰC TUYẾN' : 'NGOẠI TUYẾN'}
                    </span>
                    <h2>{current.hostname}</h2>
                    <p>
                      {current.ip_address} · {current.network_name || 'LAN'} · {current.os_name}
                    </p>
                  </div>
                </div>

                <button className="text-button" onClick={() => openClientDetail(current.client_id)}>
                  Chi tiết đầy đủ <Icon name="chevron" size={14} />
                </button>
              </div>

              <div className="resource-title">
                <h3>Tài nguyên hệ thống</h3>
                <span>
                  <i></i> Last seen: {formatRelativeTime(current.last_seen)}
                </span>
              </div>

              <div className="resource-grid">
                <ResourceCard
                  icon="cpu"
                  label="CPU"
                  value={current.cpu_usage}
                  detail={
                    current.cpu_name
                      ? `${current.cpu_name} (${current.cpu_cores || '—'}C/${current.cpu_threads || '—'}T)`
                      : `${current.cpu_cores || '—'} lõi / ${current.cpu_threads || '—'} luồng`
                  }
                  color="blue"
                />
                <ResourceCard
                  icon="activity"
                  label="Bộ nhớ RAM"
                  value={current.ram_usage}
                  detail={`${formatBytes(current.ram_used)} / ${formatBytes(current.ram_total)}`}
                  color="violet"
                />
                <ResourceCard
                  icon="storage"
                  label="Ổ đĩa hệ thống"
                  value={current.disk_usage}
                  detail={`${formatBytes(current.disk_used)} / ${formatBytes(current.disk_total)}`}
                  color="cyan"
                />
              </div>

              <div className="info-grid">
                <div>
                  <span>HỆ ĐIỀU HÀNH</span>
                  <strong>{current.os_name}</strong>
                </div>
                <div>
                  <span>UPTIME</span>
                  <strong>{formatUptime(current.uptime_seconds)}</strong>
                </div>
                <div>
                  <span>CLIENT ID / MAC</span>
                  <strong className="mono">{current.mac_address || current.client_id}</strong>
                </div>
                <div>
                  <span>CARD MẠNG</span>
                  <strong>{current.network_name || '—'}</strong>
                </div>
              </div>
            </div>

            <ResourceChart samples={currentSamples} hostname={current.hostname} />
            <CommandForm client={current} onSendCommand={executeCommand} />
          </div>
        )}
      </section>
    </div>
  );
}
