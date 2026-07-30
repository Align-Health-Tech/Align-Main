"""Test package marker.

Without this, `unittest discover` rejects `tests/` as "not importable" for any
invocation that sets an explicit top-level dir (e.g. `-t .`), and the suite is
only runnable via the exact form in package.json. Modules here already import
each other as `tests.mock_clinical_ai`, so the package form is the intended one.
"""
