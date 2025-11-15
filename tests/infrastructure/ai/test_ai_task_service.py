from app.infrastructure.ai.ai_task_service import AITaskService


def test_normalize_section_head_strips_leading_symbols():
    assert (
        AITaskService._normalize_section_head("🔹 МАТЕРІАЛ")
        == "МАТЕРІАЛ"
    )
    assert (
        AITaskService._normalize_section_head("— ОПИС")
        == "ОПИС"
    )


def test_normalize_section_head_handles_empty_input():
    assert AITaskService._normalize_section_head("") == ""
