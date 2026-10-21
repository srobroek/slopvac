"""Keep the in-package reporting registry aligned with GitHub issue forms."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml
from slopvac.reporting import REPORT_CATEGORIES, REPOSITORY_SLUG, ReportCategory

ROOT = Path(__file__).resolve().parents[1]
FORM_ROOT = ROOT / ".github" / "ISSUE_TEMPLATE"


def _field_form(field):
    attributes = {"label": field.label}
    if field.description is not None:
        attributes["description"] = field.description
    if field.render is not None:
        attributes["render"] = field.render
    if field.options:
        attributes["options"] = list(field.options)
    if field.multiple:
        attributes["multiple"] = True
    return {
        "type": field.type,
        "id": field.id,
        "attributes": attributes,
        "validations": {"required": field.required},
    }


def _registry_form(category: ReportCategory) -> dict:
    """Build one throwaway issue form with the schema declared by the registry."""
    return {
        "name": category.form_name,
        "title": f"{category.title_prefix}<title>",
        "labels": list(category.labels),
        "body": [
            {"type": "markdown", "attributes": {"value": "reporting policy"}},
            *(_field_form(field) for field in category.fields),
        ],
    }


def _assert_form_matches(category: ReportCategory, form: dict, form_path: Path) -> None:
    assert form.get("name") == category.form_name, f"{form_path}: form name differs"
    title = form.get("title", "")
    assert title.startswith(category.title_prefix), (
        f"{form_path}: title must start with {category.title_prefix!r}"
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
        assert item.get("type") == field.type, (form_path, field.id, "type")
        assert validations.get("required", False) is field.required, (
            form_path,
            field.id,
            "required",
        )
        assert attributes.get("render") == field.render, (form_path, field.id, "render")
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


def test_registry_generated_form_proves_comparison_logic(tmp_path):
    """A temporary form from the Contract B registry exercises the YAML comparator."""
    category = next(item for item in REPORT_CATEGORIES if item.key == "bug")
    path = tmp_path / category.form_file
    path.write_text(yaml.safe_dump(_registry_form(category), sort_keys=False), encoding="utf-8")
    form = yaml.safe_load(path.read_text(encoding="utf-8"))
    _assert_form_matches(category, form, path)
