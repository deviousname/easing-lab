"""Side-effect-free easing functions and editable Hermite curves.

The functions in this module expect normalized time in the inclusive range
``[0.0, 1.0]``. Use :func:`evaluate` or :func:`interpolate` when automatic
input clamping is useful.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeAlias

EasingFunction: TypeAlias = Callable[[float], float]
Point: TypeAlias = tuple[float, float]
FORMAT_NAME = "easing-lab"
FORMAT_VERSION = 1


class InvalidCurveError(ValueError):
    """Raised when control points or an Easing Lab document are invalid."""


def clamp(value: float, low: float, high: float) -> float:
    """Return *value* constrained to the inclusive ``[low, high]`` range."""

    if low > high:
        raise ValueError("low must not be greater than high")
    return max(low, min(high, value))


def clamp01(value: float) -> float:
    """Return *value* constrained to normalized time."""

    return clamp(value, 0.0, 1.0)


# Derived: standard normalized easing equations, preserved from the original
# proof of concept. They have no Pygame dependency and no import-time effects.
# The Back, Bounce, and Elastic families descend from Robert Penner's easing
# equations; the formulas and family names are also catalogued by easings.net.
def linear(t: float) -> float:
    """Move at constant speed."""

    return t


def sine_in(t: float) -> float:
    """Start a sine-based movement slowly."""

    return 1.0 - math.cos((math.pi * t) / 2.0)


def sine_out(t: float) -> float:
    """Finish a sine-based movement slowly."""

    return math.sin((math.pi * t) / 2.0)


def sine_in_out(t: float) -> float:
    """Ease using the one-dimensional projection of circular motion."""

    return 0.5 - 0.5 * math.cos(math.pi * t)


def smoothstep(t: float) -> float:
    """Cubic smoothstep with zero first derivative at both endpoints."""

    return t * t * (3.0 - 2.0 * t)


def smootherstep(t: float) -> float:
    """Quintic smoothstep with zero first and second endpoint derivatives."""

    return t**3 * (t * (t * 6.0 - 15.0) + 10.0)


def cubic_in(t: float) -> float:
    """Accelerate with a cubic curve."""

    return t**3


def cubic_out(t: float) -> float:
    """Decelerate with a cubic curve."""

    return 1.0 - (1.0 - t) ** 3


def cubic_in_out(t: float) -> float:
    """Symmetric cubic ease-in-out."""

    if t < 0.5:
        return 4.0 * t**3
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def quint_in(t: float) -> float:
    """Accelerate with a quintic curve."""

    return t**5


def quint_out(t: float) -> float:
    """Decelerate with a quintic curve."""

    return 1.0 - (1.0 - t) ** 5


def quint_in_out(t: float) -> float:
    """Symmetric quintic ease-in-out."""

    if t < 0.5:
        return 16.0 * t**5
    return 1.0 - ((-2.0 * t + 2.0) ** 5) / 2.0


def back_in(t: float) -> float:
    """Anticipate the movement using Robert Penner's Back family."""

    c1 = 1.70158
    c3 = c1 + 1.0
    return c3 * t**3 - c1 * t**2


def back_out(t: float) -> float:
    """Overshoot the target using Robert Penner's Back family."""

    c1 = 1.70158
    c3 = c1 + 1.0
    x = t - 1.0
    return 1.0 + c3 * x**3 + c1 * x**2


def back_in_out(t: float) -> float:
    """Anticipate and overshoot using Robert Penner's Back family."""

    c1 = 1.70158
    c2 = c1 * 1.525
    if t < 0.5:
        x = 2.0 * t
        return (x * x * ((c2 + 1.0) * x - c2)) / 2.0
    x = 2.0 * t - 2.0
    return (x * x * ((c2 + 1.0) * x + c2) + 2.0) / 2.0


def bounce_out(t: float) -> float:
    """Land with a rebound using Robert Penner's Bounce family."""

    n1 = 7.5625
    d1 = 2.75
    if t < 1.0 / d1:
        return n1 * t * t
    if t < 2.0 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def bounce_in(t: float) -> float:
    """Start with a rebound using Robert Penner's Bounce family."""

    return 1.0 - bounce_out(1.0 - t)


def bounce_in_out(t: float) -> float:
    """Rebound at both ends using Robert Penner's Bounce family."""

    if t < 0.5:
        return (1.0 - bounce_out(1.0 - 2.0 * t)) / 2.0
    return (1.0 + bounce_out(2.0 * t - 1.0)) / 2.0


