---
name: create-user-story-and-ac
description: 'Use when the user asks to review a GitHub Projects Ready column and add
  missing User Story and Acceptance Criteria sections to its work items. Derive the
  content from each item title, preserve existing descriptions, and format Acceptance
  Criteria as a Markdown checklist.'
---

# Create User Story and AC

Review the specified GitHub Projects board and enrich only the work items in its
`Ready` status. For each item, inspect its current description before editing:

- Add a `## User Story` section only when one is missing or empty.
- Add a `## Acceptance Criteria` section only when one is missing or empty.
- Use the item title as the primary source for both sections.
- Format every acceptance criterion as an unchecked Markdown checklist item:
  `- [ ] ...`.
- Preserve all existing description text and existing non-empty sections.
- Do not modify items in other statuses.
- Do not change titles, labels, assignees, priorities, or other project fields.

## Workflow

1. Find the project. Default: `PythonBMI Backlog` owned by `BrianNguyen291`.
   ```bash
   gh project list --owner BrianNguyen291
   ```
   `gh` needs the `project` scope (`gh auth refresh -s project`).
2. List the items and keep only those whose `status` is `Ready`.
   ```bash
   gh project item-list <NUMBER> --owner BrianNguyen291 --format json --limit 200
   ```
3. Read each Ready item's description.
   - Issue: `gh issue view <N> -R BrianNguyen291/PythonBMI --json title,body`
   - Draft issue: `content.body` from the item list.
4. Skip the item when both sections already exist and are non-empty.
5. Read `app.py`, `templates/` and `tests/` so the story fits what the BMI site already
   does (BMI form, optional user name, history at `/users/<name>`).
6. Write the missing sections from the title, in the title's language (usually 繁體中文):
   - User Story: `身為 <角色>，我想要 <功能>，以便 <價值>。`
   - Acceptance Criteria: 3–6 testable items in Given / When / Then form, with real
     numbers (thresholds, units, rounding). Name the source and effective date of any
     regulation used.
   - Do not invent scope the title does not imply; list open questions under
     `## Notes` instead.
7. Update the item, appending below any existing text.
   - Issue: `gh issue edit <N> -R BrianNguyen291/PythonBMI --body-file <file>`
   - Draft issue: `gh project item-edit --id <DI_ id> --title "<same title>" --body "<body>"`
8. Report a table: item title → updated / skipped.

## Template

```markdown
## User Story
身為 <角色>，我想要 <功能>，以便 <價值>。

## Acceptance Criteria
- [ ] **AC1** Given <前提>，When <動作>，Then <結果>。
- [ ] **AC2** ...

## Notes
- 待確認：<open questions>
```
