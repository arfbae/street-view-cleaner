# Street View Cleaner Changelog

## 1.1.0

- Release-ready packaging updates for local installation and Docker deployment.
- Added a proper CLI entry point via `street-view-cleaner`.
- Added `MANIFEST.in` and package-data support so static UI files are included in builds.
- Added a `main()` launcher for `uvicorn` and improved local startup ergonomics.
- Improved package metadata and install instructions for first-time setup.
- Kept the mock-provider safe smoke path as the default local validation flow.

## 1.0.0

- Initial local FastAPI release with provider routing, preset safety, validation, and UI workflow.
- Added Windows local browser app, Qwen and Nano Banana providers, and Docker deployment scripts.