def elastic_in(t: float) -> float:
    """Wind up with Robert Penner's oscillating Elastic family."""

    if t == 0.0 or t == 1.0:
        return t
    c4 = (2.0 * math.pi) / 3.0
    return -(2.0 ** (10.0 * t - 10.0)) * math.sin((10.0 * t - 10.75) * c4)


def elastic_out(t: float) -> float:
    """Settle with Robert Penner's oscillating Elastic family."""

    if t == 0.0 or t == 1.0:
        return t
    c4 = (2.0 * math.pi) / 3.0
    return 2.0 ** (-10.0 * t) * math.sin((10.0 * t - 0.75) * c4) + 1.0


def elastic_in_out(t: float) -> float:
    """Wind up and settle using Robert Penner's Elastic family."""

    if t == 0.0 or t == 1.0:
        return t
    c5 = (2.0 * math.pi) / 4.5
    if t < 0.5:
        return -(2.0 ** (20.0 * t - 10.0) * math.sin((20.0 * t - 11.125) * c5)) / 2.0
    return (2.0 ** (-20.0 * t + 10.0) * math.sin((20.0 * t - 11.125) * c5)) / 2.0 + 1.0


# easings.net orders these names as ease + direction + family. Keep the
# existing family-first API while making those familiar spellings importable.
ease_in_sine = sine_in
ease_out_sine = sine_out
ease_in_out_sine = sine_in_out
ease_in_cubic = cubic_in
ease_out_cubic = cubic_out
ease_in_out_cubic = cubic_in_out
ease_in_quint = quint_in
ease_out_quint = quint_out
ease_in_out_quint = quint_in_out
ease_in_back = back_in
ease_out_back = back_out
ease_in_out_back = back_in_out
ease_in_bounce = bounce_in
ease_out_bounce = bounce_out
ease_in_out_bounce = bounce_in_out
ease_in_elastic = elastic_in
ease_out_elastic = elastic_out
ease_in_out_elastic = elastic_in_out

_EASING_ITEMS = (
    ("linear", linear),
    ("sine_in", sine_in),
    ("sine_out", sine_out),
    ("sine_in_out", sine_in_out),
    ("smoothstep", smoothstep),
    ("smootherstep", smootherstep),
    ("cubic_in", cubic_in),
    ("cubic_out", cubic_out),
    ("cubic_in_out", cubic_in_out),
    ("quint_in", quint_in),
    ("quint_out", quint_out),
    ("quint_in_out", quint_in_out),
    ("back_in", back_in),
    ("back_out", back_out),
    ("back_in_out", back_in_out),
    ("bounce_in", bounce_in),
    ("bounce_out", bounce_out),
    ("bounce_in_out", bounce_in_out),
    ("elastic_in", elastic_in),
    ("elastic_out", elastic_out),
    ("elastic_in_out", elastic_in_out),
)

EASINGS: Mapping[str, EasingFunction] = MappingProxyType(dict(_EASING_ITEMS))


@dataclass(frozen=True, slots=True)
class Preset:
    """Metadata and callable behavior for a built-in easing."""

    key: str
    name: str
    subtitle: str
    function: EasingFunction
    formula: str
    sample_count: int
    editable: bool = True
    can_overshoot: bool = False

    def __call__(self, t: float) -> float:
        return self.function(t)


_PRESET_ITEMS = (
    Preset("linear", "Linear", "constant speed", linear, "y = t", 2),
    Preset(
        "sine_in_out",
        "Sine / Cosine",
        "exact circle projection",
        sine_in_out,
        "y = (1 - cos(pi*t)) / 2",
        9,
        editable=False,
    ),
    Preset(
        "smoothstep",
        "Smoothstep",
        "zero end velocity",
        smoothstep,
        "y = t^2 * (3 - 2*t)",
        7,
    ),
    Preset(
        "smootherstep",
        "Smootherstep",
        "zero end acceleration too",
        smootherstep,
        "y = 6*t^5 - 15*t^4 + 10*t^3",
        7,
    ),
    Preset(
        "cubic_in_out",
        "Cubic",
        "stronger S-curve",
        cubic_in_out,
        "y = 4*t^3 if t < 0.5 else 1 - (-2*t + 2)^3 / 2",
        9,
    ),
    Preset(
        "quint_in_out",
        "Quintic",
        "very soft endpoints",
        quint_in_out,
        "y = 16*t^5 if t < 0.5 else 1 - (-2*t + 2)^5 / 2",
        9,
    ),
    Preset(
        "back_in_out",
        "Back",
        "anticipation / overshoot",
        back_in_out,
        "easeInOutBack(t), c1=1.70158, c2=c1*1.525",
        11,
        can_overshoot=True,
    ),
    Preset(
        "bounce_in_out",
        "Bounce",
        "impact / landing",
        bounce_in_out,
        "easeInOutBounce(t), derived from piecewise quadratic bounceOut",
        21,
    ),
    Preset(
        "elastic_in_out",
        "Elastic",
        "springy / juicy",
        elastic_in_out,
        "easeInOutElastic(t), c5=(2*pi)/4.5",
        25,
        can_overshoot=True,
    ),
)

