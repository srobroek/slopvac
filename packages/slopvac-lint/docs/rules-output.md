# `slopvac rules` output

`slopvac rules` prints the loaded rule catalogue in three formats:

| `--format` | Reader | Content |
| --- | --- | --- |
| `text` (default) | a person | A table with one row per rule: id, kind, tier, severity, and source |
| `json` | a tool | Every field of every selected rule, plus the categories |
| `md` | an agent | One Markdown block per selected rule, grouped by category |

The sections below cover `json` and `md`. Both formats read the same catalogue
as `slopvac lint`. That catalogue includes the house rules from each
`--rules-dir` and the spelling rule generated for the configured locale.

## Selecting rules

| Option | Effect |
| --- | --- |
| `--kind <kind>` | Keeps the rules of one kind. `judgement` keeps the rules that lint never reports. |
| `--category <id>` | Keeps the rules of the named categories. Repeat it for more categories. |
| `--genre <genre>` | Keeps the rules whose category lists the genre in `recommended_for`. |
| `--profile <profile>` | Sets the profile for `tier` and `effective_severity`. Default: `normal`. |
| `--include-excluded` | Keeps, in `md` output, the rules that `--profile` excludes. |
| `--config <file>` | Resolves `effective_severity` with the settings of that config. |
| `--rules-dir <dir>` | Adds a directory of house rules. Repeat it for more directories. |

A rule appears only when it passes each filter that you give. For example,
`--genre consumer --category orwell` keeps the `orwell` rules, because
`orwell` lists `consumer`. `--genre reference --category orwell` keeps no rule.

`slopvac prime write` and `slopvac prime review` print this command for the
genre and profile of a document:

```sh
slopvac rules --kind judgement --genre <genre> --profile <profile> --format md
```

## JSON

The output is one object. `--genre`, `--kind`, and `--category` select the
`rules` entries; `categories` always lists every loaded category.

| Key | Type | Meaning |
| --- | --- | --- |
| `profile` | string | The profile that `tier` and `effective_severity` use. |
| `categories` | array of objects | Every loaded category, in load order. |
| `rules` | array of objects | The selected rules, in catalogue order. |

### Categories

| Key | Type | Meaning |
| --- | --- | --- |
| `categories[].id` | string | The category id. A rule id starts with it. |
| `categories[].title` | string | The category title. |
| `categories[].description` | string | What the category checks. |
| `categories[].weight` | number | The weight of the category in the score. With `0`, the findings stay in the report and leave the score and count gates. |
| `categories[].recommended_for` | array of strings | The genres that the category suits. `--genre` reads this list. It is empty when the category suits no genre. |

### Rules

Each rule object holds every field of the rule model, plus `rule_id`, `tier`,
and `effective_severity`. A field without a value is `null`, or an empty
array or object, as the type column says.

| Key | Type | Meaning |
| --- | --- | --- |
| `rules[].rule_id` | string | The qualified id, `<category>.<id>`. Lint reports, directives, and `slopvac explain` use it. |
| `rules[].id` | string | The id inside the category. |
| `rules[].category` | string | The id of the owning category. |
| `rules[].name` | string | A short imperative label. |
| `rules[].kind` | string | The checker: `tokens`, `pattern`, `substitution`, `vocabulary`, `metric`, `structure`, or `judgement`. |
| `rules[].scope` | string | The unit that the rule reads: `prose`, `heading`, `sentence`, `paragraph`, `document`, or `raw`. |
| `rules[].text_type` | string | The text that the rule applies to: `any`, `procedural`, `descriptive`, or `safety`. |
| `rules[].severity` | string | The shipped level: `suggestion`, `warning`, or `error`. A judgement rule always ships as `suggestion`. |
| `rules[].effective_severity` | string | The level that lint reports at `profile`, after the profile and the `--config` settings. It is `off` when the rule does not run there. A judgement rule keeps its shipped level. |
| `rules[].tier` | string | The tier at `profile`: `enforced`, `advisory`, or `excluded`. |
| `rules[].tiers` | object | The tier at each profile, keyed by profile name. A profile that the object omits gives `excluded`. |
| `rules[].message` | string | The finding message. `{match}` and `{replacement}` are filled for each finding. |
| `rules[].fix` | string or null | The rewrite operation. It is `null` when the rule gives none. |
| `rules[].judgement_question` | string or null | The question that a reviewer answers. It is set for each judgement rule and `null` for checked rules. |
| `rules[].examples` | array of objects | Worked examples. It is empty when the rule has none. |
| `rules[].examples[].bad` | string | Text that the rule judges. Lint checks that a pattern rule matches it. |
| `rules[].examples[].good` | string or null | The rewrite. It is `null` when the example gives none, and an empty string when the fix deletes the text. |
| `rules[].examples[].note` | string or null | Why the example passes or fails. It is `null` when absent. |
| `rules[].exceptions` | array of strings | The reasons that an allow directive can cite. It is empty when the rule takes no allow directive, as for each judgement rule. |
| `rules[].allowlist` | array of strings | Literal text that never matches. It is empty for most rules. |
| `rules[].provenance` | object | Where the rule comes from. |
| `rules[].provenance.source` | string | The origin, such as `ASD-STE100` or `Orwell 1946`. |
| `rules[].provenance.ste_ref` | string or null | The ASD-STE100 issue and rule number, such as `9:1.2`. It is `null` for other sources. |
| `rules[].provenance.orwell_ref` | string or null | The Orwell rule id, such as `stale-figure`. It is `null` for other sources. |
| `rules[].provenance.url` | string or null | A link to the source. It is `null` when the source has no link. |
| `rules[].provenance.note` | string or null | Why the rule has its wording, or its paired lint rule for a remainder rule. It is `null` when absent. |
| `rules[].ai_signal` | string | How strongly a match suggests generated text: `strong`, `weak`, or `none`. |
| `rules[].ai_signal_source` | string | The evidence for `ai_signal`: `measured`, `catalog`, or `unmeasured`. |
| `rules[].tokens` | array of strings or null | The phrases of a `tokens` rule. It is `null` for other kinds. |
| `rules[].pattern` | string or null | The regular expression of a `pattern` rule. It is `null` for other kinds. |
| `rules[].substitutions` | object or null | The phrase-to-replacement map of a `substitution` rule. It is `null` for other kinds. |
| `rules[].metric` | string or null | The measurement of a `metric` rule, such as `sentence_words`. It is `null` for other kinds. |
| `rules[].threshold` | number or null | The limit of a `metric` rule. It is `null` for other kinds. |
| `rules[].comparison` | string | How a `metric` rule compares with `threshold`: `gt`, `gte`, `lt`, or `lte`. Other kinds carry the default, `gt`, and ignore it. |
| `rules[].ignore_case` | boolean | Whether a match ignores letter case. |
| `rules[].match_all_caps` | boolean | Whether a match written in capitals counts. |

