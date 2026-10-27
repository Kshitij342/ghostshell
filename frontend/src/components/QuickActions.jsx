import React from 'react';
import { Terminal, ShieldAlert, Sparkles } from 'lucide-react';

export default function QuickActions({ activeMode, onSelectMode }) {
  const actions = [
    {
      id: 'command_oracle',
      title: 'Explain a Command',
      desc: 'Dissect flags, execution expectations, risks & safer alternatives.',
      icon: Terminal,
      className: 'command-oracle',
      placeholder: 'e.g. tar -czvf archive.tar.gz /var/log or find . -name "*.tmp" -delete',
    },
    {
      id: 'error_exorcist',
      title: 'Investigate an Error',
      desc: 'Paste a terminal error or stack trace for diagnosis and resolution.',
      icon: ShieldAlert,
      className: 'error-exorcist',
      placeholder: 'Paste your terminal error, exception stack trace, or failed exit code here...',
    },
    {
      id: 'safer_fix',
      title: 'Suggest a Safer Fix',
      desc: 'Propose safer, defensive alternatives and dry-run equivalents.',
      icon: Sparkles,
      className: 'safer-fix',
      placeholder: 'Describe the operation or command you want to make safer...',
    },
  ];

  return (
    <div className="quick-actions-bar" role="toolbar" aria-label="Quick Action Modes">
      {actions.map((act) => {
        const Icon = act.icon;
        const isActive = activeMode === act.id;

        return (
          <button
            key={act.id}
            type="button"
            className={`action-card ${act.className} ${isActive ? 'active' : ''}`}
            onClick={() => onSelectMode(isActive ? 'general' : act.id, act.placeholder)}
            aria-pressed={isActive}
          >
            <div className="action-icon">
              <Icon size={18} />
            </div>
            <div>
              <div className="action-title">{act.title}</div>
              <div className="action-desc">{act.desc}</div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
