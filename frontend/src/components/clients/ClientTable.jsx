import React, { useMemo, useState } from 'react';
import { Icon } from '../Icons';
import ClientStatus from './ClientStatus';
import {
  COMMAND_TYPES,
  STATUS_OFFLINE,
  STATUS_ONLINE,
  formatRelativeTime,
  formatUptime,
} from '../../services/api';

/**
 * components/clients/ClientTable.jsx - Bảng danh sách máy trạm theo schema ClientModel + MetricsModel.
 */
export default function ClientTable({ clients, onSelectClient, onQuickPing }) {
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const onlineCount = clients.filter((c) => c.status === STATUS_ONLINE).length;
  const offlineCount = clients.length - onlineCount;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return clients.filter((c) => {
      if (statusFilter !== 'all' && c.status !== statusFilter) return false;
      if (!q) return true;
      return (
        (c.hostname || '').toLowerCase().includes(q) ||
        (c.client_id || '').toLowerCase().includes(q) ||
        (c.ip_address || '').toLowerCase().includes(q) ||
        (c.os_name || '').toLowerCase().includes(q)
      );
    });
  }, [clients, query, statusFilter]);

  return (
    <section className="panel device-table-panel">
      <div className="table-tools">
        <label className="search-box">
          <Icon name="search" size={16} />
          <input
            placeholder="Tìm hostname, IP, MAC hoặc hệ điều hành..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>

        <div className="filter-group">
          <button
            className={`text-button ${statusFilter === 'all' ? 'active' : ''}`}
            onClick={() => setStatusFilter('all')}
          >
            Tất cả ({clients.length})
          </button>
          <button
            className={`text-button ${statusFilter === STATUS_ONLINE ? 'active' : ''}`}
            onClick={() => setStatusFilter(STATUS_ONLINE)}
          >
            Online ({onlineCount})
          </button>
          <button
            className={`text-button ${statusFilter === STATUS_OFFLINE ? 'active' : ''}`}
            onClick={() => setStatusFilter(STATUS_OFFLINE)}
          >
            Offline ({offlineCount})
          </button>
        </div>
      </div>

      <div className="device-table">
        <div className="table-row table-head">
          <span>Thiết bị (hostname · client_id)</span>
          <span>IP / Mạng</span>
          <span>Tài nguyên</span>
          <span>Trạng thái</span>
          <span>Uptime / Last seen</span>
          <span>Thao tác</span>
        </div>

        {filtered.length === 0 ? (
          <div className="empty-state">Không tìm thấy thiết bị phù hợp.</div>
        ) : (
          filtered.map((client) => {
            const isOffline = client.status !== STATUS_ONLINE;
            return (
              <div className="table-row" key={client.client_id}>
                <div className="table-device">
                  <span className={`device-symbol ${client.status}`}>
                    <Icon name="desktop" size={18} />
                  </span>
                  <span>
                    <strong>{client.hostname}</strong>
                    <small className="mono">{client.client_id}</small>
                  </span>
                </div>

                <div>
                  <span className="mono" style={{ display: 'block' }}>{client.ip_address}</span>
                  <small style={{ color: '#8c96a8', fontSize: 10 }}>{client.network_name || client.os_name}</small>
                </div>

                <div className="usage-pair">
                  <span>
                    CPU <b>{client.cpu_usage}%</b>
                  </span>
                  <span>
                    RAM <b>{client.ram_usage}%</b>
                  </span>
                  <span>
                    Disk <b>{client.disk_usage}%</b>
                  </span>
                </div>

                <div>
                  <ClientStatus status={client.status} />
                </div>

                <div>
                  <div style={{ fontWeight: 600 }}>{formatUptime(client.uptime_seconds)}</div>
                  <small style={{ color: '#8c96a8', fontSize: 10 }}>{formatRelativeTime(client.last_seen)}</small>
                </div>

                <div className="row-actions">
                  <button className="manage-button" onClick={() => onSelectClient(client.client_id)}>
                    Chi tiết <Icon name="chevron" size={13} />
                  </button>
                  {onQuickPing && (
                    <button
                      className="text-button"
                      disabled={isOffline}
                      title="Gửi lệnh PING_TEST"
                      onClick={() =>
                        onQuickPing({
                          client_id: client.client_id,
                          command_type: COMMAND_TYPES.PING_TEST,
                          parameter: { echo: 'pong' },
                        })
                      }
                    >
                      Ping
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
