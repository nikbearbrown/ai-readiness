# Canvas course exports (.imscc): what the tool reads and writes

A Canvas export is a zip: a Common Cartridge 1.1 manifest plus Canvas-only files in `course_settings/` that Canvas uses to rebuild modules, assignments, rubrics and settings. This page records the format as observed in five real Canvas exports (2026), and how `./arc` changes it. Items marked **unverified** come from general knowledge and have not been tested by importing into Canvas.

## Layout

```
imsmanifest.xml                      resources + the module tree (organizations)
course_settings/
  course_settings.xml                course identifier, title, settings
  syllabus.html                      the syllabus page
  module_meta.xml                    modules and their items (Canvas reads this)
  assignment_groups.xml              groups and weights
  rubrics.xml                        only when the course has rubrics
  files_meta.xml, context.xml, media_tracks.xml, canvas_export.txt, …
wiki_content/<slug>.html             pages
<id>/<slug>.html + assignment_settings.xml    one folder per assignment
<id>.xml                             discussion or announcement (imsdt), and its settings (topicMeta)
<id>/assessment_qti.xml …            classic quizzes (the tool never edits these)
web_resources/…                      course files: images, PDFs, video
```

## Identifiers

Every module, module item and resource has an identifier of the form `g` plus 32 lowercase hex characters. The same identifier appears in up to four places, and they must agree:

| Object | Where its identifier appears |
|---|---|
| Module | `module_meta.xml` `<module identifier>` and the manifest's module tree `<item identifier>` |
| Module item | `module_meta.xml` `<item identifier>` and the manifest tree `<item identifier>`; both point (`identifierref`) at a resource |
| Page | manifest `<resource identifier>` and the page's own `<meta name="identifier">` |
| Assignment | manifest resource, the folder name, and `assignment_settings.xml` `<assignment identifier>` |
| Discussion | manifest `imsdt` resource, its `<dependency>` on the topicMeta resource, and topicMeta `<topic_id>` |
| Rubric | `rubrics.xml` `<rubric identifier>` and each user's `<rubric_identifierref>` |

In every export examined, the manifest's module tree and `module_meta.xml` list the same modules and items in the same order with the same titles. `./arc` refuses to edit modules in an export where they disagree.

New identifiers are `"g" + md5(stable key)`, where the key is the suggestion id, the op's position and its title. Rebuilding the same plan gives the same identifiers.

## What each op writes

| Op | Files written |
|---|---|
| `add_module` | a `<module>` in `module_meta.xml` (positions renumbered 1..n); a matching `<item>` in the manifest tree at the same index |
| `add_page` | `wiki_content/<slug>.html` with identifier, editing roles and workflow-state meta tags; a `webcontent` resource; the module item in both trees |
| `add_assignment` | `<id>/<slug>.html` and `<id>/assignment_settings.xml` (the full Canvas field set, no dates); a resource listing both files; the module item; a rubric and group if needed |
| `add_discussion` | `<id>.xml` (topic, HTML entity-escaped inside `<text>`) and a topicMeta `.xml` (with an embedded `<assignment>` when graded); two resources; the module item |
| rubric (with either) | a `<rubric>` in `course_settings/rubrics.xml`, creating the file and listing it in the course-settings resource if the course had none; criterion and rating ids are local (`_1234`) |
| `edit_syllabus`, `edit_page` | only the bytes inside `<body>` |
| `edit_assignment` | the description's `<body>`; for new criteria, a **new** rubric (old criteria + new) attached to this assignment only, so a rubric shared with other assignments is never changed; `points_possible`, `submission_types`, `allowed_extensions` if asked |
| `edit_discussion` | the topic's escaped HTML inside `<text>`; for a graded discussion, the embedded `<assignment>` in its topicMeta (rubric copy as above, points) |

Writes are surgical text insertions. The tool never re-serializes XML (that would rewrite namespace prefixes and every untouched byte). Untouched entries, including all media, are copied from the original zip unchanged: an unmodified pack is entry-for-entry identical to the export.

## Sections inside a page

`insert_after` and `replace_section` find a heading by its text (case and spacing ignored). A section runs to the next heading of the same or higher level. Canvas pages often wrap sections in layout `<div>`s, so the tool steps back over the wrappers that open the next section and the closing tags of this one; the new content lands at the end of this section's own block. Headings in the inserted content are shifted to match the section's level. `replace_section` refuses when the old section's `<div>`, `<ul>` or `<table>` tags are unbalanced, because replacing it would break the page's layout.

## Importing

- **Into a new or sandbox course:** everything is created. This is the recommended path.
- **Into the course the export came from (unverified):** Canvas records each imported identifier as the object's migration id and updates objects whose migration id matches. Objects first created by hand in that course have no migration id, so re-importing its own export probably **duplicates** them. Objects created by an earlier import of the same package are matched and overwritten.
- Links to other Canvas courses (`…/courses/<number>/…`) are not rewritten on import.
- Upload size limits vary by institution; exports with video can exceed 1 GB.

## Folder input

`./arc open <folder>` builds a minimal Canvas cartridge: one module per subfolder (a leading number is dropped from the name), one page per Markdown, HTML or text file (titled by its first `#` heading), other files attached under `web_resources/` and linked from a "Files: <module>" page, and `syllabus.*` as the syllabus. The same plan, apply and pack steps then work on it.
