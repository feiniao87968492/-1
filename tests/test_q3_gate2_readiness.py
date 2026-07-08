from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_q3_smooth_atmosphere_is_hydrostatic_and_continuous() -> None:
    sys.path.insert(0, str(ROOT / "questions" / "q3" / "scripts"))
    from smooth_atmosphere import atmosphere, hydrostatic_residual

    for height_m in [10950.0, 11000.0, 11050.0]:
        temperature_k, density_kgm3, sound_speed_mps, pressure_pa = atmosphere(height_m)
        assert temperature_k > 0.0
        assert density_kgm3 > 0.0
        assert sound_speed_mps > 0.0
        assert pressure_pa > 0.0
        assert hydrostatic_residual(height_m) < 1.0e-6

    dh = 0.01
    t_slope_left = (atmosphere(11000.0)[0] - atmosphere(11000.0 - dh)[0]) / dh
    t_slope_right = (atmosphere(11000.0 + dh)[0] - atmosphere(11000.0)[0]) / dh
    assert abs(t_slope_left - t_slope_right) < 1.0e-5


def test_q3_gate2_config_and_manifest_are_explicit() -> None:
    config = yaml.safe_load((ROOT / "configs/default.yaml").read_text(encoding="utf-8"))
    gate = config["q3_optimal_control"]["feasibility_gate"]
    assert gate["slack_smoothing_tolerance_kg"] < gate["pass_criteria"]["terminal_mass_shortfall_kg"]
    assert gate["pass_criteria"]["constraint_violation_scale"] == "nondimensional"
    assert gate["atmosphere_smoothing_state"] == "temperature_only_hydrostatic_pressure"
    assert gate["collocation_transcription"] == "trapezoidal"
    assert gate["midpoint_constraint_check"] == "linear_midpoint_plus_post_reconstruction"
    assert gate["lexicographic_second_stage_mass_policy"] == "enforce_terminal_mass_with_numeric_tolerance"
    assert set(gate["reintegration_diagnostics"]) == {
        "reintegration_state_error_inf",
        "reintegration_terminal_mass_error_kg",
        "reintegration_terminal_height_error_m",
        "reintegration_terminal_speed_error_mps",
    }

    manifest = yaml.safe_load((ROOT / "questions/q3/manifest.yaml").read_text(encoding="utf-8"))
    assert (
        manifest["entrypoints"]["feasibility_collocation_no_wind"]
        == "questions/q3/scripts/solve_feasibility_collocation_no_wind.py"
    )
    assert "collocation_feasibility" in manifest["quality_gates"]
    assert manifest["quality_gates"]["collocation_feasibility"] in {"partial", "passed"}
    assert "feasibility_collocation_summary" in manifest["outputs"]
    assert "feasibility_collocation_mesh_convergence" in manifest["outputs"]
    assert "feasibility_collocation_reintegration_tolerance" in manifest["outputs"]
    assert "feasibility_collocation_continuous_audit" in manifest["outputs"]
    assert "hmax_sensitivity" not in manifest["outputs"]
    assert "hmax_sensitivity" not in manifest["quality_gates"]
    assert "legacy_warm_start_hmax_diagnostic" in manifest["outputs"]
    assert "optimized_hmax_sensitivity" in manifest["outputs"]
    assert "optimized_hmax_sensitivity" in manifest["quality_gates"]


