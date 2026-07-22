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

## Evaluation commands

Run all offline checks without sending a model request:

```powershell
python -m evaluation --capability simple --validate-only
python -m evaluation --capability complex --validate-only
python -m evaluation --stage hybrid-rag --capability simple --validate-only
python -m evaluation --stage hybrid-rag --capability complex --validate-only
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

After explicitly approving paid model calls, run the Hybrid RAG Agent against
the same fixed cases:

```powershell
python -m evaluation --stage hybrid-rag --capability simple
python -m evaluation --stage hybrid-rag --capability complex
```

These commands write `results/hybrid-rag-flash-high.jsonl` and
`results/hybrid-rag-pro-high.jsonl`. The Evaluation Runner and resume behavior
remain identical; only the selected Adapter changes. Hybrid RAG opens one
persistent repository index per snapshot and reuses it across that repository's
cases.

## Pytest-only comparison

Use the repository filter to avoid indexing or evaluating the other snapshots:

```powershell
python -m evaluation.retrieval_scorer --repository pytest
python -m evaluation --stage hybrid-rag --repository pytest --capability simple
python -m evaluation --stage hybrid-rag --repository pytest --capability complex
```

Filtered model runs use `-pytest.jsonl` result files, so they cannot be confused
with complete 31-case runs. Generate the four-way pytest comparison with:

```powershell
python -m evaluation.scorer --repository pytest `
  --result "Baseline Flash=evaluation/results/baseline-flash-high.jsonl" `
  --result "Baseline Pro=evaluation/results/baseline-pro-high.jsonl" `
  --result "Hybrid Flash=evaluation/results/hybrid-rag-flash-high-pytest.jsonl" `
  --result "Hybrid Pro=evaluation/results/hybrid-rag-pro-high-pytest.jsonl" `
  --output evaluation/reports/baseline-vs-hybrid-pytest.md
```

## Offline scoring

Generate the reusable Flash/Pro baseline report from the saved JSONL files:

```powershell
python -m evaluation.scorer
```

The scorer joins each result to its fixed case through `case_id` and writes
`reports/baseline-summary.md`. It computes completion, literal file/symbol
evidence coverage, tool-call counts, latency, and failure summaries without
calling a model. Evidence coverage is not treated as answer correctness;
human correctness remains an explicit unfilled 0/1/2 field.
