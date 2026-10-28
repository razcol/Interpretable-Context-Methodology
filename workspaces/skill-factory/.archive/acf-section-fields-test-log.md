# Test Log: acf-section-fields

## Use Case

Agent-suggested, using real project files plus one new-section fixture.

1. Existing Jaecoo section: `code/app/components/Sections/IconsWithInfo/ClientIconsWithInfo.js` and `IconsWithInfo.gql`. Expected: frontend contract found, `order` not proposed as a field, shared `layout` and `buttonFields` marked as clones, no patched file required.
2. Same layout name, two sites: Jaecoo and luxury-trade `HeroBanner.gql`. Expected: the audit says the field lists differ.
3. New section: an HTML block `data-section="PromoStrip"` (heading, paragraph, image, button, repeated items) audited against the Jaecoo repo. Expected: layout missing, spec created. A fixture ACF export containing `group_existing` / flexible `flexible` / layout `HeroBanner` is patched. Expected: group key unchanged, HeroBanner's `buttonFields` key unchanged, new layout copies that clone under a new field key and keeps `clone: ["field_shared_button"]`. Running the patch again reports the layout already present and writes nothing. A spec whose clone name is not in the export writes nothing and exits 3. `add-fields` on HeroBanner adds `title` and does not duplicate `buttonFields`.

## Approach Under Test

Audit plus patched ACF export (candidate A). The live PHP writer (candidate B) was not drafted. These machines do not have the ACF runtime for Jaecoo or luxury trade, and a write against the real group cannot be rolled back from here. The read-only `inspect_acf_layout.php` is included for operators who have WP-CLI. `php` is not installed in this environment, so that file was not syntax-checked.

## Steps Taken

1. Studied both Next repos and the matching themes under `/home/dev/apicolmobil`. No `acf-json`, no `acf_add_local_field_group`.
2. Ran `scripts/audit_sections.py` on the IconsWithInfo files, both HeroBanner fragments, and the PromoStrip HTML.
3. Built a fixture export at `stages/04-draft-and-test/output/test-run/export.json` (not a real WordPress export).
4. Ran `scripts/patch_acf_export.py` for create, second create, incomplete clone, add-fields, and a two-group export.

## Decisions Made

- A matching `.gql` file is a frontend contract, not proof the layout exists in production. The IconsWithInfo report says WordPress status is unknown.
- New sections are a layout on `fields.flexible`, not a new field group. The fixture still has one group key after the patch: `group_existing`.
- Clone fields are copied from a sibling layout. If the sibling name is missing, no import file is written.
- Leaf fields that are rendered with `__html: name` are labeled `wysiwyg or text` instead of a hard type. IconsWithInfo `description` is that label because the item body uses `__html: description`. `comment` stays `text`.
- Keys are minted only inside the patched copy. The original `field_button_old` on HeroBanner was still `field_button_old`. The copied button on PromoStrip had a different key and the same external clone target.

## Outcome

Matched the expected results.

- IconsWithInfo: `frontend_contract` found, action `confirm`, fields `title`, `description`, `iconList`, `iconList.icon` (clone of MediaItem), `buttonFields` (clone of ButtonItem), `comment`, `layout` (clone of Layout). `order` listed as a renderer prop. Post types included `model`, `page`, `article`, `serviceCenter`, `showRoom`.
- HeroBanner: both audits warned that the other repo's fields differ (`bannerCards` is luxury-only; Jaecoo's single-banner fields are not on the luxury fragment).
- PromoStrip: action `create-layout`, inferred fields `layout`, `title`, `description`, `imageFields`, `buttonFields`, `items` (with `title` and `icon`). Patch status `patched`. Second run status `layout-already-in-export` and no second file. Orphan clone exit 3, no file. Add-fields added only `title`. Two groups both named for GraphQL `fields` exited 1 and wrote nothing.

Not verified: importing the patched JSON into WordPress, `wp acf json sync`, or `inspect_acf_layout.php` against a real site. PHP is not installed here.

## Findings / Improvement Opportunities

- HTML inference is a review aid. The PromoStrip audit marks every field inferred. An editor still has to confirm names before import.
- `description` on IconsWithInfo is both plain text (the section body) and HTML (each icon). The audit says `wysiwyg or text` for both. That is intentional; the fragment does not carry ACF types.
- The inspect script still needs `php -l` on a machine with PHP, and a dry read against one real environment, before anyone treats its exit codes as confirmed.
