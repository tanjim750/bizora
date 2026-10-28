"""Deterministic anomaly detection rules and evidence engine.

Serves Business Intelligence specification section 14 (Anomaly Detection).
This is an internal, business-scoped service; callers remain responsible for
authorization before invoking anything here.

Key properties enforced:
1. Deterministic analytical rules:
   - Threshold-Based Detection: upper and lower bound threshold evaluations.
   - Period-over-Period Detection: relative and absolute differences between
     consecutive periods of identical period_type and dimension.
   - Baseline Deviation Detection: comparison against multi-period historical
     baselines.
   - Trend Break Detection: identifies direction changes after established
     multi-period trends.
   - Cross-Domain Detection: evaluates coupled conditions across multiple
     metric domains (e.g., rising marketing spend with falling conversions).
   - Dimension-Level Detection: individual products, campaigns, couriers,
     channels, or customer segments.
2. Honest baseline and sample size handling:
   - Small or missing baselines NEVER generate unsupported anomaly conclusions.
   - Zero or absent baselines yield INSUFFICIENT_DATA (never division-by-zero
     or spurious 100% shifts).
   - Insufficient historical periods yield INSUFFICIENT_DATA instead of fake
     trends.
3. Anomaly evidence preservation:
   - Every detected anomaly references the exact underlying MetricSnapshot IDs
     and values that substantiate it.
4. Tenant isolation:
   - All snapshot lookups and comparisons strictly filter by business_id.
"""

from dataclasses import dataclass, field
from decimal import Decimal, localcontext
import datetime

from django.db import transaction
from django.utils import timezone

from app import models
from . import metrics


class AnomalyValidationError(ValueError):
    """An analytical parameter, period, scope, or rule configuration is invalid."""


class AnomalyScopeError(AnomalyValidationError):
    """An entity does not belong to the requested business."""


class AnomalyRuleError(ValueError):
    """The anomaly rule definition is invalid or inconsistent."""


_PRECISION = 48
_ZERO = Decimal(0)
_QUANTUM = Decimal("0.0001")

# Documented anomaly rule types (BI §14)
RULE_TYPE_THRESHOLD = "THRESHOLD"
RULE_TYPE_PERIOD_COMPARISON = "PERIOD_COMPARISON"
RULE_TYPE_BASELINE_DEVIATION = "BASELINE_DEVIATION"
RULE_TYPE_TREND_BREAK = "TREND_BREAK"
RULE_TYPE_CROSS_DOMAIN = "CROSS_DOMAIN"

RULE_TYPES = frozenset({
    RULE_TYPE_THRESHOLD,
    RULE_TYPE_PERIOD_COMPARISON,
    RULE_TYPE_BASELINE_DEVIATION,
    RULE_TYPE_TREND_BREAK,
    RULE_TYPE_CROSS_DOMAIN,
})

# Anomaly detection outcome statuses
STATUS_ANOMALY_DETECTED = "ANOMALY_DETECTED"
STATUS_NORMAL = "NORMAL"
STATUS_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
STATUS_UNAVAILABLE = "UNAVAILABLE"

# Severities (BI §17 Severity vocabulary)
SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"

SEVERITIES = frozenset({SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL})

DIRECTION_INCREASING = "INCREASING"
DIRECTION_DECREASING = "DECREASING"
DIRECTION_ANY = "ANY"

DIRECTIONS = frozenset({DIRECTION_INCREASING, DIRECTION_DECREASING, DIRECTION_ANY})

REASON_MISSING_CURRENT = "MISSING_CURRENT_SNAPSHOT"
REASON_MISSING_BASELINE = "MISSING_BASELINE_SNAPSHOT"
REASON_SMALL_BASELINE = "INSUFFICIENT_BASELINE_VOLUME"
REASON_INSUFFICIENT_PERIODS = "INSUFFICIENT_BASELINE_PERIODS"
REASON_INSUFFICIENT_TREND_POINTS = "INSUFFICIENT_TREND_OBSERVATIONS"
REASON_NO_TREND_ESTABLISHED = "NO_PRIOR_TREND_ESTABLISHED"


def _ratio(numerator: int | Decimal, denominator: int | Decimal) -> Decimal | None:
    """Exact decimal ratio quantized to 4 decimal places, or None if zero denominator."""
    if not denominator:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        val = Decimal(numerator) / Decimal(denominator)
    return val.quantize(_QUANTUM)


