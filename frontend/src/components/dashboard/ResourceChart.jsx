import React from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatClockTime } from '../../services/api';

/**
 * components/dashboard/ResourceChart.jsx - Biểu đồ chuỗi thời gian cho
 * cpu_usage, ram_usage, disk_usage (MetricsModel) bằng Recharts.
 */
export default function ResourceChart({ samples = [], hostname = '' }) {
  const data = samples.map((item) => ({
    time: formatClockTime(item.collected_at),
    cpu_usage: Number(item.cpu_usage ?? 0),
    ram_usage: Number(item.ram_usage ?? 0),
    disk_usage: Number(item.disk_usage ?? 0),
  }));

  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h2>Biểu đồ tài nguyên theo thời gian {hostname ? `· ${hostname}` : ''}</h2>
          <p>Mẫu từ gói tin monitor (chu kỳ 5 giây · đơn vị %)</p>
        </div>
        <div className="chart-legend">
          <span>
            <i style={{ background: '#3a7de4' }}></i>CPU
          </span>
          <span>
            <i style={{ background: '#7959dd' }}></i>RAM
          </span>
          <span>
            <i style={{ background: '#20a7bb' }}></i>Ổ đĩa
          </span>
        </div>
      </div>

      <div className="chart-body">
        {data.length === 0 ? (
          <div className="empty-state">Chưa có mẫu dữ liệu metrics cho thiết bị này.</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 6, right: 12, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3a7de4" stopOpacity={0.28} />
                  <stop offset="95%" stopColor="#3a7de4" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="ramGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7959dd" stopOpacity={0.22} />
                  <stop offset="95%" stopColor="#7959dd" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e9f2" vertical={false} />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#8b95aa' }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#8b95aa' }} axisLine={false} tickLine={false} unit="%" />
              <Tooltip
                contentStyle={{
                  borderRadius: 10,
                  border: '1px solid #e2e8f0',
                  fontSize: 11,
                  boxShadow: '0 8px 24px rgba(15, 23, 42, 0.12)',
                }}
                formatter={(val, key) => {
                  const labels = { cpu_usage: 'CPU', ram_usage: 'RAM', disk_usage: 'Ổ đĩa' };
                  return [`${val}%`, labels[key] || key];
                }}
              />
              <Area type="monotone" dataKey="cpu_usage" stroke="#3a7de4" strokeWidth={2} fill="url(#cpuGrad)" isAnimationActive={false} />
              <Area type="monotone" dataKey="ram_usage" stroke="#7959dd" strokeWidth={2} fill="url(#ramGrad)" isAnimationActive={false} />
              <Area type="monotone" dataKey="disk_usage" stroke="#20a7bb" strokeWidth={1.6} fill="none" strokeDasharray="4 3" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
