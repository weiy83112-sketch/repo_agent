# Repo Agent GitHub Repository Design

## Purpose

Publish the user-built CLI local repository reading Agent as a focused GitHub portfolio repository.

The GitHub repository name is:

```text
repo_agent
```

## Included Content

The repository contains only the Repo Agent project and the decisions needed to understand its development.

```text
repo_agent/
  repo_agent/             Python package and runnable CLI code
  design/                 Formal Repo Agent design and learning-path documents
  cowork/
    DECISIONS.md          Long-term project decisions
    TASKS.md              Current learning and implementation tasks
  README.md               Project overview, setup, and usage
  .gitignore              Files that must stay local
```

## Excluded Content

The repository must not include:

```text
.venv/                    Local Python environment and installed packages
source/                   Downloaded open-source reference projects
docs/                     General learning notes and logs outside this project
API keys or .env files     Secrets
__pycache__/              Generated Python cache files
```

## GitHub Publishing Flow

```text
Create clean repo_agent folder
-> Copy selected project code and documents into it
-> Add README.md and .gitignore
-> Initialize local Git repository
-> Create first commit
-> Publish the local repository to GitHub
```

## Success Criteria

- The GitHub repository is named `repo_agent`.
- A visitor can identify it as a CLI local repository reading Agent.
- A visitor can see the runnable code, design documents, and selected decisions/tasks.
- Local virtual environments, reference source code, logs, caches, and secrets are excluded.
- The repository is ready to grow into a DeepSeek-powered tool-calling Agent.
