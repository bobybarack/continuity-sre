import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class NormalizedIntegrationModel(BaseModel):
    """Base model providing dict-style key access and safe retrieval for backward compatibility."""
    model_config = {"extra": "allow"}

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)

class PrometheusQueryResult(NormalizedIntegrationModel):
    """Normalized result representation for Prometheus / Mimir queries across MCP and direct REST."""
    status: str = "success"
    query: str = ""
    result_type: str = "vector"
    metric_value: Optional[float] = None
    data: Optional[Dict[str, Any]] = None
    raw: Any = None
    source: str = "direct_rest"
    error: Optional[str] = None

class LokiQueryResult(NormalizedIntegrationModel):
    """Normalized result representation for Loki log queries across MCP and direct REST."""
    status: str = "success"
    query: str = ""
    lines: List[str] = Field(default_factory=list)
    entry_count: int = 0
    data: Optional[Dict[str, Any]] = None
    raw: Any = None
    source: str = "direct_rest"
    error: Optional[str] = None

class GrafanaIncidentRef(NormalizedIntegrationModel):
    """Normalized incident record representation across MCP and direct IRM / annotation fallback."""
    status: str = "success"
    incident_id: str
    id: str
    title: str = ""
    severity: str = "CRITICAL"
    lifecycle_status: str = "active"
    summary: Optional[str] = None
    source: str = "direct_rest"
    raw: Any = None
    error: Optional[str] = None

class GrafanaAnnotationRef(NormalizedIntegrationModel):
    """Normalized dashboard annotation record representation across MCP and direct REST."""
    status: str = "success"
    id: Optional[int] = None
    text: str = ""
    tags: List[str] = Field(default_factory=list)
    source: str = "direct_rest"
    raw: Any = None
    error: Optional[str] = None

def normalize_prometheus_result(raw: Any, query: str = "", source: str = "direct_rest") -> PrometheusQueryResult:
    """Transforms heterogeneous Prometheus payloads from MCP or REST into a normalized model."""
    if isinstance(raw, PrometheusQueryResult):
        return raw

    if raw is None:
        return PrometheusQueryResult(
            status="error",
            query=query,
            source=source,
            error="Empty Prometheus response"
        )

    if not isinstance(raw, dict):
        return PrometheusQueryResult(
            status="success",
            query=query,
            raw=raw,
            source=source
        )

    if raw.get("status") == "error" or "error" in raw:
        err_msg = raw.get("error") or raw.get("response") or "Prometheus query failed"
        return PrometheusQueryResult(
            status="error",
            query=query,
            raw=raw,
            source=source,
            error=str(err_msg)
        )

    data_field = raw.get("data")
    result_list = []
    result_type = "vector"

    if isinstance(data_field, dict):
        result_type = data_field.get("resultType", "vector")
        result_list = data_field.get("result", [])
    elif isinstance(data_field, list):
        result_list = data_field

    metric_value: Optional[float] = None
    if isinstance(result_list, list) and len(result_list) > 0:
        first_item = result_list[0]
        if isinstance(first_item, dict):
            first_val = first_item.get("value")
            if isinstance(first_val, (list, tuple)) and len(first_val) >= 2:
                try:
                    raw_num = float(first_val[1])
                    metric_value = round(raw_num * 100.0, 2) if raw_num <= 1.0 else round(raw_num, 2)
                except (ValueError, TypeError):
                    metric_value = None
            elif "value" in first_item and isinstance(first_item["value"], (int, float)):
                metric_value = float(first_item["value"])
        elif isinstance(first_item, (int, float)):
            metric_value = float(first_item)
    elif "value" in raw and isinstance(raw["value"], (int, float, str)):
        try:
            raw_num = float(raw["value"])
            metric_value = round(raw_num * 100.0, 2) if raw_num <= 1.0 else round(raw_num, 2)
        except (ValueError, TypeError):
            metric_value = None

    return PrometheusQueryResult(
        status="success",
        query=query,
        result_type=result_type,
        metric_value=metric_value,
        data=data_field if isinstance(data_field, dict) else {"result": result_list},
        raw=raw,
        source=source
    )

