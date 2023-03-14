export const initMocks = async () => {
  if (typeof window === "undefined") {
    const { server } = await import("./server");
    await server.listen();
  } else {
    const { worker } = await import("./browser");
    await worker.start();
  }
};
