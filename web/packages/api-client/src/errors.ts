export interface MarquiseApiErrorParams {
  status: number;
  detail: string;
  errorCode: string | null;
  requestId: string | null;
}

export class MarquiseApiError extends Error {
  readonly status: number;
  readonly errorCode: string | null;
  readonly requestId: string | null;
  readonly detail: string;

  constructor(params: MarquiseApiErrorParams) {
    super(`Marquise API error ${params.status}: ${params.detail}`);
    this.name = "MarquiseApiError";
    this.status = params.status;
    this.errorCode = params.errorCode;
    this.requestId = params.requestId;
    this.detail = params.detail;

    Object.setPrototypeOf(this, MarquiseApiError.prototype);
  }
}
