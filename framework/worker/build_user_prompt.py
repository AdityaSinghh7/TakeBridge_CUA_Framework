WORKER_DEFAULT_REPLY = """
Please check the screenshot and see if the task is impossible to complete due to environmental constraints. If it is, reply with 'INFEASIBLE'.
If it is possible to complete, please complete the task, and before making any tool call, you should reasoning the next move according to the UI screenshot and instruction, while refer to the previous actions (tool calls), screenshots, and observations for reflection.

Note the user task is:
{instruction}

""".strip()