"""Document genres: the one place that names them and maps each to a profile.

A genre is a document's purpose class. `slopvac prime` and its topics read this
table to tell an agent which `--profile` to lint with, and `slopvac rules
--genre` pairs it with each category's `recommended_for` to pick the checklist
categories.
Before this module the same mapping was typed into the steering prose and into a
helper in `profiles.py` that nothing called, so the three could disagree.

`model.Genre` stays a `Literal` because pydantic validates `recommended_for`
against it and a type checker needs the values spelled out; a test holds it
equal to the names here.
"""

from __future__ import annotations

from typing import NamedTuple

from .enums import Profile


class DocumentGenre(NamedTuple):
    name: str
    surfaces: str
    profile: Profile
    purpose: str


GENRES: tuple[DocumentGenre, ...] = (
    DocumentGenre(
        "consumer",
        "README, docs, guides",
        Profile.NORMAL,
        "Shipped behavior and reader use",
    ),
    DocumentGenre(
        "reference",
        "API docs, runbooks, procedures, safety text, agent guidance",
        Profile.STRICT,
        "Exact operations and dated facts for use or verification",
    ),
    DocumentGenre(
        "change-comms",
        "PR or MR descriptions, commits, release notes, migration guides",
        Profile.NORMAL,
        "Change, rationale, verification",
    ),
    DocumentGenre(
        "internal",
        "Specifications, decision records, contributor docs",
        Profile.NORMAL,
        "Requirements and decision rationale",
    ),
    DocumentGenre(
        "informal",
        "Issue comments, discussions, blogs, drafts",
        Profile.RELAXED,
        "Immediate context",
    ),
)

# How to choose when a document's surface fits two rows above.
ROUTING = (
    "When two genres fit, choose by purpose. Migration guides are `change-comms`. "
    "Decision records and specifications are `internal`. Agent guidance and "
    "procedures are `reference`."
)
