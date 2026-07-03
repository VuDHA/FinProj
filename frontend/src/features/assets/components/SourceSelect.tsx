import { useQuery } from "@tanstack/react-query";
import { getSourcesForType } from "../../../api/settings";
import { labels } from "../../../i18n/vi";

interface SourceInfo {
  code: string;
  name: string;
  description: string;
  supports_history: boolean;
  supports_listing: boolean;
}

interface SourceSelectProps {
  assetType: string;
  value: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
}

export function SourceSelect({ assetType, value, onChange, disabled }: SourceSelectProps) {
  const sources = useQuery<SourceInfo[]>({
    queryKey: ["sources", assetType],
    queryFn: async () => getSourcesForType(assetType),
    enabled: !!assetType,
  });

  return (
    <select
      className="input-fintech"
      value={value || ""}
      onChange={(e) => onChange(e.target.value || null)}
      disabled={disabled || sources.isLoading}
    >
      <option value="">{labels.sources.useDefault}</option>
      {sources.data?.map((source) => (
        <option key={source.code} value={source.code}>
          {source.name}
        </option>
      ))}
    </select>
  );
}