@dataclass(frozen=True)
class AnomalyRuleConfig:
    """Configuration contract for a deterministic anomaly rule."""
    rule_id: str
    rule_type: str
    metric_key: str
    name: str = ""
    description: str = ""
    severity: str = SEVERITY_MEDIUM
    # Dimension targeting (None = business-wide)
    dimension_type: str | None = None
    dimension_value: str | None = None
    # For THRESHOLD rules:
    upper_bound: Decimal | None = None
    lower_bound: Decimal | None = None
    # For PERIOD_COMPARISON and BASELINE_DEVIATION rules:
    significant_change_ratio: Decimal | None = None
    significant_absolute_change: Decimal | None = None
    expected_direction: str = DIRECTION_ANY
    min_baseline_value: Decimal | None = None
    min_baseline_periods: int = 3
    # For TREND_BREAK rules:
    min_trend_periods: int = 3
    # For CROSS_DOMAIN rules:
    secondary_metric_key: str | None = None
    secondary_expected_direction: str = DIRECTION_ANY
    secondary_change_ratio: Decimal | None = None

    def __post_init__(self):
        if not self.rule_id or not str(self.rule_id).strip():
            raise AnomalyRuleError("rule_id must be a non-empty string")
        if self.rule_type not in RULE_TYPES:
            raise AnomalyRuleError(
                f"Unknown rule_type {self.rule_type!r}; expected one of {sorted(RULE_TYPES)}"
            )
        if not self.metric_key or not str(self.metric_key).strip():
            raise AnomalyRuleError("metric_key must be a non-empty string")
        if self.severity not in SEVERITIES:
            raise AnomalyRuleError(
                f"Unknown severity {self.severity!r}; expected one of {sorted(SEVERITIES)}"
            )
        if self.expected_direction not in DIRECTIONS:
            raise AnomalyRuleError(
                f"Unknown expected_direction {self.expected_direction!r}; expected one of {sorted(DIRECTIONS)}"
            )


@dataclass(frozen=True)
class AnomalyDetectionResult:
    """Evidence-backed result of evaluating an anomaly rule."""
    is_anomaly: bool
    status: str
    rule_id: str
    rule_type: str
    metric_key: str
    severity: str | None
    dimension_type: str | None
    dimension_value: str | None
    current_value: Decimal | None
    comparison_value: Decimal | None
    relative_change: Decimal | None
    absolute_change: Decimal | None
    evidence_snapshot_ids: tuple[int, ...]
    message: str
    details: dict = field(default_factory=dict)


def _validate_scope(
    *,
    business_id: int,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
) -> None:
    if not isinstance(business_id, int) or business_id <= 0:
        raise AnomalyValidationError(f"business_id must be a positive integer, got {business_id!r}")
    if not models.Business.objects.filter(pk=business_id).exists():
        raise AnomalyScopeError(f"Business {business_id} does not exist.")
    if not isinstance(period_start, datetime.datetime) or not timezone.is_aware(period_start):
        raise AnomalyValidationError("period_start must be timezone-aware")
    if not isinstance(period_end, datetime.datetime) or not timezone.is_aware(period_end):
        raise AnomalyValidationError("period_end must be timezone-aware")
    if period_start >= period_end:
        raise AnomalyValidationError(
            f"period_start ({period_start}) must precede period_end ({period_end})"
        )
    if period_type not in metrics.PERIOD_TYPES:
        raise AnomalyValidationError(
            f"Unknown period_type {period_type!r}; expected one of {sorted(metrics.PERIOD_TYPES)}"
        )


def evaluate_threshold_rule(
    *,
    business_id: int,
    rule: AnomalyRuleConfig,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
) -> AnomalyDetectionResult:
    """Evaluate a threshold-based anomaly rule (BI §14 Threshold-Based Detection)."""
    current_snap = metrics.get_metric_snapshot(
        business_id=business_id,
        metric_key=rule.metric_key,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
    )

    if current_snap is None:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=None,
            comparison_value=None,
            relative_change=None,
            absolute_change=None,
            evidence_snapshot_ids=(),
            message=f"No metric observation found for {rule.metric_key} in the current period.",
            details={"reason": REASON_MISSING_CURRENT},
        )

    val = current_snap.value
    snap_id = current_snap.snapshot_id

    breached_upper = rule.upper_bound is not None and val > rule.upper_bound
    breached_lower = rule.lower_bound is not None and val < rule.lower_bound

    if breached_upper:
        return AnomalyDetectionResult(
            is_anomaly=True,
            status=STATUS_ANOMALY_DETECTED,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=rule.severity,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=val,
            comparison_value=rule.upper_bound,
            relative_change=_ratio(val - rule.upper_bound, rule.upper_bound) if rule.upper_bound else None,
            absolute_change=val - rule.upper_bound,
            evidence_snapshot_ids=(snap_id,),
            message=(
                f"Metric {rule.metric_key} observed at {val}, exceeding upper threshold "
                f"of {rule.upper_bound}."
            ),
            details={"bound_type": "UPPER", "threshold": rule.upper_bound},
        )
    elif breached_lower:
        return AnomalyDetectionResult(
            is_anomaly=True,
            status=STATUS_ANOMALY_DETECTED,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=rule.severity,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=val,
            comparison_value=rule.lower_bound,
            relative_change=_ratio(val - rule.lower_bound, rule.lower_bound) if rule.lower_bound else None,
            absolute_change=val - rule.lower_bound,
            evidence_snapshot_ids=(snap_id,),
            message=(
                f"Metric {rule.metric_key} observed at {val}, falling below lower threshold "
                f"of {rule.lower_bound}."
            ),
            details={"bound_type": "LOWER", "threshold": rule.lower_bound},
        )

    return AnomalyDetectionResult(
        is_anomaly=False,
        status=STATUS_NORMAL,
        rule_id=rule.rule_id,
        rule_type=rule.rule_type,
        metric_key=rule.metric_key,
        severity=None,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
        current_value=val,
        comparison_value=rule.upper_bound or rule.lower_bound,
        relative_change=None,
        absolute_change=None,
        evidence_snapshot_ids=(snap_id,),
        message=f"Metric {rule.metric_key} observed at {val}, within acceptable threshold bounds.",
        details={"upper_bound": rule.upper_bound, "lower_bound": rule.lower_bound},
    )


