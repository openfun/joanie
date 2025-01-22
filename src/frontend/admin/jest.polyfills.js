
import { Blob, File } from "node:buffer";
Object.defineProperties(globalThis, {
  Blob: { value: Blob },
  File: { value: File },
});