A test compares this table with the keys that `slopvac rules --format json`
prints. A new key fails that test until this page lists it.

## Markdown

The output starts with a title and a line that gives the number of rules and
the profile. When the output omits excluded rules, the next line says so.

Category headings use level 2. Each one gives the category title, the category
id, and the genres from `recommended_for`. Under each category, each rule has
a level-3 heading with its `rule_id` and name. Categories are sorted by id,
and rules by id inside a category. The list under each rule heading gives these
fields, in order:

1. `Category`: the category id.
2. `Scope`: the unit that the rule judges.
3. `Kind`: the checker.
4. `Severity`: the shipped level, then the level at the profile.
5. `Tier at <profile>`: the tier at the profile, then the tier at each profile.
6. `Question` for a judgement rule, or `Message` for a checked rule. The
   message shows its slots as `<match>` and `<replacement>`.
7. `Fix`, when the rule has one.
8. One `Example` item for each example. It holds the `bad` text in a code
   block, then the `good` text in a code block, then the note. When the example
   has no `good` text, the item says `none`. An empty `good` text means that
   the fix deletes the text.
9. `Exceptions`, when the rule has named exceptions.
10. `Source`: the source, then `ste_ref`, `orwell_ref`, and `url` when the rule
    has them.
11. `Source note`, when the rule has one.

Without `--profile`, the output lists each selected rule, with tiers at
`normal`. With `--profile`, the output omits each rule whose tier is
`excluded` at that profile. `--include-excluded` keeps those rules, and their
`Tier` line shows `excluded`.

The rule blocks quote catalogue text, so they sit between
`<!-- slopvac-disable -->` and `<!-- slopvac-enable -->`. Lint reports no
finding inside them. The `ai-tells-formatting.em-dash-density` rule still
counts their dashes, because it measures the whole document.

`slopvac explain <rule_id> --format md` prints the block of one rule. It takes
`--profile` and `--config` in the same way, and uses the code that renders
`slopvac rules`. This block comes from
`slopvac explain prose-discipline.competing-actor-terms --format md`:

````markdown
<!-- slopvac-disable -->
### `prose-discipline.competing-actor-terms`: Pick one term for one subject

- Category: `prose-discipline`
- Scope: `document`
- Kind: `judgement`
- Severity: `suggestion`; at `normal`: `suggestion`
- Tier at `normal`: `enforced`; all tiers: `strict=enforced normal=enforced relaxed=advisory`
- Question: List every term this document uses for a person or system that acts: user, customer, client, consumer, caller, requester, tenant, account, operator, admin, developer, integrator, subscriber, end user. For each pair, do they name the same subject? If yes, that is rotation and one term must win. If no, does the document define the difference at first use?
- Fix: Choose the narrowest accurate term, replace every other, and define the distinction at first use only when two subjects genuinely differ.
- Example 1, `bad`:

  ```text
  The user submits a job. The customer receives a token. The client then polls for the result.
  ```

  `good`:

  ```text
  The user submits a job, receives a token, and polls for the result.
  ```

  Note: Three terms, one actor. The fix is one term, not three synonyms.
- Example 2, `bad`:

  ```text
  The caller opens a connection. The consumer must close it.
  ```

  `good`:

  ```text
  The caller opens the connection and must close it.
  ```
- Source: ASD-STE100; ste_ref `9:1.11`
- Source note: The specification requires one name for one thing. Software prose breaks this most often across actor nouns, because each one reads as a legitimate synonym in isolation. Kept as judgement because co-occurrence alone does not prove rotation: a document may legitimately distinguish a user from the client library that acts for them.
<!-- slopvac-enable -->
````

A test compares this block with the output of that command.
