/**
 * Type definitions for nsqjs (untyped package).
 */

declare module 'nsqjs' {
  import { EventEmitter } from 'events';

  export class Reader extends EventEmitter {
    constructor(topic: string, channel: string, options?: Record<string, unknown>);
    connect(): void;
    close(): void;
    pause(): void;
    unpause(): void;
    isPaused(): boolean;
    on(event: string, handler: (...args: unknown[]) => void): this;
  }

  export class Writer extends EventEmitter {
    constructor(nsqdHost: string, nsqdPort?: number | string, options?: Record<string, unknown>);
    connect(): void;
    close(): void;
    publish(topic: string, message: string | string[], callback?: (err: unknown) => void): void;
    send(topic: string, message: string | Buffer, callback?: (err: unknown) => void): void;
    end(): void;
    on(event: string, handler: (...args: unknown[]) => void): this;
  }

  export const ReaderConfig: any;
  export const ConnectionConfig: any;
}
