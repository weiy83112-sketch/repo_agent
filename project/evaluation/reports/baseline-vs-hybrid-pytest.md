# Repo Agent Evaluation Summary

自动证据覆盖率只表示答案是否提到固定题库中的标准文件和符号，不等同于回答正确性。人工正确性评分（0/1/2）尚未填写。

## Overall

| Run | Model | Completed | Evidence | Completed evidence | Full evidence | Tools | Avg time | P95 time |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline Flash | deepseek-v4-flash | 11/15 (73.3%) | 66.7% | 96.0% | 9/15 (60.0%) | 128 | 24.28s | 39.20s |
| Baseline Pro | deepseek-v4-pro | 12/15 (80.0%) | 73.6% | 96.4% | 10/15 (66.7%) | 116 | 29.93s | 43.46s |
| Hybrid Flash | deepseek-v4-flash | 14/15 (93.3%) | 93.1% | 100.0% | 14/15 (93.3%) | 95 | 25.24s | 40.84s |
| Hybrid Pro | deepseek-v4-pro | 15/15 (100.0%) | 100.0% | 100.0% | 15/15 (100.0%) | 91 | 37.14s | 60.86s |

## Failures

- Baseline Flash: AgentLimitError: 4
- Baseline Pro: AgentLimitError: 3
- Hybrid Flash: AgentLimitError: 1
- Hybrid Pro: None

## By category

### Baseline Flash

| Category | Completed | Evidence coverage |
| --- | ---: | ---: |
| call_chain | 3/4 (75.0%) | 76.2% |
| entry_point | 2/3 (66.7%) | 61.5% |
| feature_location | 6/6 (100.0%) | 92.3% |
| related_files | 0/2 (0.0%) | 0.0% |

### Baseline Pro

| Category | Completed | Evidence coverage |
| --- | ---: | ---: |
| call_chain | 2/4 (50.0%) | 47.6% |
| entry_point | 3/3 (100.0%) | 100.0% |
| feature_location | 6/6 (100.0%) | 96.2% |
| related_files | 1/2 (50.0%) | 41.7% |

### Hybrid Flash

| Category | Completed | Evidence coverage |
| --- | ---: | ---: |
| call_chain | 3/4 (75.0%) | 76.2% |
| entry_point | 3/3 (100.0%) | 100.0% |
| feature_location | 6/6 (100.0%) | 100.0% |
| related_files | 2/2 (100.0%) | 100.0% |

### Hybrid Pro

| Category | Completed | Evidence coverage |
| --- | ---: | ---: |
| call_chain | 4/4 (100.0%) | 100.0% |
| entry_point | 3/3 (100.0%) | 100.0% |
| feature_location | 6/6 (100.0%) | 100.0% |
| related_files | 2/2 (100.0%) | 100.0% |

## Interpretation boundary

- `Evidence` includes failed cases as zero coverage, so it reflects end-to-end reliability.
- `Completed evidence` only measures answers that completed successfully.
- Literal path/symbol matching is deterministic and reproducible, but cannot judge whether an explanation is logically correct.
- Final correctness and unsupported-claim counts require human review.
