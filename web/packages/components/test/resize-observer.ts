/** ResizeObserver test double that emits one fixed rectangle on observation. */
export function fixedResizeObserver(width: number, height: number) {
  return class FixedResizeObserver implements ResizeObserver {
    constructor(private readonly callback: ResizeObserverCallback) {}

    observe(_target: Element): void {
      this.callback(
        [{ contentRect: { width, height } } as ResizeObserverEntry],
        this,
      );
    }

    unobserve(): void {}
    disconnect(): void {}
  };
}