def test_q3_collocation_gate_dry_run_exports_readiness_tables() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "questions/q3/scripts/solve_feasibility_collocation_no_wind.py",
            "--config",
            "configs/default.yaml",
            "--nodes",
            "21",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    summary_path = ROOT / "questions/q3/artifacts/tables/no_wind_collocation_gate.csv"
    trajectory_path = ROOT / "questions/q3/artifacts/tables/no_wind_collocation_trajectory.csv"
    sensitivity_path = ROOT / "questions/q3/artifacts/tables/no_wind_hmax_sensitivity.csv"
    renamed_sensitivity_path = ROOT / "questions/q3/artifacts/tables/warm_start_hmax_diagnostic.csv"
    atmosphere_path = ROOT / "questions/q3/artifacts/tables/atmosphere_smoothing_diagnostics.csv"
    projection_path = ROOT / "questions/q3/artifacts/tables/gate1_to_collocation_projection_audit.csv"
    coupling_path = ROOT / "questions/q3/artifacts/tables/atmosphere_coupling_diagnostics.csv"
    assert summary_path.exists()
    assert trajectory_path.exists()
    assert sensitivity_path.exists()
    assert renamed_sensitivity_path.exists()
    assert atmosphere_path.exists()
    assert projection_path.exists()
    assert coupling_path.exists()

    summary = pd.read_csv(summary_path)
    row = summary.iloc[0]
    assert row["method"] == "range_domain_collocation_readiness_dry_run"
    assert row["solver_status"] == "dry_run_not_optimized"
    assert row["atmosphere_model"] == "C1_temperature_hydrostatic_pressure"
    assert row["max_scaled_constraint_violation"] >= 0.0
    assert row["max_midpoint_height_violation_m"] >= 0.0

    sensitivity = pd.read_csv(sensitivity_path)
    assert set(sensitivity["h_max_m"]) == {10950.0, 11500.0, 12000.0, 12500.0}
    renamed_sensitivity = pd.read_csv(renamed_sensitivity_path)
    assert set(renamed_sensitivity["h_max_m"]) == {10950.0, 11500.0, 12000.0, 12500.0}
    assert set(renamed_sensitivity["status"]) == {"warm_start_only_not_optimized"}

    atmosphere = pd.read_csv(atmosphere_path)
    metrics = set(atmosphere["metric"])
    assert "hydrostatic_residual_max" in metrics
    assert "hydrostatic_residual_numerical_max" in metrics
    assert "hydrostatic_residual_numerical_rms" in metrics
    assert "hydrostatic_residual_numerical_max_height_m" in metrics
    assert "hydrostatic_residual_numerical_step_0p1m_max" in metrics
    assert "hydrostatic_residual_numerical_step_0p5m_max" in metrics
    assert "hydrostatic_residual_numerical_step_1p0m_max" in metrics
    assert "hydrostatic_residual_numerical_step_2p0m_max" in metrics
    assert "hydrostatic_residual_numerical_step_5p0m_max" in metrics
    assert "temperature_derivative_jump_11000_m_kpm" in metrics
    assert "min_temperature_k" in metrics
    assert atmosphere.loc[atmosphere["metric"] == "hydrostatic_residual_max", "value"].iloc[0] < 1.0e-6
    assert atmosphere.loc[atmosphere["metric"] == "hydrostatic_residual_numerical_max", "value"].iloc[0] < 1.0e-3
    assert atmosphere.loc[atmosphere["metric"] == "hydrostatic_residual_numerical_step_0p5m_max", "unit"].iloc[0] == "1"
    assert atmosphere.loc[atmosphere["metric"] == "min_temperature_k", "value"].iloc[0] > 0.0

    projection = pd.read_csv(projection_path)
    assert set(projection["scenario"]) == {
        "A_gate1_original",
        "B_gate1_interpolated_gate2_grid_original_atmosphere",
        "C_gate1_interpolated_gate2_grid_c1_atmosphere",
    }
    assert "terminal_mass_kg" in projection.columns
    assert "mass_difference_from_previous_kg" in projection.columns

    coupling = pd.read_csv(coupling_path)
    coupling_row = coupling.iloc[0]
    assert coupling_row["height_m"] == 11000.0
    assert abs(coupling_row["density_delta_c1_minus_layer_kgm3"]) > 0.0
    assert abs(coupling_row["drag_delta_c1_minus_layer_n"]) > 0.0
    assert abs(coupling_row["dV_dx_delta_c1_minus_layer_per_m"]) > 0.0
    assert abs(coupling_row["dm_dx_delta_c1_minus_layer_kgpm"]) < 1.0e-15
    assert abs(coupling_row["required_thrust_delta_c1_minus_layer_n"]) > 0.0
    assert abs(coupling_row["required_thrust_dm_dx_delta_c1_minus_layer_kgpm"]) > 0.0


