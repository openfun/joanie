export type WithId = {
  id: string;
};

type Props<T extends WithId, Payload> = {
  data: T[];
  updateCallback?: (payload: Payload, item?: T) => T;
  createCallback?: (payload: Payload) => T;
};

export const useMockResource = <T extends WithId, Payload>({
  data,
  ...props
}: Props<T, Payload>) => {
  const getResource = (id: string) => {
    const findItem = data.find((item) => item.id === id);
    return findItem ?? data[0];
  };

  const deleteResource = (id: string) => {
    const findIndex = data.findIndex((item) => item.id === id);
    if (findIndex < 0) {
      return;
    }
    data.splice(findIndex, 1);
    return data;
  };

  const createResource = (payload: Payload) => {
    if (!props.createCallback) {
      return;
    }
    const findOrg = props.createCallback(payload);
    data.push(findOrg);
    return findOrg;
  };

  const updateResource = (id: string, payload: Payload) => {
    const findIndex = data.findIndex((item) => item.id === id);

    if (findIndex < 0) {
      return { ...data[0], ...payload };
    }

    let findOrg: T = data[findIndex];
    if (props.updateCallback) {
      findOrg = props.updateCallback(payload, findOrg);
    } else {
      findOrg = { ...data[findIndex], ...payload };
    }

    data[findIndex] = findOrg;
    return findOrg;
  };

  const getRandomResource = (): T => {
    const index = Math.floor(Math.random() * (data.length - 1));
    return data[index];
  };

  const getRandomResources = (count: number = 2): T[] => {
    const result: T[] = [];
    Array.from(Array(count).keys()).forEach(() => {
      result.push(getRandomResource());
    });
    return result;
  };

  return {
    getResource,
    deleteResource,
    updateResource,
    getRandomResource,
    getRandomResources,
    createResource,
    data,
  };
};
