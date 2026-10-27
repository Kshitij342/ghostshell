import React from 'react';

export default function GhostAvatar({ size = 28, glowing = true, className = '' }) {
  return (
    <div
      className={`ghost-avatar-wrapper ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        filter: glowing ? 'drop-shadow(0 0 6px rgba(0, 255, 157, 0.45))' : 'none',
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Ghost Body */}
        <path
          d="M12 2C7.58172 2 4 5.58172 4 10V19.5C4 20.3284 4.67157 21 5.5 21C6.01258 21 6.48831 20.7381 6.76458 20.3064L8 18.3757L9.23542 20.3064C9.51169 20.7381 9.98742 21 10.5 21C11.0126 21 11.4883 20.7381 11.7646 20.3064L12 19.9384L12.2354 20.3064C12.5117 20.7381 12.9874 21 13.5 21C14.0126 21 14.4883 20.7381 14.7646 20.3064L16 18.3757L17.2354 20.3064C17.5117 20.7381 17.9874 21 18.5 21C19.3284 21 20 20.3284 20 19.5V10C20 5.58172 16.4183 2 12 2Z"
          fill="#131d24"
          stroke="#00ff9d"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        {/* Spectral Eyes */}
        <circle cx="9" cy="10" r="1.5" fill="#00ff9d" />
        <circle cx="15" cy="10" r="1.5" fill="#00ff9d" />
        {/* Subtle Cyber Smile */}
        <path
          d="M10 14C11 15 13 15 14 14"
          stroke="#38bdf8"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}
