"""InfluxDB 1.x line-protocol exporter for EV charging receipts.

Upsert semantics: each point is keyed by (measurement, tags incl. hash_id, timestamp),
which are stable, so re-exporting overwrites points in place — safe to run every cycle.
Deliberately does NOT issue DELETE/DROP: in InfluxDB 1.x those are asynchronous and race
an immediate re-write, silently dropping freshly-written points. Stdlib only (no deps).
"""
import base64
import logging
import urllib.parse
import urllib.request
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


def _esc_tag(value) -> str:
    """Escape a line-protocol tag key/value."""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(" ", "\\ ")
        .replace(",", "\\,")
        .replace("=", "\\=")
    )


def _esc_field_str(value) -> str:
    """Escape (and quote) a line-protocol string field value."""
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _to_ns(date_str: str) -> int:
    """Parse an ISO date string to epoch nanoseconds."""
    return int(datetime.fromisoformat(date_str).timestamp() * 1_000_000_000)


class InfluxExporter:
    """Writes charging receipts to InfluxDB 1.x via the HTTP /write API."""

    def __init__(self, host, port, database, username="", password="",
                 measurement="charge_receipt", verbose=False):
        self.base = f"http://{host}:{port}"
        self.database = database
        self.username = username or ""
        self.password = password or ""
        self.measurement = measurement or "charge_receipt"
        self.verbose = verbose

    def _auth_header(self) -> dict:
        if self.username:
            token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            return {"Authorization": f"Basic {token}"}
        return {}

    def _line(self, r: dict):
        """Build one line-protocol point from a receipt dict (or None to skip)."""
        cost, date = r.get("cost"), r.get("date")
        if cost is None or not date:
            return None
        try:
            ts = _to_ns(date)
        except (ValueError, TypeError):
            return None

        tags = {
            "provider": _esc_tag(r.get("provider") or "Unknown"),
            "currency": _esc_tag(r.get("currency") or "AUD"),
            "source_type": _esc_tag(r.get("source_type") or "email"),
        }
        if r.get("hash_id"):
            tags["hash_id"] = _esc_tag(r["hash_id"])
        tag_str = ",".join(f"{k}={v}" for k, v in tags.items())

        fields = [f"cost={float(cost)}"]
        energy = r.get("energy_kwh")
        if energy:
            fields.append(f"energy_kwh={float(energy)}")
            try:
                fields.append(f"cost_per_kwh={round(float(cost) / float(energy), 3)}")
            except (ZeroDivisionError, ValueError):
                pass
        if r.get("location"):
            fields.append(f"location={_esc_field_str(str(r['location'])[:120])}")

        return f"{self.measurement},{tag_str} {','.join(fields)} {ts}"

    def export(self, receipts) -> dict:
        """Export receipt dicts to InfluxDB. Returns {'written','skipped','ok'[, 'error']}."""
        lines, skipped = [], 0
        for r in receipts:
            line = self._line(r)
            if line:
                lines.append(line)
            else:
                skipped += 1
        if not lines:
            return {"written": 0, "skipped": skipped, "ok": True}

        url = f"{self.base}/write?" + urllib.parse.urlencode(
            {"db": self.database, "precision": "ns"})
        req = urllib.request.Request(url, data="\n".join(lines).encode("utf-8"), method="POST")
        for k, v in self._auth_header().items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.status
            if self.verbose:
                _LOGGER.debug("InfluxDB export: %d points -> HTTP %s", len(lines), status)
            return {"written": len(lines), "skipped": skipped, "ok": status in (200, 204)}
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("InfluxDB export failed: %s", err)
            return {"written": 0, "skipped": skipped, "ok": False, "error": str(err)}
