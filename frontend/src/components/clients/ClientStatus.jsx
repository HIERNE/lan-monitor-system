import React from 'react';
import { STATUS_ONLINE } from '../../services/api';

export default function ClientStatus({ status }) {
  const isOnline = String(status || '').toLowerCase() === STATUS_ONLINE;
  return (
    <span className={`status-pill ${isOnline ? 'online' : 'offline'}`}>
      <i></i>
      {isOnline ? 'Online' : 'Offline'}
    </span>
  );
}
