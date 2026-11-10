# Moodle course run sync

This feature lets a Moodle instance push course creations/updates/deletions
to Joanie automatically, through a dedicated Moodle plugin
([`local_joanie_courses_sync`](https://gitlab.fun-edu.fr/fun/moodle-joanie-courses-sync),
externalized in its own repo). It reuses the `course-runs-sync` endpoint
already used by fun-apps (OpenEdX), with the same HMAC-SHA256 signature
scheme — no new endpoint was needed for the sync itself.

This page only covers what has to be set up and understood **on the Joanie
side**. For the plugin's own installation and admin settings, see that
repo's `README.md`.

> **Status**: carried by PR [openfun/joanie#1372](https://github.com/openfun/joanie/pull/1372)
> (branch `moodle-sync`), not merged yet. None of this exists on a real
> Joanie environment until it is.

## Overview

```
Moodle (plugin)                      Joanie (lms_handler app)
──────────────────                   ─────────────────────────
observer::course_changed()   ──►     POST /api/v1.0/course-runs-sync/
observer::course_deleted()   ──►     POST /api/v1.0/course-runs-delete/   ⚠️ see "Known gap" below
```

Both calls are signed HMAC-SHA256 over the exact JSON body sent
(`Authorization: SIG-HMAC-SHA256 <hex>`), checked by
`joanie.core.utils.signature.check_signature` against **any** value in
`JOANIE_COURSE_RUN_SYNC_SECRETS` — so several secrets can be valid at once
(secret rotation without downtime).

Relevant Joanie code lives in `joanie.lms_handler`:
- `api.py`: `course_runs_sync` view (and `course_runs_delete`, see the gap below)
- `backends/moodle.py`: `MoodleLMSBackend`, extracts the course number,
  filters out protected fields, provides the serializer
- `serializers.py`: `SyncCourseRunSerializer` (accepted/validated fields)
- `core/utils/signature.py`: HMAC check

## Known gap — `course-runs-delete` doesn't exist yet

The plugin already POSTs to `/api/v1.0/course-runs-delete/` whenever a
Moodle course is deleted (`observer::course_deleted`, queued as an adhoc
task on the Moodle side). **This endpoint does not exist in the current
state of PR #1372** — only `course-runs-sync` is declared in
`lms_handler/urls.py` / `api.py` on branch `moodle-sync`. It existed in an
earlier revision of the PR and was dropped since.

If the plugin is deployed before this is resolved, every Moodle course
deletion queues a task that fails with a 404 and gets retried indefinitely
by Moodle's cron with an increasing backoff (the plugin's
`sync_course_run_task::execute()` throws on any non-2xx status, with no
distinction between a transient and a permanent failure) — cluttering
Moodle's *Scheduled task report* without ever succeeding.

**Before relying on deletion sync in any real environment**: either add
`course_runs_delete` back to Joanie, or drop the call from the plugin if
deletion sync is out of scope for this iteration.

## Settings to add on every deployment

Two environment variables, no database migration.

### 1. `JOANIE_LMS_BACKENDS` — add a Moodle entry

A JSON string (list of dicts), one entry per connected LMS. Keys required
for every entry (validated by `LMSBackendValidator`,
`core/utils/__init__.py`): `BACKEND`, `BASE_URL`, `COURSE_REGEX`,
`SELECTOR_REGEX`. Add the Moodle entry to the existing list — don't replace
other LMS entries (e.g. edX):

```json
{
  "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
  "BASE_URL": "https://moodle.example.org/webservice/rest/server.php",
  "API_TOKEN": "<Moodle webservice token>",
  "COURSE_REGEX": "^.*/course/view\\.php\\?id=.*$",
  "SELECTOR_REGEX": "^.*/course/view\\.php\\?id=.*$"
}
```

- `BASE_URL` / `API_TOKEN`: used by the **pre-existing** Moodle features
  (enrollments, grades via `moodlepy`, see `docs/moodle.md`), not by the
  course sync itself — but still required to instantiate the backend
  (`MoodleLMSBackend.__init__` does `self.configuration["API_TOKEN"]`
  directly, no fallback: `KeyError` otherwise).
- `COURSE_REGEX` / `SELECTOR_REGEX`: must match the `resource_link` sent by
  the plugin, i.e. `<moodle_url>/course/view.php?id=<id>` (see
  `build_payload()` in the plugin's `classes/observer.php`). If several LMS
  entries share a broad `SELECTOR_REGEX`, `LMSHandler.select_lms` falls back
  to checking that the backend's `BASE_URL` is contained in the
  `resource_link` — so a broad regex isn't fatal, but a precise one is
  still preferable.
- Moodle-sync-specific optional keys (default behavior applies when
  omitted):
  - `COURSE_NUMBER_REGEX`: overrides the regex used to extract the course
    number from `idnumber` (default `^(?P<course_number>\d+)-session\d+M$`,
    see naming convention below).
  - `COURSE_RUN_SYNC_NO_UPDATE_FIELDS`: fields to never overwrite on update
    (e.g. `["languages"]`, recommended by the plugin's README for the
    `lang`/"Force language" caveat).

Unrelated to this PR, only needed if Moodle enrollment/grading is also used:
`JOANIE_LMS_MOODLE_STUDENT_ROLE_ID`, `MOODLE_AUTH_METHOD`.

### 2. `JOANIE_COURSE_RUN_SYNC_SECRETS` — add the shared secret

List of accepted secrets. Add the one chosen for Moodle to the existing
list — it **must** exactly match the value set in the Moodle plugin's admin
settings (**Local plugins > Joanie course sync > Shared secret**):

```shell
JOANIE_COURSE_RUN_SYNC_SECRETS=existing-edx-secret,new-moodle-secret
```

(Exact format — comma-separated list or JSON — depends on the config
mechanism used in each environment; in `settings.py` it's a
`values.ListValue`.)

No other Joanie-side config is needed: no new table, no migration, no code
redeploy beyond merging the PR itself.

## What gets created/updated in the database

On creation (first `course-runs-sync` call for a given `resource_link`):
- The course number is extracted from `idnumber` (see naming convention
  below), then normalized through `utils.normalize_code` (`slugify` +
  uppercase).
- If no `Course` has that code yet, it is **created** with that code, and
  either the `title` sent by the plugin or the code itself as a fallback.
- A `CourseRun` is created, attached to that `Course`, with its own `title`
  (always the one sent at creation time, or the `Course`'s as a fallback —
  never re-read afterwards, see below).
- **No `Organization` is attached automatically** — same as for edX today.
  Always a manual step in the Joanie back office after the first sync.

On update (a `CourseRun` already exists for this `resource_link`):
- Only `start`, `end`, `enrollment_start`, `enrollment_end`, `languages` are
  overwritten (minus whatever is listed in `COURSE_RUN_SYNC_NO_UPDATE_FIELDS`).
- `title` and `idnumber` of the `CourseRun`/`Course` are **never** re-read
  after creation — a deliberate choice (risk of a title polluted by
  Moodle's multilingual markup, and avoiding an `idnumber` edit silently
  re-assigning the `CourseRun` to a different `Course`).

`enrollment_start`/`enrollment_end` always stay `null` for a Moodle
`CourseRun` (the plugin never sends them, see its README):
`CourseRun.compute_state()` then permanently returns `TO_BE_SCHEDULED`,
regardless of the actual `start`/`end` dates — accepted because enrolling
in a Moodle course doesn't go through Joanie's order flow.

## `idnumber` → `Course.code` naming convention

`MoodleLMSBackend.extract_course_number` defaults to expecting
`[course_number]-session[N]M` (e.g. `71015-session01M`) and rejects the sync
with a **400** if `idnumber` doesn't match (or is empty) **and** no
`CourseRun` already exists for this `resource_link` — on an update to an
already-synced `CourseRun`, `idnumber` is no longer required (it's never
re-read after creation anyway).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `403 Missing authentication` | No `Authorization` header sent by the plugin (incomplete Moodle-side config) |
| `401 Invalid authentication` | Secret mismatch between the plugin and `JOANIE_COURSE_RUN_SYNC_SECRETS` |
| `400` on `resource_link` | `SELECTOR_REGEX`/`COURSE_REGEX` doesn't match any `JOANIE_LMS_BACKENDS` entry, or no LMS matches at all |
| `400` on `idnumber` | Naming convention not respected, course never synced before |
| `404` on `course-runs-delete` | Known gap, see dedicated section above |
| Sync returns 200 but nothing visibly changes | Check Django application logs — the view replies `200 {"success": true}` even when nothing actually changed (e.g. an update where every submitted field is in `COURSE_RUN_SYNC_NO_UPDATE_FIELDS`) |

## Deployment checklist

1. Merge PR #1372, deploy the resulting code to the target Joanie environment.
2. Add the Moodle entry to `JOANIE_LMS_BACKENDS` (see above).
3. Add the shared secret to `JOANIE_COURSE_RUN_SYNC_SECRETS`.
4. Deploy the plugin to the target Moodle instance (see its `README.md`),
   with the **same** secret and that environment's Joanie URL.
5. Check that at least one test course has a conforming `idnumber` before
   enabling sync in production.
6. Manually attach the `Organization` of the first created `Course` in the
   Joanie back office.
7. Confirm the `course-runs-delete` gap is resolved (endpoint added, or call
   removed from the plugin) before treating course deletion as functional.
