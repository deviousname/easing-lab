import json
import math

import pytest

from easing_lab import (
    PRESETS,
    Curve,
    InvalidCurveError,
    curve_from_preset,
    easing_from_dict,
    evaluate,
    interpolate,
    load_easing,
    ping_pong,
    preset_document,
    resolve_easing,
)


@pytest.mark.parametrize("preset", PRESETS.values(), ids=lambda preset: preset.key)
def test_every_preset_has_normalized_endpoints(preset):
    assert preset(0.0) == pytest.approx(0.0, abs=1e-12)
    assert preset(1.0) == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize(
    ("name", "t", "expected"),
    [
        ("linear", 0.25, 0.25),
        ("sine_in_out", 0.5, 0.5),
        ("smoothstep", 0.25, 0.15625),
        ("smootherstep", 0.25, 0.103515625),
        ("cubic_in_out", 0.25, 0.0625),
        ("quint_in_out", 0.25, 0.015625),
        ("bounce_in_out", 0.25, 0.1171875),
        ("elastic_in_out", 0.5, 0.5),
    ],
)
def test_representative_preset_values_use_hand_derived_literals(name, t, expected):
    # Expected values are fixed literals, intentionally independent of the
    # implementation constants and code paths.
    assert evaluate(name, t) == pytest.approx(expected, abs=1e-12)


def test_back_easing_anticipates_and_overshoots_symmetrically():
    back = resolve_easing("back")
    assert back(0.25) < 0.0
    assert back(0.25) + back(0.75) == pytest.approx(1.0, abs=1e-12)


def test_evaluate_clamps_by_default_but_can_be_unclamped():
    assert evaluate("linear", 1.5) == 1.0
    assert evaluate("linear", 1.5, clamp_input=False) == 1.5


def test_interpolate_supports_scalar_values_and_overshoot():
    assert interpolate(10.0, 30.0, 0.25, "linear") == 15.0
    assert interpolate(10.0, 30.0, 0.25, "back") < 10.0


def test_resolve_easing_accepts_documented_aliases():
    assert resolve_easing("Sine / Cosine")(0.5) == pytest.approx(0.5)
    assert resolve_easing("quintic")(0.5) == pytest.approx(0.5)
    with pytest.raises(KeyError, match="unknown easing"):
        resolve_easing("not-real")


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (1.5, 0.5), (2.0, 0.0)],
)
def test_ping_pong_phase(seconds, expected):
    assert ping_pong(seconds) == expected


def test_ping_pong_rejects_invalid_timing():
    with pytest.raises(ValueError, match="leg_seconds"):
        ping_pong(1.0, leg_seconds=0.0)
    with pytest.raises(ValueError, match="speed"):
        ping_pong(1.0, speed=-1.0)


def test_two_point_curve_is_truly_linear_regression():
    # The proof of concept pinned both endpoint slopes to zero, so its card
    # labeled Linear actually evaluated as smoothstep. A chord slope fixes it.
    curve = Curve([(0.0, 0.0), (1.0, 1.0)])
    assert curve(0.25) == 0.25
    assert curve(0.75) == 0.75
    assert curve.segments[0].to_dict() == {
        "x0": 0.0,
        "x1": 1.0,
        "a": 0.0,
        "b": 0.0,
        "c": 1.0,
        "d": 0.0,
    }


def test_three_point_curve_uses_zero_end_and_centered_internal_slopes():
    curve = Curve([(0.0, 0.0), (0.5, 1.0), (1.0, 1.0)])
    # First segment coefficients are a=-1.5, b=2.5, c=0, d=0.
    # At t=.25, u=.5, so y=-1.5*(.5^3)+2.5*(.5^2)=.4375.
    assert curve(0.25) == pytest.approx(0.4375, abs=1e-12)
    assert curve(0.5) == 1.0


@pytest.mark.parametrize(
    "points",
    [
        [],
        [(0.0, 0.0)],
        [(0.1, 0.0), (1.0, 1.0)],
        [(0.0, 0.0), (0.9, 1.0)],
        [(0.0, 0.0), (0.5, 0.3), (0.5, 0.7), (1.0, 1.0)],
        [(0.0, 0.0), (math.nan, 0.5), (1.0, 1.0)],
    ],
)
def test_curve_validation_rejects_invalid_points(points):
    with pytest.raises(InvalidCurveError):
        Curve(points)


def test_custom_curve_json_round_trip_uses_control_points_as_source_of_truth(tmp_path):
    original = Curve([(0.0, 0.0), (0.4, -0.1), (0.8, 1.2), (1.0, 1.0)])
    payload = original.to_dict(name="Juicy button", subtitle="Test curve")
    payload["segments"][0]["a"] = 9999.0
    path = tmp_path / "curve.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_easing(path)
    assert isinstance(loaded, Curve)
    assert loaded.points == original.points
    assert loaded(0.2) == pytest.approx(original(0.2), abs=1e-12)


def test_closed_form_document_loads_the_named_preset():
    payload = preset_document("sine_in_out")
    loaded = easing_from_dict(payload)
    assert loaded(0.5) == pytest.approx(0.5, abs=1e-12)


def test_curve_from_preset_preserves_linear_samples():
    curve = curve_from_preset("linear")
    assert curve.points == ((0.0, 0.0), (1.0, 1.0))
    assert curve(0.125) == 0.125
