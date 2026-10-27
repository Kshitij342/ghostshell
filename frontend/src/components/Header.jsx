import React from 'react';
import GhostAvatar from './GhostAvatar';
import { Terminal } from 'lucide-react';

export default function Header() {
  return (
    <header className="app-header">
      <div className="brand-wrapper">
        <GhostAvatar size={38} glowing={true} />
        <div>
          <h1 className="brand-title">
            <span className="brand-title-accent">Ghost</span>Shell
            <span style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem', border: '1px solid rgba(168, 85, 247, 0.4)', borderRadius: '4px', color: '#c084fc', marginLeft: '0.3rem', fontWeight: '500' }}>
              v0.1.0-alpha
            </span>
          </h1>
          <p className="brand-tagline">
            "Your terminal has a ghost. It knows your code."
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <div className="footer-pill" title="Hacktoberfest 2026 Week 4: Ghost in the Machine">
          <Terminal size={13} color="#00ff9d" />
          <span>Hacktoberfest 2026</span>
        </div>
      </div>
    </header>
  );
}
