# Changelog

## 1.0.2 - 2026-09-26

- Quarantining a selection that included a file outside the scan root moved the files before it and then stopped without writing a manifest, leaving them unrecoverable. Every path is now checked before anything moves.
- A second quarantine within the same second failed because both batches wanted the same folder name; later batches now get a numbered folder.
- Near-name review missed names such as `report_final.pdf`, because `_` counts as part of a word when stripping copy markers.
- Behavioural tests covering the areas above and the rest of the core.

## 1.0.1 - 2026-09-26

- Release builds for macOS (Apple Silicon) and Linux (x86_64) alongside Windows, with one `SHA256SUMS.txt` per release.
- CI builds the macOS and Linux packages on every push.
- A screenshot of the running app in the README.

## 1.0.0 - 2026-09-16

- Initial public V1.
- Local-first desktop interface and core engine.
- Automated tests and Windows packaging workflow.
- Tagged-release workflow with SHA-256 checksums.