def evaluate_period_comparison_rule(
    *,
    business_id: int,
    rule: AnomalyRuleConfig,
    period_type: str,
    current_start: datetime.datetime,
    current_end: datetime.datetime,
    previous_start: datetime.datetime,
    previous_end: datetime.datetime,
) -> AnomalyDetectionResult:
    """Evaluate a period-over-period anomaly rule (BI §14 Period-over-Period Detection)."""
    current_snap = metrics.get_metric_snapshot(
        business_id=business_id,
        metric_key=rule.metric_key,
        period_type=period_type,
        period_start=current_start,
        period_end=current_end,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
    )

    prev_snap = metrics.get_metric_snapshot(
        business_id=business_id,
        metric_key=rule.metric_key,
        period_type=period_type,
        period_start=previous_start,
        period_end=previous_end,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
    )

    evidence_ids: list[int] = []
    if current_snap is not None:
        evidence_ids.append(current_snap.snapshot_id)
    if prev_snap is not None:
        evidence_ids.append(prev_snap.snapshot_id)

    if current_snap is None:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=None,
            comparison_value=prev_snap.value if prev_snap else None,
            relative_change=None,
            absolute_change=None,
            evidence_snapshot_ids=tuple(evidence_ids),
            message=f"No current period observation found for {rule.metric_key}.",
            details={"reason": REASON_MISSING_CURRENT},
        )

    if prev_snap is None:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=current_snap.value,
            comparison_value=None,
            relative_change=None,
            absolute_change=None,
            evidence_snapshot_ids=tuple(evidence_ids),
            message=f"No prior period baseline observation found for {rule.metric_key}.",
            details={"reason": REASON_MISSING_BASELINE},
        )

    curr_val = current_snap.value
    prev_val = prev_snap.value

    # Check for small or zero baseline
    if prev_val == _ZERO:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=curr_val,
            comparison_value=prev_val,
            relative_change=None,
            absolute_change=curr_val - prev_val,
            evidence_snapshot_ids=tuple(evidence_ids),
            message=f"Prior period baseline for {rule.metric_key} is zero; relative change undefined.",
            details={"reason": REASON_SMALL_BASELINE, "baseline_value": prev_val},
        )

    if rule.min_baseline_value is not None and prev_val < rule.min_baseline_value:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=curr_val,
            comparison_value=prev_val,
            relative_change=_ratio(curr_val - prev_val, prev_val),
            absolute_change=curr_val - prev_val,
            evidence_snapshot_ids=tuple(evidence_ids),
            message=(
                f"Prior period baseline ({prev_val}) is below required minimum threshold "
                f"({rule.min_baseline_value}); suppressing unsupported anomaly conclusion."
            ),
            details={"reason": REASON_SMALL_BASELINE, "min_baseline_value": rule.min_baseline_value},
        )

    abs_diff = curr_val - prev_val
    rel_diff = _ratio(abs_diff, prev_val)

    # Direction check
    direction_matches = True
    if rule.expected_direction == DIRECTION_INCREASING:
        direction_matches = abs_diff > _ZERO
    elif rule.expected_direction == DIRECTION_DECREASING:
        direction_matches = abs_diff < _ZERO

    is_anom = False
    if direction_matches:
        if rule.significant_change_ratio is not None and rel_diff is not None:
            if abs(rel_diff) >= rule.significant_change_ratio:
                is_anom = True
        if rule.significant_absolute_change is not None:
            if abs(abs_diff) >= rule.significant_absolute_change:
                is_anom = True

    if is_anom:
        direction_str = "increased" if abs_diff > _ZERO else "decreased"
        return AnomalyDetectionResult(
            is_anomaly=True,
            status=STATUS_ANOMALY_DETECTED,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=rule.severity,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=curr_val,
            comparison_value=prev_val,
            relative_change=rel_diff,
            absolute_change=abs_diff,
            evidence_snapshot_ids=tuple(evidence_ids),
            message=(
                f"Metric {rule.metric_key} significantly {direction_str} from {prev_val} to "
                f"{curr_val} (change of {rel_diff * 100:.2f}%)."
            ),
            details={"previous_value": prev_val, "current_value": curr_val},
        )

    return AnomalyDetectionResult(
        is_anomaly=False,
        status=STATUS_NORMAL,
        rule_id=rule.rule_id,
        rule_type=rule.rule_type,
        metric_key=rule.metric_key,
        severity=None,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
        current_value=curr_val,
        comparison_value=prev_val,
        relative_change=rel_diff,
        absolute_change=abs_diff,
        evidence_snapshot_ids=tuple(evidence_ids),
        message=f"Period-over-period change for {rule.metric_key} is within normal expectations.",
        details={"previous_value": prev_val, "current_value": curr_val},
    )


