import type { ErrorOr } from '../types/error-types.ts'

export function ok<T>(value: T): ErrorOr<T> {
  return { ok: true, value }
}

export function err<T>(errorMessage: string): ErrorOr<T> {
  return { ok: false, error: errorMessage }
}

export function unwrap<T>(result: ErrorOr<T>): T {
  if (!result.ok) throw new Error(result.error)
  return result.value
}

export function mapResult<T, U>(result: ErrorOr<T>, transform: (value: T) => U): ErrorOr<U> {
  if (!result.ok) return result
  return ok(transform(result.value))
}