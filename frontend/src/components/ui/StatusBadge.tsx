const statusStyles: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  reserved: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  expired: "bg-gray-100 text-gray-600",
  cancelled: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize
        ${statusStyles[status] ?? "bg-gray-100 text-gray-700"}`}
    >
      {status}
    </span>
  );
}
