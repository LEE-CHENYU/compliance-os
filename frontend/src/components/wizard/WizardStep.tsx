interface Props {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export default function WizardStep({ title, subtitle, children }: Props) {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">{title}</h2>
        {subtitle && <p className="text-sm text-stone-500">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