def evaluate_baseline_deviation_rule(
    *,
    business_id: int,
    rule: AnomalyRuleConfig,
    period_type: str,
    current_start: datetime.datetime,
    current_end: datetime.datetime,
    baseline_window_start: datetime.datetime,
    baseline_window_end: datetime.datetime,
) -> AnomalyDetectionResult:
    """Evaluate baseline deviation against historical observations (BI §14 Baseline Deviation)."""
    current_snap = metrics.get_metric_snapshot(
        business_id=business_id,
        metric_key=rule.metric_key,
        period_type=period_type,
        period_start=current_start,
        period_end=current_end,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
    )

    if current_snap is None:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=None,
            comparison_value=None,
            relative_change=None,
            absolute_change=None,
            evidence_snapshot_ids=(),
            message=f"No current period observation found for {rule.metric_key}.",
            details={"reason": REASON_MISSING_CURRENT},
        )

    # Fetch baseline historical snapshots
    baseline_snaps = list(
        models.MetricSnapshot.objects.filter(
            business_id=business_id,
            metric__key=rule.metric_key,
            period_type=period_type,
            period_start__gte=baseline_window_start,
            period_end__lte=baseline_window_end,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
        ).order_by("period_start", "pk")
    )

    evidence_ids = [current_snap.snapshot_id] + [s.pk for s in baseline_snaps]

    # Verify sample size
    if len(baseline_snaps) < rule.min_baseline_periods:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=current_snap.value,
            comparison_value=None,
            relative_change=None,
            absolute_change=None,
            evidence_snapshot_ids=tuple(evidence_ids),
            message=(
                f"Baseline historical observations ({len(baseline_snaps)}) fewer than required "
                f"minimum ({rule.min_baseline_periods}); suppressing unsupported conclusion."
            ),
            details={
                "reason": REASON_INSUFFICIENT_PERIODS,
                "found_periods": len(baseline_snaps),
                "required_periods": rule.min_baseline_periods,
            },
        )

    # Calculate baseline mean
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        baseline_mean = sum((s.value for s in baseline_snaps), _ZERO) / Decimal(len(baseline_snaps))
        baseline_mean = baseline_mean.quantize(_QUANTUM)

    if baseline_mean == _ZERO or (rule.min_baseline_value and baseline_mean < rule.min_baseline_value):
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=current_snap.value,
            comparison_value=baseline_mean,
            relative_change=None,
            absolute_change=current_snap.value - baseline_mean,
            evidence_snapshot_ids=tuple(evidence_ids),
            message=f"Baseline mean ({baseline_mean}) is insufficient for reliable deviation detection.",
            details={"reason": REASON_SMALL_BASELINE, "baseline_mean": baseline_mean},
        )

    curr_val = current_snap.value
    abs_diff = curr_val - baseline_mean
    rel_diff = _ratio(abs_diff, baseline_mean)

    # Check direction and threshold
    direction_matches = True
    if rule.expected_direction == DIRECTION_INCREASING:
        direction_matches = abs_diff > _ZERO
    elif rule.expected_direction == DIRECTION_DECREASING:
        direction_matches = abs_diff < _ZERO

    is_anom = False
    if direction_matches and rel_diff is not None:
        if rule.significant_change_ratio is not None and abs(rel_diff) >= rule.significant_change_ratio:
            is_anom = True
        if rule.significant_absolute_change is not None and abs(abs_diff) >= rule.significant_absolute_change:
            is_anom = True

    if is_anom:
        direction_str = "above" if abs_diff > _ZERO else "below"
        return AnomalyDetectionResult(
            is_anomaly=True,
            status=STATUS_ANOMALY_DETECTED,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=rule.severity,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=curr_val,
            comparison_value=baseline_mean,
            relative_change=rel_diff,
            absolute_change=abs_diff,
            evidence_snapshot_ids=tuple(evidence_ids),
            message=(
                f"Metric {rule.metric_key} deviates {rel_diff * 100:.2f}% {direction_str} historical "
                f"baseline mean of {baseline_mean} (observed: {curr_val})."
            ),
            details={
                "baseline_mean": baseline_mean,
                "baseline_periods_count": len(baseline_snaps),
                "current_value": curr_val,
            },
        )

    return AnomalyDetectionResult(
        is_anomaly=False,
        status=STATUS_NORMAL,
        rule_id=rule.rule_id,
        rule_type=rule.rule_type,
        metric_key=rule.metric_key,
        severity=None,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
        current_value=curr_val,
        comparison_value=baseline_mean,
        relative_change=rel_diff,
        absolute_change=abs_diff,
        evidence_snapshot_ids=tuple(evidence_ids),
        message=f"Metric {rule.metric_key} is within normal variation from historical baseline mean.",
        details={"baseline_mean": baseline_mean, "current_value": curr_val},
    )


