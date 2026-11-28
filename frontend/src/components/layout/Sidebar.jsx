import React from 'react';
import { Brand, Icon } from '../Icons';
import { useApp } from '../../context/AppContext';
import { STATUS_ONLINE } from '../../services/api';

export default function Sidebar() {
  const { clients, commands, activePage, setActivePage, mobileNavOpen, setMobileNavOpen } = useApp();
  const onlineCount = clients.filter((c) => c.status === STATUS_ONLINE).length;

  const navigate = (page) => {
    setActivePage(page);
    setMobileNavOpen(false);
  };

  return (
    <aside className={`sidebar ${mobileNavOpen ? 'mobile-open' : ''}`}>
      <Brand />

      <nav className="nav-list" aria-label="Điều hướng chính">
        <button
          className={`nav-item ${activePage === 'dashboard' ? 'active' : ''}`}
          onClick={() => navigate('dashboard')}
        >
          <Icon name="grid" />
          <span>Tổng quan</span>
        </button>

        <button
          className={`nav-item ${activePage === 'clients' ? 'active' : ''}`}
          onClick={() => navigate('clients')}
        >
          <Icon name="desktop" />
          <span>Thiết bị LAN</span>
          <b>
            {onlineCount}/{clients.length}
          </b>
        </button>

        <button
          className={`nav-item ${activePage === 'clientDetail' ? 'active' : ''}`}
          onClick={() => navigate('clientDetail')}
        >
          <Icon name="cpu" />
          <span>Chi tiết máy trạm</span>
        </button>

        <button
          className={`nav-item ${activePage === 'history' ? 'active' : ''}`}
          onClick={() => navigate('history')}
        >
          <Icon name="terminal" />
          <span>Lịch sử lệnh</span>
          <b>{commands.length}</b>
        </button>
      </nav>

      <div className="sidebar-bottom">
        <button className="switch-view" onClick={() => navigate('clientAgent')}>
          <Icon name="server" />
          <span>
            <small>Xem giao diện máy trạm</small>Client Agent
          </span>
          <Icon name="chevron" size={16} />
        </button>

        <div className="admin-profile">
          <div className="avatar">QT</div>
          <span>
            <strong>Quản trị viên</strong>
            <small>LAN Monitor · TCP :9000</small>
          </span>
        </div>
      </div>
    </aside>
  );
}
