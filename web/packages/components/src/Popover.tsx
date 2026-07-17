import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import './Popover.css';

export interface PopoverProps {
  trigger: (open: boolean, toggle: () => void) => ReactNode;
  children: ReactNode;
  align?: 'start' | 'end';
}

/**
 * Lightweight popover primitive used by every filter dropdown (cinema,
 * language, genre, view switcher, date picker). Closes on outside click or
 * Escape. No focus-trapping/ARIA beyond the basics — flagged as a future
 * upgrade path (Radix/Floating UI) if accessibility requirements harden.
 */
export function Popover({ trigger, children, align = 'start' }: PopoverProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  return (
    <div className="popover-root" ref={rootRef}>
      {trigger(open, () => setOpen((o) => !o))}
      {open && <div className={`popover-panel popover-panel--${align}`}>{children}</div>}
    </div>
  );
}