def evaluate_trend_break_rule(
    *,
    business_id: int,
    rule: AnomalyRuleConfig,
    period_type: str,
    current_start: datetime.datetime,
    current_end: datetime.datetime,
    historical_periods: list[tuple[datetime.datetime, datetime.datetime]],
) -> AnomalyDetectionResult:
    """Evaluate trend break detection over consecutive historical observations (BI §14 Trend Break)."""
    current_snap = metrics.get_metric_snapshot(
        business_id=business_id,
        metric_key=rule.metric_key,
        period_type=period_type,
        period_start=current_start,
        period_end=current_end,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
    )

    if current_snap is None:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=None,
            comparison_value=None,
            relative_change=None,
            absolute_change=None,
            evidence_snapshot_ids=(),
            message=f"No current period observation found for {rule.metric_key}.",
            details={"reason": REASON_MISSING_CURRENT},
        )

    if len(historical_periods) < rule.min_trend_periods:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=current_snap.value,
            comparison_value=None,
            relative_change=None,
            absolute_change=None,
            evidence_snapshot_ids=(current_snap.snapshot_id,),
            message=(
                f"Historical periods ({len(historical_periods)}) fewer than required "
                f"minimum ({rule.min_trend_periods}); suppressing trend break evaluation."
            ),
            details={
                "reason": REASON_INSUFFICIENT_TREND_POINTS,
                "found_periods": len(historical_periods),
                "required_periods": rule.min_trend_periods,
            },
        )

    # Fetch snapshots for each historical period in order
    snaps: list[models.MetricSnapshot] = []
    for h_start, h_end in historical_periods:
        s = metrics.get_metric_snapshot(
            business_id=business_id,
            metric_key=rule.metric_key,
            period_type=period_type,
            period_start=h_start,
            period_end=h_end,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
        )
        if s is None:
            # Missing one of the consecutive chain
            return AnomalyDetectionResult(
                is_anomaly=False,
                status=STATUS_INSUFFICIENT_DATA,
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                metric_key=rule.metric_key,
                severity=None,
                dimension_type=rule.dimension_type,
                dimension_value=rule.dimension_value,
                current_value=current_snap.value,
                comparison_value=None,
                relative_change=None,
                absolute_change=None,
                evidence_snapshot_ids=(current_snap.snapshot_id,),
                message="Historical snapshot series contains gaps; cannot verify continuous trend.",
                details={"reason": REASON_INSUFFICIENT_TREND_POINTS},
            )
        snaps.append(s)

    evidence_ids = [current_snap.snapshot_id] + [s.snapshot_id for s in snaps]

    # Evaluate historical direction
    is_historically_increasing = all(
        snaps[i].value > snaps[i - 1].value for i in range(1, len(snaps))
    )
    is_historically_decreasing = all(
        snaps[i].value < snaps[i - 1].value for i in range(1, len(snaps))
    )

    if not is_historically_increasing and not is_historically_decreasing:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_NORMAL,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=current_snap.value,
            comparison_value=snaps[-1].value,
            relative_change=_ratio(current_snap.value - snaps[-1].value, snaps[-1].value),
            absolute_change=current_snap.value - snaps[-1].value,
            evidence_snapshot_ids=tuple(evidence_ids),
            message="No consistent monotonic historical trend was established; no trend break.",
            details={"reason": REASON_NO_TREND_ESTABLISHED},
        )

    last_hist_val = snaps[-1].value
    curr_val = current_snap.value
    abs_diff = curr_val - last_hist_val
    rel_diff = _ratio(abs_diff, last_hist_val)

    # Trend break detection:
    # If historical trend was INCREASING, and current drops
    broke_upward = is_historically_increasing and curr_val < last_hist_val
    # If historical trend was DECREASING, and current jumps
    broke_downward = is_historically_decreasing and curr_val > last_hist_val

    is_anom = False
    if broke_upward:
        if rule.significant_change_ratio is None or (rel_diff and abs(rel_diff) >= rule.significant_change_ratio):
            is_anom = True
    elif broke_downward:
        if rule.significant_change_ratio is None or (rel_diff and abs(rel_diff) >= rule.significant_change_ratio):
            is_anom = True

    if is_anom:
        prior_trend_str = "increasing" if is_historically_increasing else "decreasing"
        break_str = "dropped" if broke_upward else "surged"
        return AnomalyDetectionResult(
            is_anomaly=True,
            status=STATUS_ANOMALY_DETECTED,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=rule.severity,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=curr_val,
            comparison_value=last_hist_val,
            relative_change=rel_diff,
            absolute_change=abs_diff,
            evidence_snapshot_ids=tuple(evidence_ids),
            message=(
                f"Trend break detected: metric {rule.metric_key} was consistently {prior_trend_str} "
                f"over {len(snaps)} periods, but {break_str} to {curr_val} in current period."
            ),
            details={
                "prior_trend": prior_trend_str,
                "periods_in_trend": len(snaps),
                "latest_baseline_value": last_hist_val,
                "current_value": curr_val,
            },
        )

    return AnomalyDetectionResult(
        is_anomaly=False,
        status=STATUS_NORMAL,
        rule_id=rule.rule_id,
        rule_type=rule.rule_type,
        metric_key=rule.metric_key,
        severity=None,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
        current_value=curr_val,
        comparison_value=last_hist_val,
        relative_change=rel_diff,
        absolute_change=abs_diff,
        evidence_snapshot_ids=tuple(evidence_ids),
        message=f"Metric {rule.metric_key} continues its established historical trend direction.",
        details={"current_value": curr_val, "last_baseline_value": last_hist_val},
    )


