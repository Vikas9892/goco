import type { Status } from "../api";
import { STATUS_LABEL } from "../format";

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`badge badge-${status}`}><i className="badge-dot" />{STATUS_LABEL[status]}</span>;
}
