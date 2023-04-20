export const initMocks = async () => {
  if (typeof window === "undefined") {
    console.log("A");
    const { server } = await import("./server");
    await server.listen();
  } else {
    console.log("B");
    const { worker } = await import("./browser");
    await worker.start();
  }
};
