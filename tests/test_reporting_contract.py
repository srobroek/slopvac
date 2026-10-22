"""Keep the in-package reporting registry aligned with GitHub issue forms."""

from __future__ import annotations

import copy
import tomllib
from pathlib import Path

import pytest
import yaml
from slopvac.reporting import REPORT_CATEGORIES, REPOSITORY_SLUG, ReportCategory

ROOT = Path(__file__).resolve().parents[1]
FORM_ROOT = ROOT / ".github" / "ISSUE_TEMPLATE"


def _field_form(field):
    attributes = {"label": field.label}
    if field.render is not None:
        attributes["render"] = field.render
    if field.type == "checkboxes":
        attributes["options"] = [
            {"label": label, "required": required}
            for label, required in field.checkbox_options
        ]
    elif field.options:
        attributes["options"] = list(field.options)
    if field.multiple:
        attributes["multiple"] = True
    return {
        "type": field.type,
        "id": field.id,
        "attributes": attributes,
        "validations": (
            {} if field.type == "checkboxes" else {"required": field.required}
        ),
    }


def _registry_form(category: ReportCategory) -> dict:
    """Build one throwaway issue form with the schema declared by the registry."""
    return {
        "name": category.form_name,
        "title": category.title_prefix,
        "labels": list(category.labels),
        "body": [
            {"type": "markdown", "attributes": {"value": "reporting policy"}},
            *(_field_form(field) for field in category.fields),
        ],
    }


def _assert_form_matches(category: ReportCategory, form: dict, form_path: Path) -> None:
    assert form.get("name") == category.form_name, f"{form_path}: form name differs"
    assert form.get("title") == category.title_prefix, (
        f"{form_path}: title differs from {category.title_prefix!r}"
    )
    assert form.get("labels") == list(category.labels), f"{form_path}: labels differ"
    actual_fields = [
        item for item in form.get("body", []) if isinstance(item, dict) and "id" in item
    ]
    assert [item["id"] for item in actual_fields] == [
        field.id for field in category.fields
    ], f"{form_path}: field ids or order differ"
    for field, item in zip(category.fields, actual_fields, strict=True):
        attributes = item.get("attributes", {})
        validations = item.get("validations", {})
        assert attributes.get("label") == field.label, (form_path, field.id, "label")
        assert attributes.get("render") == field.render, (form_path, field.id, "render")
        assert item.get("type") == field.type, (form_path, field.id, "type")
        if field.type != "checkboxes":
            assert validations.get("required", False) is field.required, (
                form_path,
                field.id,
                "required",
            )
        if field.type == "checkboxes":
            assert attributes.get("options", []) == [
                {"label": label, "required": required}
                for label, required in field.checkbox_options
            ], (form_path, field.id, "checkbox options")
        else:
            assert attributes.get("options", []) == list(field.options), (
                form_path,
                field.id,
                "options",
            )
        assert attributes.get("multiple", False) is field.multiple, (
            form_path,
            field.id,
            "multiple",
        )


def test_registry_repository_slug_matches_project_urls():
    pyproject = tomllib.loads(
        (ROOT / "packages" / "slopvac-lint" / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    repository_url = pyproject["project"]["urls"]["Repository"]
    assert REPOSITORY_SLUG == repository_url.removeprefix("https://github.com/")


@pytest.mark.parametrize("category", REPORT_CATEGORIES, ids=lambda category: category.key)
def test_issue_form_matches_registry(category):
    path = FORM_ROOT / category.form_file
    assert path.is_file(), f"missing issue form named in report registry: {path}"
    form = yaml.safe_load(path.read_text(encoding="utf-8"))
    _assert_form_matches(category, form, path)


def test_issue_form_files_match_registry():
    form_files = {path.name for path in FORM_ROOT.glob("*.yml")} - {"config.yml"}
    registry_files = {category.form_file for category in REPORT_CATEGORIES}
    assert form_files == registry_files


@pytest.mark.parametrize(
    "field",
    ["options", "checkbox_options", "checkbox_required", "required", "render", "labels", "title"],
)
def test_form_comparison_rejects_contract_drift(field, tmp_path):
    category = next(item for item in REPORT_CATEGORIES if item.key == "bug")
    form = copy.deepcopy(_registry_form(category))
    fields = {
        item["id"]: item
        for item in form["body"]
        if isinstance(item, dict) and "id" in item
    }
    if field == "options":
        fields["latest"]["attributes"]["options"].append("Unexpected")
    elif field == "checkbox_options":
        fields["reporter"]["attributes"]["options"].append(
            {"label": "Unexpected", "required": False}
        )
    elif field == "checkbox_required":
        fields["duplicates"]["attributes"]["options"][0]["required"] = False
    elif field == "required":
        fields["what-happened"]["validations"]["required"] = False
    elif field == "render":
        fields["config"]["attributes"]["render"] = "markdown"
    elif field == "labels":
        form["labels"].append("unexpected")
    else:
        form["title"] += "extra"
    path = tmp_path / category.form_file
    with pytest.raises(AssertionError):
        _assert_form_matches(category, form, path)
