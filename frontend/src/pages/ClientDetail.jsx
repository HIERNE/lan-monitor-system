import React from 'react';
import { Icon } from '../components/Icons';
import ClientStatus from '../components/clients/ClientStatus';
import ResourceChart from '../components/dashboard/ResourceChart';
import CommandForm from '../components/commands/CommandForm';
import { useApp } from '../context/AppContext';
import {
  STATUS_ONLINE,
  formatBytes,
  formatClockTime,
  formatRelativeTime,
  formatUptime,
} from '../services/api';

/**
 * pages/ClientDetail.jsx - Trang chi tiết toàn bộ thông số 1 máy trạm:
 * cấu hình phần cứng (ClientModel), biểu đồ tài nguyên (MetricsModel),
 * gửi lệnh (CommandForm) và lịch sử lệnh riêng của máy đó.
 */
export default function ClientDetail() {
  const {
    clients,
    selectedClient,
    setSelectedClientId,
    metricsHistory,
    commands,
    setActivePage,
    executeCommand,
  } = useApp();

  const client = selectedClient || clients[0];
  if (!client) {
    return (
      <div className="dashboard-content">
        <div className="panel empty-state">Chưa có thiết bị nào được chọn.</div>
      </div>
    );
  }

  const samples = metricsHistory[client.client_id] || [];
  const clientCommands = commands.filter((cmd) => cmd.client_id === client.client_id).slice(0, 8);

  return (
    <div className="dashboard-content page-content">
      <div className="page-intro">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="secondary-button" onClick={() => setActivePage('clients')}>
            <Icon name="arrowLeft" size={15} /> Danh sách
          </button>
          <div>
            <h2>{client.hostname}</h2>
            <p>
              {client.client_id} · {client.ip_address} · {client.os_name}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ClientStatus status={client.status} />
          <select
            className="param-input"
            style={{ minWidth: 190, flex: 'none' }}
            value={client.client_id}
            onChange={(e) => setSelectedClientId(e.target.value)}
            aria-label="Chọn thiết bị"
          >
            {clients.map((c) => (
              <option key={c.client_id} value={c.client_id}>
                {c.hostname} ({c.status === STATUS_ONLINE ? 'Online' : 'Offline'})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="details-column">
        {/* Thông số phần cứng & hệ thống đầy đủ theo ClientModel + MetricsModel */}
        <section className="detail-panel panel">
          <div className="resource-title">
            <h3>Thông số tài nguyên trực tiếp</h3>
            <span>
              <i></i> Thu thập: {formatRelativeTime(client.collected_at || client.last_seen)}
            </span>
          </div>

          <div className="resource-grid">
            <div className="resource-card">
              <div className="resource-top">
                <span className="resource-icon blue">
                  <Icon name="cpu" size={17} />
                </span>
                <b>{Number(client.cpu_usage || 0).toFixed(1)}%</b>
              </div>
              <p>CPU</p>
              <div className="progress">
                <i className="blue" style={{ width: `${client.cpu_usage || 0}%` }}></i>
              </div>
              <small>{client.cpu_name || 'Chưa xác định'}</small>
            </div>

            <div className="resource-card">
              <div className="resource-top">
                <span className="resource-icon violet">
                  <Icon name="activity" size={17} />
                </span>
                <b>{Number(client.ram_usage || 0).toFixed(1)}%</b>
              </div>
              <p>RAM (Free: {formatBytes(client.ram_free)})</p>
              <div className="progress">
                <i className="violet" style={{ width: `${client.ram_usage || 0}%` }}></i>
              </div>
              <small>
                {formatBytes(client.ram_used)} / {formatBytes(client.ram_total)}
              </small>
            </div>

            <div className="resource-card">
              <div className="resource-top">
                <span className="resource-icon cyan">
                  <Icon name="storage" size={17} />
                </span>
                <b>{Number(client.disk_usage || 0).toFixed(1)}%</b>
              </div>
              <p>Ổ đĩa (Free: {formatBytes(client.disk_free)})</p>
              <div className="progress">
                <i className="cyan" style={{ width: `${client.disk_usage || 0}%` }}></i>
              </div>
              <small>
                {formatBytes(client.disk_used)} / {formatBytes(client.disk_total)}
              </small>
            </div>
          </div>

          <div className="info-grid">
            <div>
              <span>CLIENT ID</span>
              <strong className="mono">{client.client_id}</strong>
            </div>
            <div>
              <span>ĐỊA CHỈ IP / MAC</span>
              <strong className="mono">
                {client.ip_address} · {client.mac_address}
              </strong>
            </div>
            <div>
              <span>CPU CORES / THREADS</span>
              <strong>
                {client.cpu_cores ?? '—'} lõi / {client.cpu_threads ?? '—'} luồng
              </strong>
            </div>
            <div>
              <span>CARD MẠNG</span>
              <strong>{client.network_name || '—'}</strong>
            </div>
            <div>
              <span>HỆ ĐIỀU HÀNH</span>
              <strong>{client.os_name}</strong>
            </div>
            <div>
              <span>THỜI GIAN HOẠT ĐỘNG</span>
              <strong>{formatUptime(client.uptime_seconds)}</strong>
            </div>
            <div>
              <span>THỜI ĐIỂM KHỞI ĐỘNG</span>
              <strong className="mono">
                {client.boot_time ? new Date(client.boot_time).toLocaleString('vi-VN') : '—'}
              </strong>
            </div>
            <div>
              <span>LAST SEEN (UTC→LOCAL)</span>
              <strong className="mono">
                {client.last_seen ? new Date(client.last_seen).toLocaleString('vi-VN') : '—'}
              </strong>
            </div>
          </div>
        </section>

        <ResourceChart samples={samples} hostname={client.hostname} />
        <CommandForm client={client} onSendCommand={executeCommand} />

        {/* Lịch sử lệnh gần nhất của riêng client này */}
        <section className="panel device-table-panel">
          <div className="panel-heading">
            <div>
              <h2>Lệnh gần đây trên {client.hostname}</h2>
              <p>Kết quả từ bản ghi command_result</p>
            </div>
            <button className="text-button" onClick={() => setActivePage('history')}>
              Xem toàn bộ lịch sử <Icon name="chevron" size={14} />
            </button>
          </div>

          <div className="device-table">
            <div className="table-row history-row table-head">
              <span>Command ID</span>
              <span>Loại lệnh</span>
              <span>Parameter</span>
              <span>Trạng thái</span>
              <span>Kết quả (result_message)</span>
              <span>Thời điểm</span>
            </div>
            {clientCommands.length === 0 ? (
              <div className="empty-state">Chưa có lệnh nào gửi tới thiết bị này.</div>
            ) : (
              clientCommands.map((cmd) => (
                <div className="table-row history-row" key={cmd.command_id}>
                  <span className="mono">{cmd.command_id}</span>
                  <strong>{cmd.command_type}</strong>
                  <span className="mono">{JSON.stringify(cmd.parameter || {})}</span>
                  <div>
                    <span className={`status-pill ${String(cmd.status).toLowerCase()}`}>
                      <i></i>
                      {cmd.status}
                    </span>
                  </div>
                  <span style={{ fontSize: 11, color: '#64748b' }}>
                    {cmd.result_message || '—'}
                    {cmd.exit_code !== null && cmd.exit_code !== undefined ? ` (code: ${cmd.exit_code})` : ''}
                  </span>
                  <span className="mono">{formatClockTime(cmd.finished_at || cmd.sent_at || cmd.created_at)}</span>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