def evaluate_cross_domain_rule(
    *,
    business_id: int,
    rule: AnomalyRuleConfig,
    period_type: str,
    current_start: datetime.datetime,
    current_end: datetime.datetime,
    previous_start: datetime.datetime,
    previous_end: datetime.datetime,
) -> AnomalyDetectionResult:
    """Evaluate a cross-domain anomaly involving multiple metrics (BI §14 Cross-Domain Anomalies)."""
    if not rule.secondary_metric_key:
        raise AnomalyRuleError("Cross-domain rules must specify secondary_metric_key")

    primary_snap = metrics.get_metric_snapshot(
        business_id=business_id,
        metric_key=rule.metric_key,
        period_type=period_type,
        period_start=current_start,
        period_end=current_end,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
    )
    primary_prev = metrics.get_metric_snapshot(
        business_id=business_id,
        metric_key=rule.metric_key,
        period_type=period_type,
        period_start=previous_start,
        period_end=previous_end,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
    )

    sec_snap = metrics.get_metric_snapshot(
        business_id=business_id,
        metric_key=rule.secondary_metric_key,
        period_type=period_type,
        period_start=current_start,
        period_end=current_end,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
    )
    sec_prev = metrics.get_metric_snapshot(
        business_id=business_id,
        metric_key=rule.secondary_metric_key,
        period_type=period_type,
        period_start=previous_start,
        period_end=previous_end,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
    )

    evidence_ids: list[int] = []
    for s in (primary_snap, primary_prev, sec_snap, sec_prev):
        if s is not None:
            evidence_ids.append(s.snapshot_id)

    if primary_snap is None or primary_prev is None or sec_snap is None or sec_prev is None:
        return AnomalyDetectionResult(
            is_anomaly=False,
            status=STATUS_INSUFFICIENT_DATA,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=None,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=primary_snap.value if primary_snap else None,
            comparison_value=primary_prev.value if primary_prev else None,
            relative_change=None,
            absolute_change=None,
            evidence_snapshot_ids=tuple(evidence_ids),
            message="Cross-domain evaluation requires complete current and previous observations for both metrics.",
            details={"reason": REASON_MISSING_BASELINE},
        )

    p_curr = primary_snap.value
    p_prev = primary_prev.value
    s_curr = sec_snap.value
    s_prev = sec_prev.value

    p_diff = p_curr - p_prev
    s_diff = s_curr - s_prev

    p_rel = _ratio(p_diff, p_prev)
    s_rel = _ratio(s_diff, s_prev)

    # Check primary condition
    p_matches = True
    if rule.expected_direction == DIRECTION_INCREASING:
        p_matches = p_diff > _ZERO
    elif rule.expected_direction == DIRECTION_DECREASING:
        p_matches = p_diff < _ZERO

    if rule.significant_change_ratio is not None and p_rel is not None:
        p_matches = p_matches and abs(p_rel) >= rule.significant_change_ratio

    # Check secondary condition
    s_matches = True
    if rule.secondary_expected_direction == DIRECTION_INCREASING:
        s_matches = s_diff > _ZERO
    elif rule.secondary_expected_direction == DIRECTION_DECREASING:
        s_matches = s_diff < _ZERO

    if rule.secondary_change_ratio is not None and s_rel is not None:
        s_matches = s_matches and abs(s_rel) >= rule.secondary_change_ratio

    if p_matches and s_matches:
        p_dir = "rising" if p_diff > _ZERO else "falling"
        s_dir = "rising" if s_diff > _ZERO else "falling"
        return AnomalyDetectionResult(
            is_anomaly=True,
            status=STATUS_ANOMALY_DETECTED,
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            metric_key=rule.metric_key,
            severity=rule.severity,
            dimension_type=rule.dimension_type,
            dimension_value=rule.dimension_value,
            current_value=p_curr,
            comparison_value=p_prev,
            relative_change=p_rel,
            absolute_change=p_diff,
            evidence_snapshot_ids=tuple(evidence_ids),
            message=(
                f"Cross-domain anomaly detected: {rule.metric_key} is {p_dir} "
                f"({p_prev} → {p_curr}) while {rule.secondary_metric_key} is {s_dir} "
                f"({s_prev} → {s_curr})."
            ),
            details={
                "primary_metric": rule.metric_key,
                "primary_change_ratio": p_rel,
                "secondary_metric": rule.secondary_metric_key,
                "secondary_change_ratio": s_rel,
            },
        )

    return AnomalyDetectionResult(
        is_anomaly=False,
        status=STATUS_NORMAL,
        rule_id=rule.rule_id,
        rule_type=rule.rule_type,
        metric_key=rule.metric_key,
        severity=None,
        dimension_type=rule.dimension_type,
        dimension_value=rule.dimension_value,
        current_value=p_curr,
        comparison_value=p_prev,
        relative_change=p_rel,
        absolute_change=p_diff,
        evidence_snapshot_ids=tuple(evidence_ids),
        message="Cross-domain conditions for anomaly were not satisfied.",
        details={
            "primary_metric": rule.metric_key,
            "secondary_metric": rule.secondary_metric_key,
        },
    )


