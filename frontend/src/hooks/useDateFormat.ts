import { useQuery } from "@tanstack/react-query";
import API from "../api/client";
import { getItem, setItem } from "../lib/storage";
import { DEFAULT_DATE_FORMAT, DATE_FORMAT_OPTIONS } from "../lib/utils";

const STORAGE_KEY = "date_format";

type DateFormatResponse = { format: string; options: string[] };

/**
 * Provides the configured date format for display across the app.
 * The backend setting is the source of truth; a localStorage copy is kept so
 * the UI can render with the last known value before the network resolves and
 * survives offline use.
 */
export function useDateFormat() {
  const query = useQuery<DateFormatResponse>({
    queryKey: ["date-format"],
    queryFn: async () => (await API.get("/settings/date-format")).data,
    staleTime: 5 * 60 * 1000,
  });

  const format =
    query.data?.format ||
    getItem<string>(STORAGE_KEY, DEFAULT_DATE_FORMAT) ||
    DEFAULT_DATE_FORMAT;

  const options = query.data?.options || DATE_FORMAT_OPTIONS;

  const persist = (fmt: string) => setItem(STORAGE_KEY, fmt);

  return { format, options, persist, ...query };
}
