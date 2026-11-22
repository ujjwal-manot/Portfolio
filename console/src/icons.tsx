// Minimal custom SVG icons drawn for the EdgeSense-130 console with no external or vendor assets.
export function TrackIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <rect x="1.5" y="1.5" width="9" height="9" stroke="currentColor" strokeWidth="1.2" />
      <line x1="1.5" y1="5" x2="10.5" y2="5" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

export function BlockIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <rect x="3" y="3" width="6" height="6" stroke="currentColor" strokeWidth="1.2" />
      <line x1="1" y1="6" x2="3" y2="6" stroke="currentColor" strokeWidth="1.2" />
      <line x1="9" y1="6" x2="11" y2="6" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

export function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M1 6C2.5 3.5 9.5 3.5 11 6C9.5 8.5 2.5 8.5 1 6Z" stroke="currentColor" strokeWidth="1.1" />
      {open ? (
        <circle cx="6" cy="6" r="1.5" fill="currentColor" />
      ) : (
        <line x1="2" y1="10" x2="10" y2="2" stroke="currentColor" strokeWidth="1.2" />
      )}
    </svg>
  );
}
