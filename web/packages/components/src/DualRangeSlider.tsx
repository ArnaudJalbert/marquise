import './DualRangeSlider.css';

export interface DualRangeSliderProps {
  min: number;
  max: number;
  value: [number, number];
  onChange: (value: [number, number]) => void;
  formatLabel: (value: [number, number]) => string;
}

/**
 * Two overlapping native range inputs presented as a single dual-thumb
 * slider. Native browser drag, not a custom drag implementation — a
 * deliberate scope choice per the design spec. The currently-larger value's
 * input gets a higher z-index so both thumbs stay draggable past each other.
 */
export function DualRangeSlider({ min, max, value, onChange, formatLabel }: DualRangeSliderProps) {
  const [start, end] = value;
  const leftPct = ((start - min) / (max - min)) * 100;
  const rightPct = 100 - ((end - min) / (max - min)) * 100;

  function handleStartChange(next: number) {
    onChange([Math.min(next, end), end]);
  }

  function handleEndChange(next: number) {
    onChange([start, Math.max(next, start)]);
  }

  return (
    <div className="dual-range-slider">
      <div className="dual-range-slider__track-area">
        <div className="dual-range-slider__track" />
        <div className="dual-range-slider__fill" style={{ left: `${leftPct}%`, right: `${rightPct}%` }} />
        <input
          type="range"
          className="dual-range-slider__input"
          style={{ zIndex: start >= end ? 2 : 1 }}
          min={min}
          max={max}
          step={1}
          value={start}
          onChange={(e) => handleStartChange(Number(e.target.value))}
        />
        <input
          type="range"
          className="dual-range-slider__input"
          style={{ zIndex: end >= start ? 2 : 1 }}
          min={min}
          max={max}
          step={1}
          value={end}
          onChange={(e) => handleEndChange(Number(e.target.value))}
        />
      </div>
      <span className="dual-range-slider__label">{formatLabel(value)}</span>
    </div>
  );
}
