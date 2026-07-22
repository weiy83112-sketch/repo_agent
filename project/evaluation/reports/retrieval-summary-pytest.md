# Hybrid RAG Retrieval Evaluation

`Recall@5` 表示固定题目的正确文件或符号是否出现在前五个候选中；`MRR` 衡量第一个正确候选的排名。该报告不调用回答模型。

| Method | Hits@5 | Recall@5 | MRR | Avg query | P95 query |
| --- | ---: | ---: | ---: | ---: | ---: |
| keyword | 8/15 | 53.3% | 0.199 | 0.041s | 0.083s |
| vector | 6/15 | 40.0% | 0.227 | 0.139s | 0.221s |
| hybrid | 7/15 | 46.7% | 0.306 | 0.183s | 0.307s |

## Boundary

- A hit requires an exact expected repository-relative file path or an exact/qualified expected symbol.
- Retrieval metrics isolate evidence selection; final answer quality is measured separately with saved DeepSeek results.
