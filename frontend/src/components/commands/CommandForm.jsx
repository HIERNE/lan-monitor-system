import React, { useState } from 'react';
import { Icon } from '../Icons';
import { COMMAND_META, COMMAND_TYPES, STATUS_ONLINE } from '../../services/api';

/**
 * components/commands/CommandForm.jsx - Gửi lệnh điều khiển theo protocol/messages.md.
 * Khóa payload: { client_id, command_type, parameter }.
 * Bản giữa kỳ (command_manager.py): allowlist mặc định chỉ cho phép PING_TEST.
 */
export default function CommandForm({ client, onSendCommand }) {
  const [echoText, setEchoText] = useState('pong');
  const [pendingConfirm, setPendingConfirm] = useState(null);
  const [sending, setSending] = useState(false);

  if (!client) return null;
  const isOffline = client.status !== STATUS_ONLINE;

  const dispatch = async (meta) => {
    if (isOffline || sending) return;
    if (meta.needsConfirm && pendingConfirm !== meta.type) {
      setPendingConfirm(meta.type);
      return;
    }

    setPendingConfirm(null);
    setSending(true);
    try {
      const parameter = meta.type === COMMAND_TYPES.PING_TEST ? { echo: echoText.trim() || 'pong' } : {};
      await onSendCommand({
        client_id: client.client_id,
        command_type: meta.type,
        parameter,
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h2>Điều khiển thiết bị · {client.hostname}</h2>
          <p>Gửi lệnh qua giao thức JSON TCP (`command_type` + `parameter`)</p>
        </div>
        <span className="secure">
          <Icon name="shield" size={14} /> Allowlist giữa kỳ: PING_TEST
        </span>
      </div>

      <div className="command-grid">
        {COMMAND_META.map((meta) => (
          <button
            key={meta.type}
            className={`command ${meta.tone}`}
            disabled={isOffline || sending}
            onClick={() => dispatch(meta)}
          >
            <span>
              <Icon name={meta.icon} />
            </span>
            <div>
              <strong>
                {meta.label}
                {meta.midtermAllowed && <em className="midterm-tag">Mở sẵn</em>}
              </strong>
              <small>{meta.desc}</small>
            </div>
            <Icon name="chevron" size={15} />
          </button>
        ))}
      </div>

      {pendingConfirm && (
        <div className="confirm-banner">
          <span>
            Xác nhận gửi lệnh <strong>{pendingConfirm}</strong> tới <strong>{client.hostname}</strong> ({client.client_id})?
          </span>
          <div className="confirm-actions">
            <button className="secondary-button" onClick={() => setPendingConfirm(null)}>
              Hủy
            </button>
            <button
              className="danger-button"
              onClick={() => dispatch(COMMAND_META.find((m) => m.type === pendingConfirm))}
            >
              Xác nhận gửi
            </button>
          </div>
        </div>
      )}

      <div className="command-custom-bar">
        <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>PING_TEST parameter.echo:</span>
        <input
          className="param-input"
          value={echoText}
          onChange={(e) => setEchoText(e.target.value)}
          placeholder='Chuỗi echo (mặc định "pong")'
          disabled={isOffline}
        />
        <button
          className="primary-button"
          disabled={isOffline || sending}
          onClick={() => dispatch(COMMAND_META[0])}
        >
          <Icon name="send" size={14} /> Gửi PING_TEST
        </button>
      </div>
    </div>
  );
}
