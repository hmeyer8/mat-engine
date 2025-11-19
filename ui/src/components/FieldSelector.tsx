import { FormEvent } from "react";

interface Props {
  fieldId: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
}

export function FieldSelector({ fieldId, onChange, onSubmit, loading }: Props) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form className="card field-form" onSubmit={handleSubmit}>
      <input
        value={fieldId}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Enter field ID (e.g., demo-field)"
        aria-label="Field identifier"
      />
      <button type="submit" disabled={!fieldId.trim() || loading}>
        {loading ? "Loading" : "Load insights"}
      </button>
    </form>
  );
}
