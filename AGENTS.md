# Working on The Daily Douglas

This repository is a reusable newspaper renderer. Keep personal editions, account
identifiers, tokens and printer queue names in ignored local configuration and
data directories, not in examples or tests.

Use the `daily-newspaper` skill for producing an edition. For code changes, run
`python -m unittest discover -s tests -v`. Changes to layout also need a rendered
demo and visual inspection of all four reading pages and both imposed A4 pages.

The generator must fail clearly on overflow or unsupported content rather than
silently lose text. Preserve `[4|1] [2|3]` imposition. Tests must mock physical
printing and must not access personal accounts. Keep printing opt-in and retain
the record before submitting a job, including uncertain attempts.
