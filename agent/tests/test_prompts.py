import os
import subprocess
import sys
from pathlib import Path

from prompts import load_fewshot_prompt, load_prompt_bundle, load_system_prompt


def test_prompt_files_are_loaded_from_their_own_directory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    system = load_system_prompt()
    fewshot = load_fewshot_prompt()

    assert "# R — Role" in system
    assert "get_delivery_orders" in system
    assert "optimize_dispatch" in system
    assert "시나리오 2" in fewshot
    assert "시나리오 3" in fewshot


def test_prompt_bundle_contains_separate_system_and_fewshot_content() -> None:
    bundle = load_prompt_bundle()

    assert bundle.system == load_system_prompt()
    assert bundle.fewshot == load_fewshot_prompt()
    assert "runtime_context" in bundle.system
    assert "geocodes[input_address]" in bundle.fewshot


def test_prompts_preserve_missing_input_and_tms_result_rules() -> None:
    system = load_system_prompt()
    fewshot = load_fewshot_prompt()

    assert "추정하지 않는다" in system
    assert "TMAP TMS가 계산한다" in system
    assert "반환되지 않은 값을 추가하지 않는다" in system
    assert "ambiguous" in fewshot
    assert "not_found" in fewshot


def test_installed_wheel_loads_prompts_from_outside_repository(tmp_path: Path) -> None:
    project_dir = Path(__file__).parents[1]
    wheel_dir = tmp_path / "wheel"
    install_dir = tmp_path / "site"
    outside_dir = tmp_path / "outside"
    wheel_dir.mkdir()
    install_dir.mkdir()
    outside_dir.mkdir()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(project_dir),
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(wheel_dir.glob("badaro_agent-*.whl"))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            str(wheel),
            "--no-deps",
            "--target",
            str(install_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(install_dir)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from prompts import load_prompt_bundle; "
                "bundle = load_prompt_bundle(); "
                "assert '# R — Role' in bundle.system; "
                "assert '시나리오 2' in bundle.fewshot"
            ),
        ],
        cwd=outside_dir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
