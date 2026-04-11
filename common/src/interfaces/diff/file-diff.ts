export interface FileDiff {
  path: string
  language: string
  addedLines: string[]
  removedLines: string[]
  content: string
  isNewFile: boolean
  isDeleted: boolean
  isBinary: boolean
}
