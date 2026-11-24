import type { Status } from "../api";
import { STATUS_LABEL } from "../format";

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABEL[status]}</span>;
}