# Standard documented anomaly rules (BI §14)
STANDARD_ANOMALY_RULES: dict[str, AnomalyRuleConfig] = {
    "delivery_failure_high": AnomalyRuleConfig(
        rule_id="anom.delivery.failure_rate.high",
        rule_type=RULE_TYPE_THRESHOLD,
        metric_key="bi.metric.delivery_failure_rate.v1",
        name="High Delivery Failure Rate",
        upper_bound=Decimal("0.1500"),
        severity=SEVERITY_HIGH,
        description="Delivery failure rate exceeds 15% threshold.",
    ),
    "cart_abandonment_high": AnomalyRuleConfig(
        rule_id="anom.website.cart_abandonment.high",
        rule_type=RULE_TYPE_THRESHOLD,
        metric_key="bi.metric.website_cart_abandonment_rate.v1",
        name="High Cart Abandonment Rate",
        upper_bound=Decimal("0.7500"),
        severity=SEVERITY_MEDIUM,
        description="Website cart abandonment rate exceeds 75% threshold.",
    ),
    "support_response_time_delay": AnomalyRuleConfig(
        rule_id="anom.support.response_time.delay",
        rule_type=RULE_TYPE_THRESHOLD,
        metric_key="bi.metric.support_response_time.v1",
        name="Support Response Delay",
        upper_bound=Decimal("3600.0000"),
        severity=SEVERITY_HIGH,
        description="Average initial support response time exceeds 1 hour (3600 seconds).",
    ),
    "roas_low_threshold": AnomalyRuleConfig(
        rule_id="anom.marketing.roas.low",
        rule_type=RULE_TYPE_THRESHOLD,
        metric_key="bi.metric.marketing_return_on_ad_spend.v1",
        name="Low Return On Ad Spend",
        lower_bound=Decimal("1.0000"),
        severity=SEVERITY_HIGH,
        description="Campaign ROAS fell below break-even threshold (1.0).",
    ),
    "revenue_sharp_decline": AnomalyRuleConfig(
        rule_id="anom.revenue.net.sharp_decline",
        rule_type=RULE_TYPE_PERIOD_COMPARISON,
        metric_key="bi.metric.revenue_net.v1",
        name="Sharp Net Revenue Decline",
        expected_direction=DIRECTION_DECREASING,
        significant_change_ratio=Decimal("0.2000"),
        min_baseline_value=Decimal("100.0000"),
        severity=SEVERITY_HIGH,
        description="Net revenue declined by 20% or more period-over-period.",
    ),
    "cross_domain_spend_up_conversions_down": AnomalyRuleConfig(
        rule_id="anom.cross_domain.spend_rising_conversions_falling",
        rule_type=RULE_TYPE_CROSS_DOMAIN,
        metric_key="bi.metric.marketing_spend.v1",
        secondary_metric_key="bi.metric.marketing_conversions.v1",
        name="Spend Rising While Conversions Falling",
        expected_direction=DIRECTION_INCREASING,
        secondary_expected_direction=DIRECTION_DECREASING,
        severity=SEVERITY_HIGH,
        description="Ad spend increased while marketing conversions decreased.",
    ),
}


