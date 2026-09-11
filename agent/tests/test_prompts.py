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
