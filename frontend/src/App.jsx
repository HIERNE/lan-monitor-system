import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import { Icon } from './components/Icons';
import Dashboard from './pages/Dashboard';
import Client, { ClientAgentView } from './pages/Client';
import ClientDetail from './pages/ClientDetail';
import CommandHistory from './pages/CommandHistory';

function AppShell() {
  const {
    activePage,
    darkMode,
    mobileNavOpen,
    setMobileNavOpen,
    screenModalClient,
    setScreenModalClient,
    notice,
  } = useApp();

  if (activePage === 'clientAgent') {
    return (
      <>
        <ClientAgentView />
        {notice && (
          <div className="toast">
            <span>
              <Icon name="check" size={14} />
            </span>
            {notice}
          </div>
        )}
      </>
    );
  }

  return (
    <div className={`admin-shell ${darkMode ? 'dark' : ''}`}>
      <Sidebar />

      <main className="admin-main">
        <Header />
        {activePage === 'dashboard' && <Dashboard />}
        {activePage === 'clients' && <Client />}
        {activePage === 'clientDetail' && <ClientDetail />}
        {activePage === 'history' && <CommandHistory />}
      </main>

      {mobileNavOpen && (
        <button
          className="mobile-nav-backdrop"
          aria-label="Đóng menu"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      {screenModalClient && (
        <div className="modal-backdrop" onMouseDown={() => setScreenModalClient(null)}>
          <div className="screen-modal" onMouseDown={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <span className="live-tag">
                  <i></i> DEMO SCREEN
                </span>
                <h2>
                  {screenModalClient.hostname} ({screenModalClient.ip_address})
                </h2>
              </div>
              <button className="icon-button" onClick={() => setScreenModalClient(null)} aria-label="Đóng">
                <Icon name="x" />
              </button>
            </div>
            <div className="remote-screen">
              <div className="screen-top">
                <span></span>
                <span></span>
                <span></span>
                <small>{screenModalClient.hostname} — SCREEN command preview</small>
              </div>
              <div className="screen-content">
                <div className="screen-wallpaper">
                  <Icon name="monitor" size={44} />
                  <strong>Giám sát màn hình (Chế độ Demo)</strong>
                  <small>Agent phản hồi MOD-1.6.6 · Sẽ hiển thị khung hình thật khi bật luồng ảnh</small>
                </div>
                <div className="screen-taskbar">
                  <span>▦</span>
                  <span className="fake-search">{screenModalClient.os_name}</span>
                  <span>{new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
              </div>
            </div>
            <div className="modal-foot">
              <span>
                <Icon name="activity" size={14} /> CPU {screenModalClient.cpu_usage}%
              </span>
              <span>RAM {screenModalClient.ram_usage}%</span>
              <span className="mono">{screenModalClient.client_id}</span>
              <button className="stop-button" onClick={() => setScreenModalClient(null)}>
                Đóng cửa sổ
              </button>
            </div>
          </div>
        </div>
      )}

      {notice && (
        <div className="toast">
          <span>
            <Icon name="check" size={14} />
          </span>
          {notice}
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppShell />
    </AppProvider>
  );
}
