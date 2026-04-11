// Minimal ambient declarations for LangChain packages before `bun install` runs.
// These are replaced by the real types once node_modules exist.

declare module '@langchain/anthropic' {
  export class ChatAnthropic {
    constructor(config: Record<string, unknown>)
    invoke(input: string): Promise<{ content: string }>
    bindTools(tools: unknown[]): ChatAnthropic
    pipe(next: unknown): unknown
  }
}

declare module '@langchain/openai' {
  export class ChatOpenAI {
    constructor(config: Record<string, unknown>)
    invoke(input: string): Promise<{ content: string }>
    bindTools(tools: unknown[]): ChatOpenAI
    pipe(next: unknown): unknown
  }
}

declare module '@langchain/google-genai' {
  export class ChatGoogleGenerativeAI {
    constructor(config: Record<string, unknown>)
    invoke(input: string): Promise<{ content: string }>
    bindTools(tools: unknown[]): ChatGoogleGenerativeAI
    pipe(next: unknown): unknown
  }
}

declare module '@langchain/ollama' {
  export class ChatOllama {
    constructor(config: Record<string, unknown>)
    invoke(input: string): Promise<{ content: string }>
    bindTools(tools: unknown[]): ChatOllama
    pipe(next: unknown): unknown
  }
}

declare module '@langchain/core/language_models/chat_models' {
  export abstract class BaseChatModel {
    invoke(input: string): Promise<{ content: string }>
    bindTools(tools: unknown[]): this
    pipe(next: unknown): unknown
  }
}

declare module '@langchain/core/tools' {
  export class DynamicStructuredTool<T = unknown> {
    constructor(config: Record<string, unknown>)
    name: string
    description: string
    schema: unknown
    func: (input: T) => Promise<string>
  }
  export function tool(fn: unknown, config: unknown): DynamicStructuredTool
}

declare module '@langchain/core/messages' {
  export class HumanMessage {
    constructor(content: string)
    content: string
  }
  export class AIMessage {
    constructor(content: string)
    content: string
  }
  export class SystemMessage {
    constructor(content: string)
    content: string
  }
  export class ToolMessage {
    constructor(config: Record<string, unknown>)
    content: string
    tool_call_id: string
  }
  export type BaseMessage = HumanMessage | AIMessage | SystemMessage | ToolMessage
}

declare module '@langchain/langgraph' {
  export class StateGraph<T = unknown> {
    constructor(config: unknown)
    addNode(name: string, node: unknown): this
    addEdge(from: string, to: string): this
    addConditionalEdges(from: string, condition: unknown, map: unknown): this
    setEntryPoint(name: string): this
    setFinishPoint(name: string): this
    compile(config?: Record<string, unknown>): CompiledGraph<T>
  }
  export class CompiledGraph<T = unknown> {
    invoke(state: T): Promise<T>
    stream(state: T): AsyncGenerator<T>
  }
  export const END: string
  export const START: string
  export function createReactAgent(config: Record<string, unknown>): CompiledGraph
  export function MemorySaver(): unknown
}

declare module '@langchain/langgraph/prebuilt' {
  export function createReactAgent(config: Record<string, unknown>): import('@langchain/langgraph').CompiledGraph
}

declare module 'langsmith' {
  export class Client {
    constructor(config?: Record<string, unknown>)
    createRun(config: Record<string, unknown>): Promise<void>
    updateRun(id: string, config: Record<string, unknown>): Promise<void>
  }
}

declare module 'langsmith/traceable' {
  export function traceable<T extends (...args: unknown[]) => unknown>(
    fn: T,
    config?: Record<string, unknown>
  ): T
}
