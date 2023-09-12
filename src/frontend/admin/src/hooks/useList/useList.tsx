import { useCallback, useState } from "react";

export function useList<T>(defaultList: T[] = []) {
  const [list, setList] = useState<T[]>(defaultList);

  const set = useCallback((newList: T[]) => {
    setList(newList);
  }, []);

  const push = useCallback((element: T) => {
    setList((prevList) => [...prevList, element]);
  }, []);

  const removeAt = useCallback((index: number) => {
    setList((prevList) => [
      ...prevList.slice(0, index),
      ...prevList.slice(index + 1),
    ]);
  }, []);

  const insertAt = useCallback((index: number, element: T) => {
    setList((prevList) => [
      ...prevList.slice(0, index),
      element,
      ...prevList.slice(index),
    ]);
  }, []);

  const updateAt = useCallback((index: number, element: T) => {
    setList((prevList) => prevList.map((e, i) => (i === index ? element : e)));
  }, []);

  const clear = useCallback(() => setList([]), []);

  return { items: list, set, push, removeAt, insertAt, updateAt, clear };
}
