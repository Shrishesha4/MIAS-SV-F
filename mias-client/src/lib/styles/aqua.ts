// MIAS Design System - Mac OS X Aqua Skeuomorphic Style Constants
// DO NOT MODIFY THESE VALUES

export const aquaStyles = {
  // Background Pattern
  appBackground: `
    background-image: repeating-linear-gradient(
      0deg,
      rgba(180, 190, 210, 0.2),
      rgba(180, 190, 210, 0.2) 1px,
      rgba(210, 220, 230, 0.4) 1px,
      rgba(210, 220, 230, 0.4) 2px
    );
    background-color: #e0e5eb;
    box-shadow: inset 0 0 100px rgba(180, 190, 210, 0.3);
  `,

  // Primary Blue Gradient
  primaryButton: `
    background: linear-gradient(to bottom, #4d90fe, #0066cc);
    border: 1px solid rgba(0,0,0,0.2);
    box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);
  `,

  // Secondary/Light Button
  secondaryButton: `
    background: linear-gradient(to bottom, #f0f4fa, #d5dde8);
    border: 1px solid rgba(0,0,0,0.2);
    box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);
  `,

  // Danger/Red Button
  dangerButton: `
    background: linear-gradient(to bottom, #ff5a5a, #cc0000);
    border: 1px solid rgba(0,0,0,0.2);
    box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);
  `,

  // NavBar Gradient
  navBar: `
    background-image: linear-gradient(to bottom, #d1dbed, #b8c6df);
    box-shadow: 0 1px 3px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.7);
    border-bottom: 1px solid rgba(0,0,0,0.2);
  `,

  // Card Style
  card: `
    background-color: white;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24),
                0 0 0 1px rgba(0,0,0,0.05), inset 0 -5px 10px rgba(0,0,0,0.05);
    border: 1px solid rgba(0,0,0,0.1);
  `,

  // Card Section Header
  cardHeader: `
    background-image: linear-gradient(to bottom, #f8f9fb, #d9e1ea);
    box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1);
    border-bottom: 1px solid rgba(0,0,0,0.1);
  `,

  // Input Field
  input: `
    border: 1px solid rgba(0,0,0,0.2);
    border-radius: 6px;
    background-color: rgba(255,255,255,0.8);
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
  `,

  // Status Colors
  successBadge: `
    background: linear-gradient(to bottom, #a7f3d0, #6ee7b7);
    border: 1px solid rgba(16,185,129,0.3);
  `,

  errorBadge: `
    background: linear-gradient(to bottom, #ff5a5a, #cc0000);
  `,

  creditBadge: `
    background: linear-gradient(to bottom, #4ade80, #22c55e);
  `,

  medicalAlert: `
    background-color: rgba(255,0,0,0.05);
    border: 1px solid rgba(220,50,50,0.2);
  `,

  // Report Status Badges
  normalBadge: `background: linear-gradient(to bottom, #34c759, #30b350);`,
  abnormalBadge: `background: linear-gradient(to bottom, #ff9500, #ff5e3a);`,
  criticalBadge: `background: linear-gradient(to bottom, #ff3b30, #d70015);`,
  pendingBadge: `background: linear-gradient(to bottom, #8e8e93, #636366);`,

  // Avatar
  avatar: `
    border: 2px solid rgba(255,255,255,0.9);
    box-shadow: 0 1px 3px rgba(0,0,0,0.2), 0 0 0 1px rgba(0,0,0,0.05);
    border-radius: 9999px;
  `,
} as const;
