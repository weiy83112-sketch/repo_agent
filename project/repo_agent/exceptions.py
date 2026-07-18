# 项目级异常：表示一次 Agent 运行超过了某种安全限制
class AgentLimitError(RuntimeError):
    pass


# 项目级异常：表示一次 Agent 模型请求超过了时间限制
class AgentTimeoutError(AgentLimitError):
    pass