def evaluate_anomaly_rule(
    *,
    business_id: int,
    rule: AnomalyRuleConfig,
    period_type: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    previous_period_start: datetime.datetime | None = None,
    previous_period_end: datetime.datetime | None = None,
    baseline_window_start: datetime.datetime | None = None,
    baseline_window_end: datetime.datetime | None = None,
    historical_periods: list[tuple[datetime.datetime, datetime.datetime]] | None = None,
) -> AnomalyDetectionResult:
    """Evaluate an anomaly rule against the business's metric snapshots."""
    _validate_scope(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
    )

    if rule.rule_type == RULE_TYPE_THRESHOLD:
        return evaluate_threshold_rule(
            business_id=business_id,
            rule=rule,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
        )

    elif rule.rule_type == RULE_TYPE_PERIOD_COMPARISON:
        if previous_period_start is None or previous_period_end is None:
            raise AnomalyValidationError(
                "PERIOD_COMPARISON rules require previous_period_start and previous_period_end."
            )
        return evaluate_period_comparison_rule(
            business_id=business_id,
            rule=rule,
            period_type=period_type,
            current_start=period_start,
            current_end=period_end,
            previous_start=previous_period_start,
            previous_end=previous_period_end,
        )

    elif rule.rule_type == RULE_TYPE_BASELINE_DEVIATION:
        if baseline_window_start is None or baseline_window_end is None:
            raise AnomalyValidationError(
                "BASELINE_DEVIATION rules require baseline_window_start and baseline_window_end."
            )
        return evaluate_baseline_deviation_rule(
            business_id=business_id,
            rule=rule,
            period_type=period_type,
            current_start=period_start,
            current_end=period_end,
            baseline_window_start=baseline_window_start,
            baseline_window_end=baseline_window_end,
        )

    elif rule.rule_type == RULE_TYPE_TREND_BREAK:
        if historical_periods is None:
            raise AnomalyValidationError(
                "TREND_BREAK rules require historical_periods (list of ordered period tuples)."
            )
        return evaluate_trend_break_rule(
            business_id=business_id,
            rule=rule,
            period_type=period_type,
            current_start=period_start,
            current_end=period_end,
            historical_periods=historical_periods,
        )

    elif rule.rule_type == RULE_TYPE_CROSS_DOMAIN:
        if previous_period_start is None or previous_period_end is None:
            raise AnomalyValidationError(
                "CROSS_DOMAIN comparison rules require previous_period_start and previous_period_end."
            )
        return evaluate_cross_domain_rule(
            business_id=business_id,
            rule=rule,
            period_type=period_type,
            current_start=period_start,
            current_end=period_end,
            previous_start=previous_period_start,
            previous_end=previous_period_end,
        )

    raise AnomalyRuleError(f"Unhandled rule type {rule.rule_type!r}")


__all__ = [
    "AnomalyDetectionResult",
    "AnomalyRuleConfig",
    "AnomalyRuleError",
    "AnomalyScopeError",
    "AnomalyValidationError",
    "DIRECTIONS",
    "DIRECTION_ANY",
    "DIRECTION_DECREASING",
    "DIRECTION_INCREASING",
    "REASON_INSUFFICIENT_PERIODS",
    "REASON_INSUFFICIENT_TREND_POINTS",
    "REASON_MISSING_BASELINE",
    "REASON_MISSING_CURRENT",
    "REASON_NO_TREND_ESTABLISHED",
    "REASON_SMALL_BASELINE",
    "RULE_TYPES",
    "RULE_TYPE_BASELINE_DEVIATION",
    "RULE_TYPE_CROSS_DOMAIN",
    "RULE_TYPE_PERIOD_COMPARISON",
    "RULE_TYPE_THRESHOLD",
    "RULE_TYPE_TREND_BREAK",
    "SEVERITIES",
    "SEVERITY_CRITICAL",
    "SEVERITY_HIGH",
    "SEVERITY_LOW",
    "SEVERITY_MEDIUM",
    "STANDARD_ANOMALY_RULES",
    "STATUS_ANOMALY_DETECTED",
    "STATUS_INSUFFICIENT_DATA",
    "STATUS_NORMAL",
    "STATUS_UNAVAILABLE",
    "evaluate_anomaly_rule",
    "evaluate_baseline_deviation_rule",
    "evaluate_cross_domain_rule",
    "evaluate_period_comparison_rule",
    "evaluate_threshold_rule",
    "evaluate_trend_break_rule",
]
