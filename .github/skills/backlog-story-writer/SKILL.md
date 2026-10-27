---
name: backlog-story-writer
description: Check every item in the Ready column of this repo's GitHub Project (kanban). If an item has no User Story or Acceptance Criteria, write them from the item's title and update the item. Use when asked to "check Ready backlogs", "write user stories", "補 User Story / 驗收條件", or after creating a new backlog item.
---

# Backlog Story Writer

Fill in missing **User Story** and **Acceptance Criteria** for backlog items in the
**Ready** column of the GitHub Project linked to this repo (PythonBMI, Flask BMI site).

## Inputs

- Project owner: `BrianNguyen291` (user-owned project)
- Project title: `PythonBMI Backlog` — find its number with `gh project list --owner BrianNguyen291`
- Repo: `BrianNguyen291/PythonBMI` (always pass `-R`; `gh` may default to the upstream fork)
- `gh` needs the `project` scope: `gh auth refresh -s project`

## Steps

1. List items and keep only those with `status == "Ready"`:
   ```bash
   gh project item-list <NUMBER> --owner BrianNguyen291 --format json --limit 200
   ```
2. For each Ready item, read the body:
   - Issue: `gh issue view <N> -R BrianNguyen291/PythonBMI --json title,body`
   - Draft issue: use `content.body` from the item list.
3. Skip the item if the body already contains **both** `## User Story` and `## Acceptance Criteria`.
4. Otherwise write them from the **title** (and any existing body text — keep it, append below):
   - Read `app.py`, `templates/` and `tests/` first so the story fits what the site already does
     (BMI form, optional user name, SQLite history at `/users` and `/users/<name>`).
   - Write in Traditional Chinese (繁體中文), matching the title's language.
   - Use the template below. 3–6 acceptance criteria, each testable, in Given/When/Then.
   - Put real numbers in the criteria (thresholds, units, rounding). If a rule comes from a
     regulation, name the source and its effective date.
   - Do not invent scope the title does not imply. List open questions instead of guessing.
5. Update the item:
   - Issue: `gh issue edit <N> -R BrianNguyen291/PythonBMI --body-file <file>`
   - Draft issue: `gh project item-edit --id <DRAFT_ISSUE_ID> --title "<title>" --body "<body>"`
     (the id is `content.id`, which starts with `DI_`)
6. Report a table: item title → updated / skipped (already had both).

## Template

```markdown
## User Story
身為 <角色>，我想要 <功能>，以便 <價值>。

## Acceptance Criteria
- [ ] **AC1** Given <前提>，When <動作>，Then <結果>。
- [ ] **AC2** ...

## Notes
- 待確認：<open questions, if any>
```

## Rules

- Never move items between columns and never change titles.
- Never overwrite an existing User Story or Acceptance Criteria section.
- Only touch items in the Ready column.
