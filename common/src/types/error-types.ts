export type ErrorOr<T> = { ok: true; value: T } | { ok: false; error: string }
