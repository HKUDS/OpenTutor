/**
 * Minimal module declaration for js-yaml to satisfy the Playwright audit suite
 * without pulling additional type dependencies into the UI bundle.
 */
declare module 'js-yaml' {
  interface LoadOptions {
    schema?: unknown
    onWarning?: (warning: Error) => void
  }

  export function load(content: string, options?: LoadOptions): unknown

  const yaml: {
    load: typeof load
  }

  export default yaml
}