PRESETS: Mapping[str, Preset] = MappingProxyType({preset.key: preset for preset in _PRESET_ITEMS})

_ALIASES = {
    "sine": "sine_in_out",
    "sine_cosine": "sine_in_out",
    "ease_in_sine": "sine_in",
    "ease_out_sine": "sine_out",
    "ease_in_out_sine": "sine_in_out",
    "cubic": "cubic_in_out",
    "ease_in_cubic": "cubic_in",
    "ease_out_cubic": "cubic_out",
    "ease_in_out_cubic": "cubic_in_out",
    "quintic": "quint_in_out",
    "quint": "quint_in_out",
    "ease_in_quint": "quint_in",
    "ease_out_quint": "quint_out",
    "ease_in_out_quint": "quint_in_out",
    "back": "back_in_out",
    "ease_in_back": "back_in",
    "ease_out_back": "back_out",
    "ease_in_out_back": "back_in_out",
    "bounce": "bounce_in_out",
    "ease_in_bounce": "bounce_in",
    "ease_out_bounce": "bounce_out",
    "ease_in_out_bounce": "bounce_in_out",
    "elastic": "elastic_in_out",
    "ease_in_elastic": "elastic_in",
    "ease_out_elastic": "elastic_out",
    "ease_in_out_elastic": "elastic_in_out",
}


def _normalize_name(name: str) -> str:
    normalized = "_".join(name.strip().lower().replace("/", " ").replace("-", " ").split())
    return _ALIASES.get(normalized, normalized)


def resolve_easing(easing: str | EasingFunction | Preset) -> EasingFunction:
    """Resolve a built-in easing name or return a callable unchanged."""

    if isinstance(easing, str):
        key = _normalize_name(easing)
        try:
            return EASINGS[key]
        except KeyError as exc:
            names = ", ".join(EASINGS)
            raise KeyError(f"unknown easing {easing!r}; choose one of: {names}") from exc
    if isinstance(easing, Preset):
        return easing.function
    if callable(easing):
        return easing
    raise TypeError("easing must be a preset name or callable")


def evaluate(
    easing: str | EasingFunction | Preset,
    t: float,
    *,
    clamp_input: bool = True,
) -> float:
    """Evaluate an easing at *t*, clamping normalized time by default."""

    normalized = clamp01(float(t)) if clamp_input else float(t)
    return float(resolve_easing(easing)(normalized))


def interpolate(
    start: Any,
    end: Any,
    t: float,
    easing: str | EasingFunction | Preset = "linear",
    *,
    clamp_input: bool = True,
) -> Any:
    """Interpolate values that support subtraction, scalar multiply, and addition.

    Scalars and ``pygame.Vector2`` values both satisfy this small protocol. The
    result can leave the start/end range when an overshooting easing is used.
    """

    amount = evaluate(easing, t, clamp_input=clamp_input)
    return start + (end - start) * amount


def ping_pong(seconds: float, *, leg_seconds: float = 1.0, speed: float = 1.0) -> float:
    """Return a repeating normalized ``0 -> 1 -> 0`` phase."""

    if leg_seconds <= 0.0:
        raise ValueError("leg_seconds must be greater than zero")
    if speed < 0.0:
        raise ValueError("speed must not be negative")
    phase = (float(seconds) * speed / leg_seconds) % 2.0
    return phase if phase <= 1.0 else 2.0 - phase


