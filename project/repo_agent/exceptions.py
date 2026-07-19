# 项目级异常：表示一次 Agent 运行超过了某种安全限制
class AgentLimitError(RuntimeError):
    pass


# 项目级异常：表示一次 Agent 模型请求超过了时间限制
class AgentTimeoutError(AgentLimitError):
    pass


# 项目级异常：图正常结束，但最后一条 assistant 消息没有可用文本。
class AgentResponseError(RuntimeError):
    pass


# 项目级全局异常：模型 SDK 无法连接服务，或服务拒绝当前请求。
class ModelServiceError(RuntimeError):
    pass
