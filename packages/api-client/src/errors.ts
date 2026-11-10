export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
    message = `Spottr API request failed (${status}): ${detail}`,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
