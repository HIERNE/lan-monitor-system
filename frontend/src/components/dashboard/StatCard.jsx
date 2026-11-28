import React from 'react';
import { Icon } from '../Icons';

export default function StatCard({ icon, color = 'blue', label, value, subtext }) {
  return (
    <article className="stat-card">
      <div className={`stat-icon ${color}`}>
        <Icon name={icon} />
      </div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        {subtext && <small>{subtext}</small>}
      </div>
    </article>
  );
}
