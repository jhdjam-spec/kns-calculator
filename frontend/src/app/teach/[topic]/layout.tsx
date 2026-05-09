// Server-side generateStaticParams для static export.
// 7 тем энциклопедии — список фиксирован, синхронизирован с backend
// pump_calculator/encyclopedia/registry.py

const TOPIC_KEYS = [
  "fire",
  "water",
  "electrical",
  "hydraulics",
  "structural",
  "los",
  "documentation",
] as const;

export function generateStaticParams() {
  return TOPIC_KEYS.map((topic) => ({ topic }));
}

export default function TeachTopicLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