def test_q3_collocation_gate_non_dry_run_exports_formal_gate_diagnostics() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "questions/q3/scripts/solve_feasibility_collocation_no_wind.py",
            "--config",
            "configs/default.yaml",
            "--nodes",
            "11",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    summary_path = ROOT / "questions/q3/artifacts/tables/no_wind_collocation_formal_gate.csv"
    sensitivity_path = ROOT / "questions/q3/artifacts/tables/optimized_hmax_sensitivity.csv"
    summary = pd.read_csv(summary_path)
    row = summary.iloc[0]
    assert row["method"] == "range_domain_collocation_feasibility_gate"
    assert row["solver_status"] != "dry_run_not_optimized"
    assert row["lexicographic_stage"] == "stage1_minimize_terminal_mass_slack"
    assert row["mass_constraint_policy"] == "m_f_plus_s_ge_62000_s_ge_0"
    assert row["control_reconstruction"] == "piecewise_linear_node_controls"
    for column in [
        "terminal_mass_slack_kg",
        "scaled_collocation_defect_inf",
        "reintegration_state_error_inf",
        "reintegration_terminal_mass_kg",
        "reintegration_terminal_mass_signed_error_kg",
        "reintegration_terminal_mass_error_kg",
        "reintegration_terminal_mass_shortfall_kg",
        "reintegration_terminal_height_signed_error_m",
        "reintegration_terminal_height_error_m",
        "reintegration_terminal_speed_signed_error_mps",
        "reintegration_terminal_speed_error_mps",
        "reintegration_max_scaled_constraint_violation",
        "max_reconstruction_height_violation_m",
    ]:
        assert column in summary.columns
        assert pd.notna(row[column])
    if (
        row["terminal_mass_slack_kg"] <= 0.05
        and row["scaled_collocation_defect_inf"] <= 1.0e-6
        and row["max_scaled_constraint_violation"] <= 1.0e-6
        and row["reintegration_terminal_speed_error_mps"] > 1.0e-3
    ):
        assert row["solver_status"] == "discrete_feasible_reintegration_failed"

    sensitivity = pd.read_csv(sensitivity_path)
    assert set(sensitivity["h_max_m"]) == {10950.0, 11500.0, 12000.0, 12500.0}
    assert "terminal_mass_slack_kg" in sensitivity.columns
    assert "reintegration_terminal_mass_shortfall_kg" in sensitivity.columns
    assert "reintegration_terminal_speed_error_mps" in sensitivity.columns
    assert "active_hmax_fraction" in sensitivity.columns
    assert "gate_status" in sensitivity.columns
    assert set(sensitivity["gate_status"]).issubset(
        {
            "gate2_feasible",
            "needs_relaxation",
            "discrete_feasible_reintegration_failed",
            "optimization_failed",
        }
    )


def test_q3_collocation_mesh_study_exports_reintegration_convergence_diagnostics() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "questions/q3/scripts/solve_feasibility_collocation_no_wind.py",
            "--config",
            "configs/default.yaml",
            "--nodes",
            "7",
            "--mesh-study-nodes",
            "7,9",
            "--skip-hmax-sensitivity",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    mesh_path = ROOT / "questions/q3/artifacts/tables/no_wind_collocation_mesh_convergence.csv"
    assert mesh_path.exists()

    mesh = pd.read_csv(mesh_path)
    assert mesh["nodes"].tolist() == [7, 9]
    for column in [
        "h_max_m",
        "terminal_mass_slack_kg",
        "scaled_collocation_defect_inf",
        "max_scaled_constraint_violation",
        "reintegration_terminal_mass_error_kg",
        "reintegration_terminal_speed_error_mps",
        "mass_error_ratio_from_previous",
        "speed_error_ratio_from_previous",
        "max_thrust_step_n",
        "max_gamma_step_rad",
        "total_variation_thrust_n",
        "total_variation_gamma_rad",
        "max_node_speed_signed_error_mps",
        "terminal_speed_signed_error_mps",
        "gate_status",
    ]:
        assert column in mesh.columns
    assert pd.isna(mesh.loc[0, "mass_error_ratio_from_previous"])
    assert pd.isna(mesh.loc[0, "speed_error_ratio_from_previous"])
    assert set(mesh["gate_status"]).issubset(
        {
            "gate2_feasible",
            "needs_relaxation",
            "discrete_feasible_reintegration_failed",
            "optimization_failed",
        }
    )


