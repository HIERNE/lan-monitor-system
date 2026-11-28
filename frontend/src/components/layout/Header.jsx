import React from 'react';
import { Icon } from '../Icons';
import { useApp } from '../../context/AppContext';
import { formatRelativeTime } from '../../services/api';

const PAGE_TITLES = {
  dashboard: 'Trung tâm giám sát LAN',
  clients: 'Quản lý thiết bị',
  clientDetail: 'Chi tiết máy trạm',
  history: 'Lịch sử lệnh điều khiển',
};

export default function Header() {
  const { activePage, setMobileNavOpen, connectionMode, lastSyncAt, refreshAll, darkMode, toggleDarkMode } = useApp();

  return (
    <header className="topbar">
      <button className="mobile-menu" aria-label="Mở menu" onClick={() => setMobileNavOpen(true)}>
        <Icon name="menu" />
      </button>

      <div>
        <p className="eyebrow">HỆ THỐNG GIÁM SÁT MẠNG LAN</p>
        <h1>{PAGE_TITLES[activePage] || 'NetWatch'}</h1>
      </div>

      <div className="top-actions">
        <div
          className={`system-ok ${connectionMode}`}
          title={`Đồng bộ gần nhất: ${formatRelativeTime(lastSyncAt)}`}
        >
          <span></span>
          {connectionMode === 'live' ? 'WebSocket trực tiếp' : 'Mô phỏng (chờ API TV4)'}
        </div>

        <button className="icon-button" aria-label="Làm mới dữ liệu" title="Làm mới dữ liệu" onClick={() => refreshAll(false)}>
          <Icon name="refresh" size={17} />
        </button>

        <button
          className="icon-button"
          aria-label={darkMode ? 'Chế độ sáng' : 'Chế độ tối'}
          title={darkMode ? 'Chế độ sáng' : 'Chế độ tối'}
          onClick={toggleDarkMode}
        >
          <Icon name={darkMode ? 'sun' : 'moon'} size={17} />
        </button>
      </div>
    </header>
  );
}
