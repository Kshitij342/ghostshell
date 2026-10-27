import React from 'react';
import { ShieldCheck, Lock, HardDrive } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="app-footer">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
        <span className="footer-pill">
          <HardDrive size={12} color="#00ff9d" />
          <span>Local Open-Weight Inference (Ollama)</span>
        </span>
        <span className="footer-pill">
          <Lock size={12} color="#38bdf8" />
          <span>Zero Telemetry & Private</span>
        </span>
        <span className="footer-pill">
          <ShieldCheck size={12} color="#c084fc" />
          <span>Execution-Free Sandbox</span>
        </span>
      </div>

      <div style={{ color: 'var(--text-muted)' }}>
        GhostShell &bull; Hacktoberfest 2026: Ghost in the Machine
      </div>
    </footer>
  );
}