def test_q3_collocation_gate_exports_ode_tolerance_and_continuous_audit_tables() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "questions/q3/scripts/solve_feasibility_collocation_no_wind.py",
            "--config",
            "configs/default.yaml",
            "--nodes",
            "7",
            "--skip-hmax-sensitivity",
            "--ode-rtols",
            "1e-8,1e-10",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    tolerance_path = ROOT / "questions/q3/artifacts/tables/no_wind_collocation_reintegration_tolerance.csv"
    audit_path = ROOT / "questions/q3/artifacts/tables/no_wind_collocation_continuous_audit.csv"
    assert tolerance_path.exists()
    assert audit_path.exists()

    tolerance = pd.read_csv(tolerance_path)
    assert tolerance["rtol"].tolist() == [1.0e-8, 1.0e-10]
    for column in [
        "nodes",
        "h_max_m",
        "rtol",
        "atol_height_m",
        "atol_speed_mps",
        "atol_mass_kg",
        "atol_time_s",
        "terminal_mass_kg",
        "terminal_mass_signed_error_kg",
        "terminal_speed_signed_error_mps",
        "terminal_height_signed_error_m",
        "terminal_speed_delta_from_previous_mps",
        "terminal_mass_delta_from_previous_kg",
        "success",
    ]:
        assert column in tolerance.columns
    assert pd.isna(tolerance.loc[0, "terminal_speed_delta_from_previous_mps"])
    assert pd.notna(tolerance.loc[1, "terminal_speed_delta_from_previous_mps"])

    audit = pd.read_csv(audit_path)
    assert audit["rtol"].tolist() == [1.0e-8, 1.0e-10]
    for column in [
        "nodes",
        "h_max_m",
        "rtol",
        "max_height_error_m",
        "max_speed_error_mps",
        "max_mass_error_kg",
        "max_time_error_s",
        "max_scaled_state_error",
        "max_continuous_scaled_constraint_violation",
        "max_height_violation_m",
        "max_speed_violation_mps",
        "max_mach_violation",
        "max_thrust_violation_n",
        "max_gamma_violation_rad",
        "success",
    ]:
        assert column in audit.columns
    assert (audit["max_continuous_scaled_constraint_violation"] >= 0.0).all()


def test_q3_final_no_wind_optimization_exports_results_and_validation_tables() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "questions/q3/scripts/solve_feasibility_collocation_no_wind.py",
            "--config",
            "configs/default.yaml",
            "--final-fuel",
            "--final-solver",
            "slsqp",
            "--nodes",
            "9",
            "--continuation-nodes",
            "7,9",
            "--initial-guess",
            "gate2",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    results_path = ROOT / "questions/q3/artifacts/tables/no_wind_final_optimal_results.csv"
    validation_path = ROOT / "questions/q3/artifacts/tables/no_wind_final_optimal_validation.csv"
    trajectory_path = ROOT / "questions/q3/artifacts/tables/no_wind_final_optimal_trajectory.csv"
    assert results_path.exists()
    assert validation_path.exists()
    assert trajectory_path.exists()

    results = pd.read_csv(results_path)
    row = results.iloc[0]
    assert row["artifact_id"] == "q3-T07"
    assert row["method"] == "range_domain_collocation_final_fuel_optimization"
    assert row["objective"] == "min_m0_minus_mf"
    assert row["slack_policy"] == "s_fixed_0"
    assert row["mass_constraint_policy"] == "m_f_ge_62000_s_fixed_0"
    assert row["continuation_nodes"] == "7->9"
    assert row["final_nodes"] == 9
    assert row["fuel_used_kg"] > 0.0

    validation = pd.read_csv(validation_path)
    vrow = validation.iloc[0]
    assert vrow["artifact_id"] == "q3-T08"
    for column in [
        "reintegration_terminal_speed_error_mps",
        "reintegration_terminal_height_error_m",
        "fuel_identity_residual_kg",
        "max_continuous_scaled_constraint_violation",
        "objective_grid_abs_delta_kg",
        "objective_grid_relative_delta",
        "multi_initial_objective_range_kg",
        "near_zero_thrust_fraction",
        "tf_over_t_base",
        "time_limit_1p05_feasible",
        "time_limit_1p10_feasible",
        "optimizer_success",
        "validation_status",
    ]:
        assert column in validation.columns
        assert pd.notna(vrow[column])

    trajectory = pd.read_csv(trajectory_path)
    assert len(trajectory) == 9
    assert "scaled_constraint_violation" in trajectory.columns
