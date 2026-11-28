import React, { useMemo, useState } from 'react';
import { Icon } from '../components/Icons';
import { useApp } from '../context/AppContext';
import { formatClockTime } from '../services/api';

/**
 * pages/CommandHistory.jsx - Nhật ký toàn bộ lệnh (CommandModel):
 * command_id, client_id, command_type, parameter, status, result_message, exit_code.
 */
export default function CommandHistory() {
  const { commands, clients, openClientDetail, refreshAll } = useApp();
  const [statusFilter, setStatusFilter] = useState('all');
  const [query, setQuery] = useState('');

  const hostById = useMemo(() => {
    const map = {};
    for (const c of clients) map[c.client_id] = c.hostname;
    return map;
  }, [clients]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return commands.filter((cmd) => {
      if (statusFilter !== 'all' && String(cmd.status).toLowerCase() !== statusFilter) return false;
      if (!q) return true;
      const host = (hostById[cmd.client_id] || '').toLowerCase();
      return (
        (cmd.command_id || '').toLowerCase().includes(q) ||
        (cmd.command_type || '').toLowerCase().includes(q) ||
        (cmd.client_id || '').toLowerCase().includes(q) ||
        host.includes(q) ||
        (cmd.result_message || '').toLowerCase().includes(q)
      );
    });
  }, [commands, statusFilter, query, hostById]);

  const countBy = (st) => commands.filter((c) => String(c.status).toLowerCase() === st).length;

  return (
    <div className="dashboard-content page-content">
      <div className="page-intro">
        <div>
          <h2>Lịch sử lệnh điều khiển</h2>
          <p>Theo dõi vòng đời lệnh: pending → sent → SUCCESS | FAILED | timeout.</p>
        </div>
        <button className="secondary-button" onClick={() => refreshAll(false)}>
          <Icon name="refresh" size={15} /> Đồng bộ nhật ký
        </button>
      </div>

      <section className="panel device-table-panel">
        <div className="table-tools">
          <label className="search-box">
            <Icon name="search" size={16} />
            <input
              placeholder="Tìm command_id, loại lệnh, hostname hoặc kết quả..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>

          <div className="filter-group">
            <button
              className={`text-button ${statusFilter === 'all' ? 'active' : ''}`}
              onClick={() => setStatusFilter('all')}
            >
              Tất cả ({commands.length})
            </button>
            <button
              className={`text-button ${statusFilter === 'success' ? 'active' : ''}`}
              onClick={() => setStatusFilter('success')}
            >
              SUCCESS ({countBy('success')})
            </button>
            <button
              className={`text-button ${statusFilter === 'failed' ? 'active' : ''}`}
              onClick={() => setStatusFilter('failed')}
            >
              FAILED ({countBy('failed')})
            </button>
            <button
              className={`text-button ${statusFilter === 'timeout' ? 'active' : ''}`}
              onClick={() => setStatusFilter('timeout')}
            >
              Timeout ({countBy('timeout')})
            </button>
          </div>
        </div>

        <div className="device-table">
          <div className="table-row history-row table-head">
            <span>Command ID</span>
            <span>Thiết bị đích</span>
            <span>Loại lệnh / Parameter</span>
            <span>Trạng thái</span>
            <span>Kết quả (result_message)</span>
            <span>Hoàn tất</span>
          </div>

          {filtered.length === 0 ? (
            <div className="empty-state">Không có bản ghi lệnh phù hợp.</div>
          ) : (
            filtered.map((cmd) => (
              <div className="table-row history-row" key={cmd.command_id}>
                <span className="mono">{cmd.command_id}</span>

                <div>
                  <button
                    className="text-button"
                    style={{ padding: '4px 8px' }}
                    onClick={() => openClientDetail(cmd.client_id)}
                  >
                    {hostById[cmd.client_id] || cmd.client_id}
                  </button>
                </div>

                <div>
                  <strong style={{ display: 'block' }}>{cmd.command_type}</strong>
                  <small className="mono" style={{ fontSize: 10 }}>
                    {JSON.stringify(cmd.parameter || {})}
                  </small>
                </div>

                <div>
                  <span className={`status-pill ${String(cmd.status).toLowerCase()}`}>
                    <i></i>
                    {cmd.status}
                  </span>
                </div>

                <span style={{ color: '#64748b', fontSize: 11, wordBreak: 'break-word' }}>
                  {cmd.result_message || '—'}
                  {cmd.exit_code !== null && cmd.exit_code !== undefined ? ` (exit: ${cmd.exit_code})` : ''}
                </span>

                <span className="mono">{formatClockTime(cmd.finished_at || cmd.sent_at || cmd.created_at)}</span>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
