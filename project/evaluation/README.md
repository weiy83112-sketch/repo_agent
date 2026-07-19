# Evaluation Dataset

This directory contains the fixed question set used to compare the original
file-tool Agent with the code-aware hybrid retrieval version.

## Repository snapshots

`data/repositories.json` records the upstream URL and exact commit for each local
benchmark snapshot. The downloaded repositories remain under the ignored
`source/` directory and are not copied into this project.

## Cases

`data/cases.jsonl` contains:

- one small `repo_agent` teaching case;
- 15 pytest cases;
- 15 Django cases.

Each JSON object records the target repository, question, expected evidence
files, expected symbols, and evaluation category. The pytest and Django cases
cover entry points, feature locations, call chains, and related files.

The expected paths and symbols are checked against the recorded snapshots
before the dataset is used. Representative cases are still reviewed with the
user so the benchmark remains explainable in a portfolio interview; learning
the complete pytest and Django codebases is not required.

## Workflow

1. Load and validate every JSONL case.
2. Run the original Agent against the matching repository snapshot.
3. Save the baseline answer and execution metadata.
4. Implement the new retrieval pipeline without changing the question set.
5. Run the same cases again and compare retrieval and answer metrics.

## Baseline commands

Run all offline checks without sending a model request:

```powershell
python -m evaluation --capability simple --validate-only
python -m evaluation --capability complex --validate-only
```

Run the Flash High baseline first, then the Pro High baseline:

```powershell
python -m evaluation --capability simple
python -m evaluation --capability complex
```

The commands write `results/baseline-flash-high.jsonl` and
`results/baseline-pro-high.jsonl`. Every completed case is flushed immediately;
rerunning the same command validates the existing file and skips saved case IDs.

During a real run, evaluation questions and repository excerpts selected by the
Agent tools are sent to the configured DeepSeek API. API keys, `.env` contents,
environment variables, and HTTP request headers are never written to results.
