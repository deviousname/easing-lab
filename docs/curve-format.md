# Easing Lab JSON format, version 1

> **Observed:** This document describes the format emitted and accepted by Easing Lab
> 0.1.0. **Derived:** The cubic polynomial representation follows ordinary Hermite
> interpolation algebra. **Inferred:** Consumers in other languages should interoperate if
> they implement the rules below; no non-Python consumer has been tested yet.

Every document is a UTF-8 JSON object with:

```json
{
  "format": "easing-lab",
  "version": 1,
  "curve_type": "piecewise_cubic_hermite"
}
```

`format` and `version` are compatibility gates. Unknown versions are rejected instead of
being guessed.

## Editable Hermite curves

`control_points` is the source of truth:

```json
{
  "control_points": [
    {"t": 0.0, "value": 0.0},
    {"t": 0.5, "value": 0.8},
    {"t": 1.0, "value": 1.0}
  ]
}
```

The following invariants are enforced:

- `t` values are finite, inside `0..1`, and strictly increasing.
- The first `t` is `0` and the last `t` is `1`.
- At least two points are present.
- Output values are finite but may overshoot below `0` or above `1`.

For two points, both tangents equal the chord slope. This makes `(0,0) -> (1,1)` exactly
linear. With three or more points, endpoint tangents are zero and each internal tangent is:

```text
m_i = (y_(i+1) - y_(i-1)) / (x_(i+1) - x_(i-1))
```

For the segment containing `t`, compute:

```text
u = (t - x0) / (x1 - x0)
y = ((a*u + b)*u + c)*u + d
```

The exported `segments` array duplicates the derived coefficients for consumers that want
them. Easing Lab deliberately recalculates them from `control_points` when loading, so
edited or stale duplicate coefficients cannot change the curve.

## Closed-form presets

Locked presets use:

```json
{
  "format": "easing-lab",
  "version": 1,
  "curve_type": "closed_form",
  "preset": "sine_in_out"
}
```

Version 1 loaders accept closed-form documents only when `preset` matches a built-in stable
key. The human-readable `formula` field is documentation, not executable input.

## Python loading

```python
from easing_lab import Curve, easing_from_dict, load_easing

ease = load_easing("curve.json")
value = ease(0.5)
```

`Curve.from_dict()` accepts editable documents specifically. `easing_from_dict()` and
`load_easing()` accept either editable or closed-form documents.
