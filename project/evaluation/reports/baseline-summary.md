# Repo Agent Evaluation Summary

自动证据覆盖率只表示答案是否提到固定题库中的标准文件和符号，不等同于回答正确性。人工正确性评分（0/1/2）尚未填写。

## Overall

| Run | Model | Completed | Evidence | Completed evidence | Full evidence | Tools | Avg time | P95 time |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Flash High | deepseek-v4-flash | 26/31 (83.9%) | 80.5% | 97.0% | 22/31 (71.0%) | 252 | 26.71s | 44.62s |
| Pro High | deepseek-v4-pro | 28/31 (90.3%) | 86.8% | 97.2% | 25/31 (80.6%) | 236 | 32.96s | 55.71s |

## Failures

- Flash High: AgentLimitError: 5
- Pro High: AgentLimitError: 3

## By category

### Flash High

| Category | Completed | Evidence coverage |
| --- | ---: | ---: |
| call_chain | 8/9 (88.9%) | 89.8% |
| entry_point | 6/7 (85.7%) | 82.9% |
| feature_location | 10/11 (90.9%) | 83.7% |
| related_files | 2/4 (50.0%) | 53.8% |

### Pro High

| Category | Completed | Evidence coverage |
| --- | ---: | ---: |
| call_chain | 7/9 (77.8%) | 77.6% |
| entry_point | 7/7 (100.0%) | 100.0% |
| feature_location | 11/11 (100.0%) | 98.0% |
| related_files | 3/4 (75.0%) | 65.4% |

## Interpretation boundary

- `Evidence` includes failed cases as zero coverage, so it reflects end-to-end reliability.
- `Completed evidence` only measures answers that completed successfully.
- Literal path/symbol matching is deterministic and reproducible, but cannot judge whether an explanation is logically correct.
- Final correctness and unsupported-claim counts require human review.
