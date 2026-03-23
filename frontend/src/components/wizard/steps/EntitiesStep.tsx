import WizardStep from "../WizardStep";

interface Entity {
  name: string;
  type: string;
  state: string;
  ein: string;
}

interface Props {
  value: Entity[];
  onChange: (v: Entity[]) => void;
}

const EMPTY: Entity = { name: "", type: "", state: "", ein: "" };

export default function EntitiesStep({ value, onChange }: Props) {
  const hasEntities = value.length > 0;

  const addEntity = () => onChange([...value, { ...EMPTY }]);
  const removeEntity = (i: number) => onChange(value.filter((_, idx) => idx !== i));
  const updateEntity = (i: number, field: keyof Entity, val: string) => {
    const updated = [...value];
    updated[i] = { ...updated[i], [field]: val };
    onChange(updated);
  };

  return (
    <WizardStep title="Do you own or control any business entities?">
      {!hasEntities ? (
        <div className="flex gap-3">
          <button
            type="button"
            onClick={addEntity}
            className="rounded-lg border-2 border-stone-200 p-4 flex-1 hover:border-stone-300"
          >
            Yes
          </button>
          <button
            type="button"
            onClick={() => onChange([])}
            className="rounded-lg border-2 border-stone-800 bg-stone-50 p-4 flex-1"
          >
            No
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {value.map((entity, i) => (
            <div key={i} className="rounded-lg border border-stone-200 p-4 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-stone-500">Entity {i + 1}</span>
                <button type="button" onClick={() => removeEntity(i)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
              </div>
              <input placeholder="Entity name" value={entity.name} onChange={(e) => updateEntity(i, "name", e.target.value)} className="w-full rounded border border-stone-300 px-3 py-2 text-sm" />
              <div className="grid grid-cols-3 gap-2">
                <select value={entity.type} onChange={(e) => updateEntity(i, "type", e.target.value)} className="rounded border border-stone-300 px-3 py-2 text-sm">
                  <option value="">Type</option>
                  <option value="LLC">LLC</option>
                  <option value="C-Corp">C-Corp</option>
                  <option value="S-Corp">S-Corp</option>
                  <option value="Partnership">Partnership</option>
                </select>
                <input placeholder="State" value={entity.state} onChange={(e) => updateEntity(i, "state", e.target.value)} className="rounded border border-stone-300 px-3 py-2 text-sm" />
                <input placeholder="EIN" value={entity.ein} onChange={(e) => updateEntity(i, "ein", e.target.value)} className="rounded border border-stone-300 px-3 py-2 text-sm" />
              </div>
            </div>
          ))}
          <button type="button" onClick={addEntity} className="text-sm text-stone-600 hover:text-stone-800">
            + Add another entity
          </button>
        </div>
      )}
    </WizardStep>
  );
}
