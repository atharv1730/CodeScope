import { useEffect, useState } from "react";
import { getSection } from "../api/client";

// Loads one analysis section, with loading/error state.
export function useSection(id, section) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    getSection(id, section)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [id, section]);

  return { data, error, loading };
}