@dataclass(frozen=True, slots=True)
class CubicSegment:
    """Portable cubic coefficients for one normalized curve segment."""

    x0: float
    x1: float
    a: float
    b: float
    c: float
    d: float

    def evaluate(self, t: float) -> float:
        u = (t - self.x0) / (self.x1 - self.x0)
        return ((self.a * u + self.b) * u + self.c) * u + self.d

    def to_dict(self) -> dict[str, float]:
        return {
            "x0": self.x0,
            "x1": self.x1,
            "a": self.a,
            "b": self.b,
            "c": self.c,
            "d": self.d,
        }


@dataclass(frozen=True, slots=True, init=False)
class Curve:
    """A validated piecewise cubic Hermite easing curve.

    Two-point curves use their chord slope, preserving a truly linear curve.
    Curves with three or more points use zero endpoint slopes and centered
    internal slopes, matching the standalone designer.
    """

    points: tuple[Point, ...]

    def __init__(self, points: Iterable[Sequence[float]]) -> None:
        try:
            normalized = tuple((float(point[0]), float(point[1])) for point in points)
        except (IndexError, TypeError, ValueError) as exc:
            raise InvalidCurveError("each control point must contain two numbers") from exc
        self._validate(normalized)
        object.__setattr__(self, "points", normalized)

    @staticmethod
    def _validate(points: tuple[Point, ...]) -> None:
        if len(points) < 2:
            raise InvalidCurveError("a curve needs at least two control points")
        if not all(math.isfinite(x) and math.isfinite(y) for x, y in points):
            raise InvalidCurveError("control points must contain finite numbers")
        if not math.isclose(points[0][0], 0.0, abs_tol=1e-12):
            raise InvalidCurveError("the first control point must start at t=0")
        if not math.isclose(points[-1][0], 1.0, abs_tol=1e-12):
            raise InvalidCurveError("the last control point must end at t=1")
        if any(not 0.0 <= x <= 1.0 for x, _ in points):
            raise InvalidCurveError("control point times must stay within [0, 1]")
        if any(right[0] <= left[0] for left, right in pairwise(points)):
            raise InvalidCurveError("control point times must be strictly increasing")

    def _slope(self, index: int) -> float:
        if len(self.points) == 2:
            (x0, y0), (x1, y1) = self.points
            return (y1 - y0) / (x1 - x0)
        if index == 0 or index == len(self.points) - 1:
            return 0.0
        xa, ya = self.points[index - 1]
        xb, yb = self.points[index + 1]
        return (yb - ya) / (xb - xa)

    @property
    def segments(self) -> tuple[CubicSegment, ...]:
        result = []
        for index, ((x0, y0), (x1, y1)) in enumerate(pairwise(self.points)):
            dx = x1 - x0
            m0 = self._slope(index)
            m1 = self._slope(index + 1)
            result.append(
                CubicSegment(
                    x0=x0,
                    x1=x1,
                    a=2.0 * y0 - 2.0 * y1 + dx * (m0 + m1),
                    b=-3.0 * y0 + 3.0 * y1 - dx * (2.0 * m0 + m1),
                    c=dx * m0,
                    d=y0,
                )
            )
        return tuple(result)

    def __call__(self, t: float) -> float:
        value = float(t)
        if value <= 0.0:
            return self.points[0][1]
        if value >= 1.0:
            return self.points[-1][1]
        for segment in self.segments:
            if value <= segment.x1:
                return segment.evaluate(value)
        return self.points[-1][1]

    def to_dict(
        self,
        *,
        name: str = "Custom easing",
        subtitle: str = "Designed in Easing Lab",
    ) -> dict[str, Any]:
        """Return a versioned, language-neutral JSON-compatible document."""

        return {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "name": name,
            "subtitle": subtitle,
            "input_domain": [0.0, 1.0],
            "output_can_overshoot": True,
            "curve_type": "piecewise_cubic_hermite",
            "formula": ("For the segment containing t: u=(t-x0)/(x1-x0); y=a*u^3+b*u^2+c*u+d"),
            "endpoint_rule": (
                "two points use the chord slope; three or more points use zero endpoint slopes"
            ),
            "internal_tangent_rule": "m_i=(y_(i+1)-y_(i-1))/(x_(i+1)-x_(i-1))",
            "control_points": [{"t": x, "value": y} for x, y in self.points],
            "segments": [segment.to_dict() for segment in self.segments],
            "provenance": {
                "classification": "observed",
                "source": "Easing Lab runtime export",
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Curve:
        """Load and validate an editable curve document."""

        _validate_document_header(payload)
        if payload.get("curve_type") != "piecewise_cubic_hermite":
            raise InvalidCurveError("document is not an editable Hermite curve")
        raw_points = payload.get("control_points")
        if not isinstance(raw_points, list):
            raise InvalidCurveError("control_points must be a list")
        try:
            points = [(point["t"], point["value"]) for point in raw_points]
        except (KeyError, TypeError) as exc:
            raise InvalidCurveError("each control point needs t and value fields") from exc
        return cls(points)


def curve_from_preset(preset: str | Preset) -> Curve:
    """Sample a built-in preset into an editable designer curve."""

    resolved = PRESETS[_normalize_name(preset)] if isinstance(preset, str) else preset
    count = resolved.sample_count
    points = [
        (index / (count - 1), resolved.function(index / (count - 1))) for index in range(count)
    ]
    return Curve(points)


def preset_document(preset: str | Preset) -> dict[str, Any]:
    """Return a versioned closed-form preset document."""

    resolved = PRESETS[_normalize_name(preset)] if isinstance(preset, str) else preset
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "name": resolved.name,
        "subtitle": resolved.subtitle,
        "input_domain": [0.0, 1.0],
        "output_can_overshoot": resolved.can_overshoot,
        "curve_type": "closed_form",
        "preset": resolved.key,
        "formula": resolved.formula,
        "provenance": {
            "classification": "derived",
            "source": "built-in Easing Lab preset",
        },
    }


def _validate_document_header(payload: Mapping[str, Any]) -> None:
    if payload.get("format") != FORMAT_NAME:
        raise InvalidCurveError(f"expected format {FORMAT_NAME!r}")
    if payload.get("version") != FORMAT_VERSION:
        raise InvalidCurveError(f"unsupported document version {payload.get('version')!r}")


def easing_from_dict(payload: Mapping[str, Any]) -> EasingFunction:
    """Load a callable from either supported Easing Lab document type."""

    _validate_document_header(payload)
    curve_type = payload.get("curve_type")
    if curve_type == "piecewise_cubic_hermite":
        return Curve.from_dict(payload)
    if curve_type == "closed_form":
        preset = payload.get("preset")
        if not isinstance(preset, str):
            raise InvalidCurveError("closed-form documents need a preset name")
        try:
            return resolve_easing(preset)
        except KeyError as exc:
            raise InvalidCurveError(str(exc)) from exc
    raise InvalidCurveError(f"unsupported curve_type {curve_type!r}")


def load_easing(path: str | Path) -> EasingFunction:
    """Read an Easing Lab JSON file and return a callable easing."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidCurveError(f"could not read easing document: {exc}") from exc
    if not isinstance(payload, dict):
        raise InvalidCurveError("easing document must contain a JSON object")
    return easing_from_dict(payload)


__all__ = [
    "EASINGS",
    "FORMAT_NAME",
    "FORMAT_VERSION",
    "PRESETS",
    "CubicSegment",
    "Curve",
    "EasingFunction",
    "InvalidCurveError",
    "Preset",
    "back_in",
    "back_in_out",
    "back_out",
    "bounce_in",
    "bounce_in_out",
    "bounce_out",
    "clamp",
    "clamp01",
    "cubic_in",
    "cubic_in_out",
    "cubic_out",
    "curve_from_preset",
    "ease_in_back",
    "ease_in_bounce",
    "ease_in_cubic",
    "ease_in_elastic",
    "ease_in_out_back",
    "ease_in_out_bounce",
    "ease_in_out_cubic",
    "ease_in_out_elastic",
    "ease_in_out_quint",
    "ease_in_out_sine",
    "ease_in_quint",
    "ease_in_sine",
    "ease_out_back",
    "ease_out_bounce",
    "ease_out_cubic",
    "ease_out_elastic",
    "ease_out_quint",
    "ease_out_sine",
    "easing_from_dict",
    "elastic_in",
    "elastic_in_out",
    "elastic_out",
    "evaluate",
    "interpolate",
    "linear",
    "load_easing",
    "ping_pong",
    "preset_document",
    "quint_in",
    "quint_in_out",
    "quint_out",
    "resolve_easing",
    "sine_in",
    "sine_in_out",
    "sine_out",
    "smootherstep",
    "smoothstep",
]
