# Field report template

`field-report.md` is the click list you follow in WordPress to build the section's group. It sits beside the component (`<app root>/<sectionsDir>/<Folder>/field-report.md`) as a helper you delete later. Write it in plain steps for someone clicking through the dashboard. Tool output goes only in the closing evidence block.

## Layout

```markdown
# <Folder>: fields to add in WordPress

Site: <repo name>. Section group: section: <graphqlName>. Layout: <Folder>.

## Steps

1. ...first dashboard step for this branch...
2. ...
(one block per field, in plan order, from acf-dashboard-steps.md)
N. Save: click Save Changes on the section group (older ACF shows Update).
N+1. ...the layout block, when this branch needs it...
N+2. Save the fields group the same way.

## When you are done

Reply `continue <node-id>` in the workspace chat.

## Evidence

- patterns: flexible type <flexible.union>, flexibleField <parentType>.<field>
- section <Folder>: layoutType <...>, groupType <...>, onFlexibleUnion <...>
- exposedAs: <list from section, or from a similar section>
```

## Which branch

Pick the branch from the `section <Folder>` and `patterns` JSON keys. Never from a `summary` sentence.

| State | Keys | First step |
|---|---|---|
| Missing | `layoutType` null and `groupType` null | Create the section group (block "Section group missing") |
| Group only | `groupType` set, `onFlexibleUnion` false | Open that group by GraphQL Field Name, add the missing fields, then the layout block |
| Layout type, not listed | `layoutType` set, `onFlexibleUnion` false, summary says it is not on the flexible type | Open the `fields` group and check the layout's Name and Clone; the layout exists but is not on the list |
| Already a layout | `onFlexibleUnion` true | Open the `fields` group and expand the layout; add only fields not in `tree` |

A set `patterns.flexibleField` means the shared `fields` group and its `flexible` field already exist: open it, never create it, never add a second flexible field. `patterns.flexible` null alone does not mean the `fields` group is missing. When `flexibleField.parentField` is `enFields`, write `enFields` and `enFlexible` wherever the steps say `fields` and `flexible`.

## Rules for every report

- Save the section group before the layout's Clone step points at it. A Clone cannot select an unsaved group.
- The save button is "Save Changes" on current ACF and "Update" on older versions. Write both.
- The location of a new section group comes from `section`'s `exposedAs` for a similar section, or from `patterns` (for example Post Type is equal to Post when similar sections are exposed as `Post.<name>`). Do not copy a location from another site.
- The group's list title cannot be read from GraphQL. Match an existing group by its GraphQL Field Name, and say so.
- English-only layouts use `EnFieldsEnFlexible<Folder>Layout`; say which language the layout is for.
- Every field gets its full block. Never shorten a field to one line, and never write "add the fields from the .gql".
