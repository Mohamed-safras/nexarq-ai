import type { ReviewRun } from '@nexarq/common/interfaces'

type StateListener = (run: ReviewRun | null) => void

class ReviewState {
  private currentRun: ReviewRun | null = null
  private readonly listeners: Set<StateListener> = new Set()

  get(): ReviewRun | null {
    return this.currentRun
  }

  set(run: ReviewRun | null): void {
    this.currentRun = run
    for (const listener of this.listeners) {
      listener(run)
    }
  }

  subscribe(listener: StateListener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }
}

export const reviewState = new ReviewState()