def normalize_loki_result(raw: Any, query: str = "", source: str = "direct_rest") -> LokiQueryResult:
    """Transforms heterogeneous Loki payloads from MCP or REST into a normalized model."""
    if isinstance(raw, LokiQueryResult):
        return raw

    if raw is None:
        return LokiQueryResult(
            status="error",
            query=query,
            source=source,
            error="Empty Loki response"
        )

    if isinstance(raw, list):
        lines = [str(item) for item in raw]
        return LokiQueryResult(
            status="success",
            query=query,
            lines=lines,
            entry_count=len(lines),
            raw=raw,
            source=source
        )

    if not isinstance(raw, dict):
        return LokiQueryResult(
            status="success",
            query=query,
            lines=[str(raw)],
            entry_count=1,
            raw=raw,
            source=source
        )

    if raw.get("status") == "error" or "error" in raw:
        err_msg = raw.get("error") or raw.get("response") or "Loki query failed"
        return LokiQueryResult(
            status="error",
            query=query,
            raw=raw,
            source=source,
            error=str(err_msg)
        )

    lines: List[str] = []
    data_field = raw.get("data")

    if "lines" in raw and isinstance(raw["lines"], list):
        lines = [str(l) for l in raw["lines"]]
    elif isinstance(data_field, dict):
        stream_results = data_field.get("result", [])
        if isinstance(stream_results, list):
            for stream_entry in stream_results:
                if isinstance(stream_entry, dict):
                    vals = stream_entry.get("values", [])
                    if isinstance(vals, list):
                        for pair in vals:
                            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                                lines.append(str(pair[1]))
                            elif isinstance(pair, str):
                                lines.append(pair)
    elif isinstance(data_field, list):
        lines = [str(item) for item in data_field]

    return LokiQueryResult(
        status="success",
        query=query,
        lines=lines,
        entry_count=len(lines),
        data=data_field if isinstance(data_field, dict) else None,
        raw=raw,
        source=source
    )

def normalize_incident_result(
    raw: Any,
    default_title: str = "",
    default_severity: str = "CRITICAL",
    source: str = "direct_rest"
) -> GrafanaIncidentRef:
    """Normalizes raw response from MCP tool or direct API into a canonical GrafanaIncidentRef."""
    if isinstance(raw, GrafanaIncidentRef):
        return raw

    if not isinstance(raw, dict):
        fallback_id = f"INC-{int(time.time())}"
        return GrafanaIncidentRef(
            status="error" if raw is None else "success",
            incident_id=fallback_id,
            id=fallback_id,
            title=default_title,
            severity=default_severity,
            lifecycle_status="active",
            source=source,
            raw=raw,
            error="Invalid incident payload" if raw is None else None
        )

    incident_id = (
        raw.get("incident_id") or
        raw.get("id") or
        (raw.get("incident", {}).get("id") if isinstance(raw.get("incident"), dict) else None) or
        (raw.get("Payload", {}).get("id") if isinstance(raw.get("Payload"), dict) else None) or
        f"INC-{int(time.time())}"
    )
    title = raw.get("title") or (raw.get("incident", {}).get("title") if isinstance(raw.get("incident"), dict) else default_title)
    severity = raw.get("severity") or (raw.get("incident", {}).get("severity") if isinstance(raw.get("incident"), dict) else default_severity)

    nested_status = raw.get("incident", {}).get("status") if isinstance(raw.get("incident"), dict) else None
    if nested_status:
        lifecycle_status = nested_status
    elif raw.get("lifecycle_status"):
        lifecycle_status = raw.get("lifecycle_status")
    elif raw.get("status") and raw.get("status") not in ("success", "error"):
        lifecycle_status = raw.get("status")
    else:
        lifecycle_status = "active"

    summary = raw.get("summary") or (raw.get("incident", {}).get("summary") if isinstance(raw.get("incident"), dict) else None)
    status = "error" if raw.get("status") == "error" else "success"
    err = raw.get("error")

    return GrafanaIncidentRef(
        status=status,
        incident_id=str(incident_id),
        id=str(incident_id),
        title=str(title),
        severity=str(severity),
        lifecycle_status=str(lifecycle_status),
        summary=summary,
        source=source,
        raw=raw,
        error=err
    )

def normalize_annotation_result(raw: Any, source: str = "direct_rest") -> GrafanaAnnotationRef:
    """Normalizes raw annotation response from MCP tool or direct API into a canonical GrafanaAnnotationRef."""
    if isinstance(raw, GrafanaAnnotationRef):
        return raw

    if not isinstance(raw, dict):
        return GrafanaAnnotationRef(
            status="error",
            id=None,
            source=source,
            raw=raw,
            error="Invalid annotation payload"
        )

    ann_id = (
        raw.get("id") or
        (raw.get("annotation", {}).get("id") if isinstance(raw.get("annotation"), dict) else None) or
        (raw.get("Payload", {}).get("id") if isinstance(raw.get("Payload"), dict) else None)
    )
    parsed_id = int(ann_id) if ann_id and str(ann_id).isdigit() else None
    status = "error" if raw.get("status") == "error" else "success"
    text = raw.get("text") or raw.get("message") or ""
    tags = raw.get("tags") or []

    return GrafanaAnnotationRef(
        status=status,
        id=parsed_id,
        text=text,
        tags=tags,
        source=source,
        raw=raw,
        error=raw.get("error")
    )
