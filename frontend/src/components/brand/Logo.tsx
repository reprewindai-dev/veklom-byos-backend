import React from 'react';

export const Logo: React.FC<{ size?: number; onClick?: () => void; className?: string }> = ({
  size = 24,
  onClick,
  className = '',
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 100 100"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    onClick={onClick}
    className={`drop-shadow-[0_0_4px_rgba(255,184,0,0.4)] ${onClick ? 'cursor-pointer' : ''} ${className}`}
  >
    <path
      d="M15 15 L45 85 C48 91, 52 91, 55 85 L85 15"
      stroke="#ffb800"
      strokeWidth="12"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <circle cx="50" cy="48" r="8" fill="#ffffff" />
  </svg>
);
