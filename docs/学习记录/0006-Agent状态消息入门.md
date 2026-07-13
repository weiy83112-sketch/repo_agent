# Messages connected to source-project reading

The original lesson 0006 was too abstract, so it was rewritten around the user's real learning route: read open-source Agent projects under `source/`, extract concepts into `docs/`, then implement the user's own project under `project/`.

The user should understand `messages` as the Agent work log:

```text
user asks how to run source/openhands
assistant decides to call read_file
tool returns README content
assistant answers from the tool result
```

Durable insight:

```text
messages is not just chat history.
For an Agent, messages records the full task trace: user request, model action, tool result, and final answer.
```

Future lessons should stay grounded in a concrete source project whenever possible.
