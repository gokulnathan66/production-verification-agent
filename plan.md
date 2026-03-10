 use the bedrock aws llm antropic. and use the propmt.txt for orch agent and implement the below plan ```I can see your actual codebase! Your current orchestrator **has no LLM inside it** — it's a pure rule-based router that calls agents sequentially in hardcoded order. Here's exactly what's missing and how to wire an LLM into **your specific `OrchestratorAgentExecutor`**.

***

## What Your Current Orchestrator Does

Right now your `OrchestratorAgentExecutor.execute()` calls agents in a **hardcoded sequence**: code-logic → research → validation → tests. There's no LLM deciding what to do — it's just `if workflow == "verification": run these 4 agents`. That's a scripted pipeline, not an intelligent orchestrator. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/76332706/a223aa98-a338-4d7e-9f18-270bbe86666c/paste.txt?AWSAccessKeyId=ASIA2F3EMEYE6PGJWZPK&Signature=nwW%2BeQ3EFDzKxF5%2FNSY067P8KX0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEEwaCXVzLWVhc3QtMSJHMEUCIQDIi3NfiU9PlB34AGHK00ZqtfmAHf6iQKmNbZsiugerYQIgIgT1wdxNvF%2FkGJPpgIeofbYlMdFOA4zmtg4PvqN56S8q8wQIFRABGgw2OTk3NTMzMDk3MDUiDPKcMVnFOKav7zln3SrQBIOsasx36%2B37TIyWLG1MqOlEEGvcc%2BZCSqU37l3LbtAG6%2BzZiysWWvyAa9HaWN5RbOkTby0sngbocdA9IWxBHdTWaO7yUsBY0Dp5SZvtzPtpWr8lLeufuRWiRI8gA%2F%2BwUhmI3%2B7GV3X%2BM7wgrBcIxQOZbLdk6QSGZwb%2F5MHlDHtVeOPdGYRDtwAZjdDDIjdoKbWWGUxQ23sBkCLQIS6wiTPpulk89Ryen3GN4S4sbUljMid7L0PnoJ7EuR%2FzEr98mdp4joX49fBdCptKCQaTnH6GMhMzJRXRWPD61iwpMbS7OP17R67K69d%2FSUI4ys8xKiRyDtJScX3%2B6KoBTxxx7ny1LzQeq0CIJ95F5SwDUN62rP%2B%2FHiFvbft6f4c4ejEzFgEaWskLAhw9cu1%2FS6129BT8RWw0VOPCBQ86x84a9%2Be334all4sFcXy0X2u%2F44pvsCMCaEEmG5UBE%2FQyytbkHvhTPcgKwKTVcK8R5O%2B%2FQrkV%2BwlPA1ke1M4EeWmxo%2F3qyW5kzwQipnaLuucLhC0VlmNZ0PCc6Fw%2BvqTPw5CkZ5DPr9VMzcNm%2FGsBg4JPHOMv6JiG3QfwRWp8CmC7nw7cAZUGvrwy2ISyeHMH%2BEkGl3DqdDN6xTQ8jZM3fRHbH9ggcZGEeW57TP%2FrXypSDf547b1RgA4lo7FJFAeRFRC19Q6t0jFKrg668%2FIiQHWQz%2F0vSY7HGtc%2BRIaHRbxM8%2FkoMySh7luz7u2kmgM3cmMdHjMqcTdvT0r%2BzHbVJh%2FgV2MJVRDc%2BzyQoqxonzsQi3dOaFcwksS1zQY6mAGDXvFb%2FlrFjI%2F2PVw7MuyOB6wl%2B8hEC9mPnkx0AqrZsNZbH5kk5KKZOIViAlsGIsWjMX1AVuyCVcfhEo4zdXry99Ak2XnZ1K6TbOaz5EUPzt9s1sd%2FRhxbz3DOEThFdIoN5zvo7oXFXKjP1%2FGUAyg4PxJ1Cm9Vlf8bdIUvFcFnb7c%2BpQMGsDBAhweaydVyNS5OMWpi5yziKQ%3D%3D&Expires=1772973087)

***

## Where to Inject the LLM in Your Code

The LLM goes inside `MultiAgentOrchestrator` and replaces the hardcoded `runfullanalysis` / `handleverificationworkflow` logic. Here's the pattern for your existing file structure: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/76332706/a223aa98-a338-4d7e-9f18-270bbe86666c/paste.txt?AWSAccessKeyId=ASIA2F3EMEYE6PGJWZPK&Signature=nwW%2BeQ3EFDzKxF5%2FNSY067P8KX0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEEwaCXVzLWVhc3QtMSJHMEUCIQDIi3NfiU9PlB34AGHK00ZqtfmAHf6iQKmNbZsiugerYQIgIgT1wdxNvF%2FkGJPpgIeofbYlMdFOA4zmtg4PvqN56S8q8wQIFRABGgw2OTk3NTMzMDk3MDUiDPKcMVnFOKav7zln3SrQBIOsasx36%2B37TIyWLG1MqOlEEGvcc%2BZCSqU37l3LbtAG6%2BzZiysWWvyAa9HaWN5RbOkTby0sngbocdA9IWxBHdTWaO7yUsBY0Dp5SZvtzPtpWr8lLeufuRWiRI8gA%2F%2BwUhmI3%2B7GV3X%2BM7wgrBcIxQOZbLdk6QSGZwb%2F5MHlDHtVeOPdGYRDtwAZjdDDIjdoKbWWGUxQ23sBkCLQIS6wiTPpulk89Ryen3GN4S4sbUljMid7L0PnoJ7EuR%2FzEr98mdp4joX49fBdCptKCQaTnH6GMhMzJRXRWPD61iwpMbS7OP17R67K69d%2FSUI4ys8xKiRyDtJScX3%2B6KoBTxxx7ny1LzQeq0CIJ95F5SwDUN62rP%2B%2FHiFvbft6f4c4ejEzFgEaWskLAhw9cu1%2FS6129BT8RWw0VOPCBQ86x84a9%2Be334all4sFcXy0X2u%2F44pvsCMCaEEmG5UBE%2FQyytbkHvhTPcgKwKTVcK8R5O%2B%2FQrkV%2BwlPA1ke1M4EeWmxo%2F3qyW5kzwQipnaLuucLhC0VlmNZ0PCc6Fw%2BvqTPw5CkZ5DPr9VMzcNm%2FGsBg4JPHOMv6JiG3QfwRWp8CmC7nw7cAZUGvrwy2ISyeHMH%2BEkGl3DqdDN6xTQ8jZM3fRHbH9ggcZGEeW57TP%2FrXypSDf547b1RgA4lo7FJFAeRFRC19Q6t0jFKrg668%2FIiQHWQz%2F0vSY7HGtc%2BRIaHRbxM8%2FkoMySh7luz7u2kmgM3cmMdHjMqcTdvT0r%2BzHbVJh%2FgV2MJVRDc%2BzyQoqxonzsQi3dOaFcwksS1zQY6mAGDXvFb%2FlrFjI%2F2PVw7MuyOB6wl%2B8hEC9mPnkx0AqrZsNZbH5kk5KKZOIViAlsGIsWjMX1AVuyCVcfhEo4zdXry99Ak2XnZ1K6TbOaz5EUPzt9s1sd%2FRhxbz3DOEThFdIoN5zvo7oXFXKjP1%2FGUAyg4PxJ1Cm9Vlf8bdIUvFcFnb7c%2BpQMGsDBAhweaydVyNS5OMWpi5yziKQ%3D%3D&Expires=1772973087)

```python
# src/orchestorator_agent/agent.py

import anthropic  # or openai / boto3 for Bedrock

class MultiAgentOrchestrator:
    def __init__(self):
        # Your existing S3 init...
        self.llm = anthropic.Anthropic()  # or use boto3 for Bedrock Claude

    def _build_system_prompt(self) -> str:
        """Inject the agent registry into the LLM's context."""
        agents_info = "\n".join([
            f"- {agent_id}: {AGENT_DESCRIPTIONS[agent_id]}"
            for agent_id in KNOWN_AGENTS
        ])
        return f"""
You are an expert orchestrator agent. Your job is to decompose the user's
request and delegate each subtask to the right specialist agent.

Available agents:
{agents_info}

Rules:
1. Analyze the task and decide WHICH agents are needed and in what ORDER.
2. For each step, respond with JSON:
   {{"action": "call_agent", "agent_id": "<agent_id>", "instruction": "<what to do>"}}
3. After all agents respond, respond with:
   {{"action": "final_answer", "summary": "<synthesized result>"}}
4. Only call agents that are relevant. Not every task needs all 4 agents.
"""

    async def llm_run(
        self,
        user_task: str,
        context: dict,
        http_client: httpx.AsyncClient
    ) -> dict:
        """LLM-driven agentic loop."""
        messages = [{"role": "user", "content": user_task}]
        agent_results = {}

        for _ in range(10):  # max 10 LLM turns
            response = self.llm.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=self._build_system_prompt(),
                messages=messages,
            )

            llm_text = response.content[0].text
            messages.append({"role": "assistant", "content": llm_text})

            try:
                decision = json.loads(llm_text)
            except json.JSONDecodeError:
                break  # LLM gave free text, treat as final answer

            if decision["action"] == "final_answer":
                return {"summary": decision["summary"], "details": agent_results}

            elif decision["action"] == "call_agent":
                agent_id = decision["agent_id"]
                instruction = decision["instruction"]

                # Call the actual A2A agent
                result = await self.call_agent(
                    agent_id,
                    [
                        Part(root=TextPart(text=instruction)),
                        Part(root=DataPart(data=context))
                    ],
                    http_client
                )
                agent_results[agent_id] = result

                # Feed result BACK to LLM so it can decide next step
                messages.append({
                    "role": "user",
                    "content": f"Agent '{agent_id}' completed. Result: {json.dumps(result)[:2000]}"
                })

        return agent_results
```

***

## Add Agent Descriptions (for the Prompt)

Add this constant near your `KNOWN_AGENTS` dict: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/76332706/a223aa98-a338-4d7e-9f18-270bbe86666c/paste.txt?AWSAccessKeyId=ASIA2F3EMEYE6PGJWZPK&Signature=nwW%2BeQ3EFDzKxF5%2FNSY067P8KX0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEEwaCXVzLWVhc3QtMSJHMEUCIQDIi3NfiU9PlB34AGHK00ZqtfmAHf6iQKmNbZsiugerYQIgIgT1wdxNvF%2FkGJPpgIeofbYlMdFOA4zmtg4PvqN56S8q8wQIFRABGgw2OTk3NTMzMDk3MDUiDPKcMVnFOKav7zln3SrQBIOsasx36%2B37TIyWLG1MqOlEEGvcc%2BZCSqU37l3LbtAG6%2BzZiysWWvyAa9HaWN5RbOkTby0sngbocdA9IWxBHdTWaO7yUsBY0Dp5SZvtzPtpWr8lLeufuRWiRI8gA%2F%2BwUhmI3%2B7GV3X%2BM7wgrBcIxQOZbLdk6QSGZwb%2F5MHlDHtVeOPdGYRDtwAZjdDDIjdoKbWWGUxQ23sBkCLQIS6wiTPpulk89Ryen3GN4S4sbUljMid7L0PnoJ7EuR%2FzEr98mdp4joX49fBdCptKCQaTnH6GMhMzJRXRWPD61iwpMbS7OP17R67K69d%2FSUI4ys8xKiRyDtJScX3%2B6KoBTxxx7ny1LzQeq0CIJ95F5SwDUN62rP%2B%2FHiFvbft6f4c4ejEzFgEaWskLAhw9cu1%2FS6129BT8RWw0VOPCBQ86x84a9%2Be334all4sFcXy0X2u%2F44pvsCMCaEEmG5UBE%2FQyytbkHvhTPcgKwKTVcK8R5O%2B%2FQrkV%2BwlPA1ke1M4EeWmxo%2F3qyW5kzwQipnaLuucLhC0VlmNZ0PCc6Fw%2BvqTPw5CkZ5DPr9VMzcNm%2FGsBg4JPHOMv6JiG3QfwRWp8CmC7nw7cAZUGvrwy2ISyeHMH%2BEkGl3DqdDN6xTQ8jZM3fRHbH9ggcZGEeW57TP%2FrXypSDf547b1RgA4lo7FJFAeRFRC19Q6t0jFKrg668%2FIiQHWQz%2F0vSY7HGtc%2BRIaHRbxM8%2FkoMySh7luz7u2kmgM3cmMdHjMqcTdvT0r%2BzHbVJh%2FgV2MJVRDc%2BzyQoqxonzsQi3dOaFcwksS1zQY6mAGDXvFb%2FlrFjI%2F2PVw7MuyOB6wl%2B8hEC9mPnkx0AqrZsNZbH5kk5KKZOIViAlsGIsWjMX1AVuyCVcfhEo4zdXry99Ak2XnZ1K6TbOaz5EUPzt9s1sd%2FRhxbz3DOEThFdIoN5zvo7oXFXKjP1%2FGUAyg4PxJ1Cm9Vlf8bdIUvFcFnb7c%2BpQMGsDBAhweaydVyNS5OMWpi5yziKQ%3D%3D&Expires=1772973087)

```python
KNOWN_AGENTS = {
    "code-logic-agent": "http://localhost:8001",
    "research-agent":   "http://localhost:8003",
    "test-run-agent":   "http://localhost:8004",
    "validation-agent": "http://localhost:8005",
}

AGENT_DESCRIPTIONS = {
    "code-logic-agent": "Analyzes code structure, logic, and architecture",
    "research-agent":   "Searches codebase for patterns, functions, and dependencies",
    "test-run-agent":   "Generates and executes tests with coverage analysis",
    "validation-agent": "Runs security scans, finds secrets/vulnerabilities",
}
```

***

## Update Your Executor to Call the LLM Loop

In your existing `OrchestratorAgentExecutor.execute()`, replace the workflow branching with:

```python
async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
    updater = TaskUpdater(event_queue, context.task_id, context.context_id)
    await updater.submit()
    await updater.start_work()
    try:
        # Parse incoming message (your existing logic)
        code_text = ""
        s3_key = ""
        for part in context.message.parts:
            if isinstance(part.root, TextPart):
                code_text = part.root.text
            elif isinstance(part.root, DataPart):
                data = dict(part.root.data) or {}
                s3_key = data.get("projectArtifact", "")

        async with httpx.AsyncClient(timeout=300.0) as http_client:
            await orchestrator.discover_agents(http_client)

            # ✅ THIS IS WHERE THE LLM TAKES OVER
            results = await orchestrator.llm_run(
                user_task=code_text or f"Verify project at S3 key: {s3_key}",
                context={"s3key": s3_key, "code": code_text},
                http_client=http_client,
            )

        await updater.add_artifact(
            parts=[
                Part(root=TextPart(text=results.get("summary", "Done"))),
                Part(root=DataPart(data=results)),
            ],
            name="orchestration-results",
        )
        await updater.complete()
    except Exception as exc:
        await updater.failed(message=str(exc))
```

***

## If You're Using AWS Bedrock (given your stack)

Since you're on AWS, swap `anthropic.Anthropic()` for Bedrock:

```python
import boto3, json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

response = bedrock.invoke_model(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": self._build_system_prompt(),
        "messages": messages,
    })
)
result = json.loads(response["body"].read())
llm_text = result["content"][0]["text"]
```

***

## The Key Mental Model

```
User Request
     │
     ▼
  LLM (Claude via Bedrock)  ← system prompt with agent registry
     │
     │ decides: "call validation-agent first"
     ▼
23% > use the bedrock aws llm antropic. and use the propmt.txt for orch agent and implement the below plan ```I can see your actual codebase! Your current orchestrator **has no LLM inside it** — it's a pure rule-based router that calls agents sequentially in hardcoded order. Here's exactly what's missing and how to wire an LLM into **your specific `OrchestratorAgentExecutor`**.

***

## What Your Current Orchestrator Does

Right now your `OrchestratorAgentExecutor.execute()` calls agents in a **hardcoded sequence**: code-logic → research → validation → tests. There's no LLM deciding what to do — it's just `if workflow == "verification": run these 4 agents`. That's a scripted pipeline, not an intelligent orchestrator. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/76332706/a223aa98-a338-4d7e-9f18-270bbe86666c/paste.txt?AWSAccessKeyId=ASIA2F3EMEYE6PGJWZPK&Signature=nwW%2BeQ3EFDzKxF5%2FNSY067P8KX0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEEwaCXVzLWVhc3QtMSJHMEUCIQDIi3NfiU9PlB34AGHK00ZqtfmAHf6iQKmNbZsiugerYQIgIgT1wdxNvF%2FkGJPpgIeofbYlMdFOA4zmtg4PvqN56S8q8wQIFRABGgw2OTk3NTMzMDk3MDUiDPKcMVnFOKav7zln3SrQBIOsasx36%2B37TIyWLG1MqOlEEGvcc%2BZCSqU37l3LbtAG6%2BzZiysWWvyAa9HaWN5RbOkTby0sngbocdA9IWxBHdTWaO7yUsBY0Dp5SZvtzPtpWr8lLeufuRWiRI8gA%2F%2BwUhmI3%2B7GV3X%2BM7wgrBcIxQOZbLdk6QSGZwb%2F5MHlDHtVeOPdGYRDtwAZjdDDIjdoKbWWGUxQ23sBkCLQIS6wiTPpulk89Ryen3GN4S4sbUljMid7L0PnoJ7EuR%2FzEr98mdp4joX49fBdCptKCQaTnH6GMhMzJRXRWPD61iwpMbS7OP17R67K69d%2FSUI4ys8xKiRyDtJScX3%2B6KoBTxxx7ny1LzQeq0CIJ95F5SwDUN62rP%2B%2FHiFvbft6f4c4ejEzFgEaWskLAhw9cu1%2FS6129BT8RWw0VOPCBQ86x84a9%2Be334all4sFcXy0X2u%2F44pvsCMCaEEmG5UBE%2FQyytbkHvhTPcgKwKTVcK8R5O%2B%2FQrkV%2BwlPA1ke1M4EeWmxo%2F3qyW5kzwQipnaLuucLhC0VlmNZ0PCc6Fw%2BvqTPw5CkZ5DPr9VMzcNm%2FGsBg4JPHOMv6JiG3QfwRWp8CmC7nw7cAZUGvrwy2ISyeHMH%2BEkGl3DqdDN6xTQ8jZM3fRHbH9ggcZGEeW57TP%2FrXypSDf547b1RgA4lo7FJFAeRFRC19Q6t0jFKrg668%2FIiQHWQz%2F0vSY7HGtc%2BRIaHRbxM8%2FkoMySh7luz7u2kmgM3cmMdHjMqcTdvT0r%2BzHbVJh%2FgV2MJVRDc%2BzyQoqxonzsQi3dOaFcwksS1zQY6mAGDXvFb%2FlrFjI%2F2PVw7MuyOB6wl%2B8hEC9mPnkx0AqrZsNZbH5kk5KKZOIViAlsGIsWjMX1AVuyCVcfhEo4zdXry99Ak2XnZ1K6TbOaz5EUPzt9s1sd%2FRhxbz3DOEThFdIoN5zvo7oXFXKjP1%2FGUAyg4PxJ1Cm9Vlf8bdIUvFcFnb7c%2BpQMGsDBAhweaydVyNS5OMWpi5yziKQ%3D%3D&Expires=1772973087)

***

## Where to Inject the LLM in Your Code

The LLM goes inside `MultiAgentOrchestrator` and replaces the hardcoded `runfullanalysis` / `handleverificationworkflow` logic. Here's the pattern for your existing file structure: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/76332706/a223aa98-a338-4d7e-9f18-270bbe86666c/paste.txt?AWSAccessKeyId=ASIA2F3EMEYE6PGJWZPK&Signature=nwW%2BeQ3EFDzKxF5%2FNSY067P8KX0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEEwaCXVzLWVhc3QtMSJHMEUCIQDIi3NfiU9PlB34AGHK00ZqtfmAHf6iQKmNbZsiugerYQIgIgT1wdxNvF%2FkGJPpgIeofbYlMdFOA4zmtg4PvqN56S8q8wQIFRABGgw2OTk3NTMzMDk3MDUiDPKcMVnFOKav7zln3SrQBIOsasx36%2B37TIyWLG1MqOlEEGvcc%2BZCSqU37l3LbtAG6%2BzZiysWWvyAa9HaWN5RbOkTby0sngbocdA9IWxBHdTWaO7yUsBY0Dp5SZvtzPtpWr8lLeufuRWiRI8gA%2F%2BwUhmI3%2B7GV3X%2BM7wgrBcIxQOZbLdk6QSGZwb%2F5MHlDHtVeOPdGYRDtwAZjdDDIjdoKbWWGUxQ23sBkCLQIS6wiTPpulk89Ryen3GN4S4sbUljMid7L0PnoJ7EuR%2FzEr98mdp4joX49fBdCptKCQaTnH6GMhMzJRXRWPD61iwpMbS7OP17R67K69d%2FSUI4ys8xKiRyDtJScX3%2B6KoBTxxx7ny1LzQeq0CIJ95F5SwDUN62rP%2B%2FHiFvbft6f4c4ejEzFgEaWskLAhw9cu1%2FS6129BT8RWw0VOPCBQ86x84a9%2Be334all4sFcXy0X2u%2F44pvsCMCaEEmG5UBE%2FQyytbkHvhTPcgKwKTVcK8R5O%2B%2FQrkV%2BwlPA1ke1M4EeWmxo%2F3qyW5kzwQipnaLuucLhC0VlmNZ0PCc6Fw%2BvqTPw5CkZ5DPr9VMzcNm%2FGsBg4JPHOMv6JiG3QfwRWp8CmC7nw7cAZUGvrwy2ISyeHMH%2BEkGl3DqdDN6xTQ8jZM3fRHbH9ggcZGEeW57TP%2FrXypSDf547b1RgA4lo7FJFAeRFRC19Q6t0jFKrg668%2FIiQHWQz%2F0vSY7HGtc%2BRIaHRbxM8%2FkoMySh7luz7u2kmgM3cmMdHjMqcTdvT0r%2BzHbVJh%2FgV2MJVRDc%2BzyQoqxonzsQi3dOaFcwksS1zQY6mAGDXvFb%2FlrFjI%2F2PVw7MuyOB6wl%2B8hEC9mPnkx0AqrZsNZbH5kk5KKZOIViAlsGIsWjMX1AVuyCVcfhEo4zdXry99Ak2XnZ1K6TbOaz5EUPzt9s1sd%2FRhxbz3DOEThFdIoN5zvo7oXFXKjP1%2FGUAyg4PxJ1Cm9Vlf8bdIUvFcFnb7c%2BpQMGsDBAhweaydVyNS5OMWpi5yziKQ%3D%3D&Expires=1772973087)

```python
# src/orchestorator_agent/agent.py

import anthropic  # or openai / boto3 for Bedrock

class MultiAgentOrchestrator:
    def __init__(self):
        # Your existing S3 init...
        self.llm = anthropic.Anthropic()  # or use boto3 for Bedrock Claude

    def _build_system_prompt(self) -> str:
        """Inject the agent registry into the LLM's context."""
        agents_info = "\n".join([
            f"- {agent_id}: {AGENT_DESCRIPTIONS[agent_id]}"
            for agent_id in KNOWN_AGENTS
        ])
        return f"""
You are an expert orchestrator agent. Your job is to decompose the user's
request and delegate each subtask to the right specialist agent.

Available agents:
{agents_info}

Rules:
1. Analyze the task and decide WHICH agents are needed and in what ORDER.
2. For each step, respond with JSON:
   {{"action": "call_agent", "agent_id": "<agent_id>", "instruction": "<what to do>"}}
3. After all agents respond, respond with:
   {{"action": "final_answer", "summary": "<synthesized result>"}}
4. Only call agents that are relevant. Not every task needs all 4 agents.
"""

    async def llm_run(
        self,
        user_task: str,
        context: dict,
        http_client: httpx.AsyncClient
    ) -> dict:
        """LLM-driven agentic loop."""
        messages = [{"role": "user", "content": user_task}]
        agent_results = {}

        for _ in range(10):  # max 10 LLM turns
            response = self.llm.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=self._build_system_prompt(),
                messages=messages,
            )

            llm_text = response.content[0].text
            messages.append({"role": "assistant", "content": llm_text})

            try:
                decision = json.loads(llm_text)
            except json.JSONDecodeError:
                break  # LLM gave free text, treat as final answer

            if decision["action"] == "final_answer":
                return {"summary": decision["summary"], "details": agent_results}

            elif decision["action"] == "call_agent":
                agent_id = decision["agent_id"]
                instruction = decision["instruction"]

                # Call the actual A2A agent
                result = await self.call_agent(
                    agent_id,
                    [
                        Part(root=TextPart(text=instruction)),
                        Part(root=DataPart(data=context))
                    ],
                    http_client
                )
                agent_results[agent_id] = result

                # Feed result BACK to LLM so it can decide next step
                messages.append({
                    "role": "user",
                    "content": f"Agent '{agent_id}' completed. Result: {json.dumps(result)[:2000]}"
                })

        return agent_results
```

***

## Add Agent Descriptions (for the Prompt)

Add this constant near your `KNOWN_AGENTS` dict: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/76332706/a223aa98-a338-4d7e-9f18-270bbe86666c/paste.txt?AWSAccessKeyId=ASIA2F3EMEYE6PGJWZPK&Signature=nwW%2BeQ3EFDzKxF5%2FNSY067P8KX0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEEwaCXVzLWVhc3QtMSJHMEUCIQDIi3NfiU9PlB34AGHK00ZqtfmAHf6iQKmNbZsiugerYQIgIgT1wdxNvF%2FkGJPpgIeofbYlMdFOA4zmtg4PvqN56S8q8wQIFRABGgw2OTk3NTMzMDk3MDUiDPKcMVnFOKav7zln3SrQBIOsasx36%2B37TIyWLG1MqOlEEGvcc%2BZCSqU37l3LbtAG6%2BzZiysWWvyAa9HaWN5RbOkTby0sngbocdA9IWxBHdTWaO7yUsBY0Dp5SZvtzPtpWr8lLeufuRWiRI8gA%2F%2BwUhmI3%2B7GV3X%2BM7wgrBcIxQOZbLdk6QSGZwb%2F5MHlDHtVeOPdGYRDtwAZjdDDIjdoKbWWGUxQ23sBkCLQIS6wiTPpulk89Ryen3GN4S4sbUljMid7L0PnoJ7EuR%2FzEr98mdp4joX49fBdCptKCQaTnH6GMhMzJRXRWPD61iwpMbS7OP17R67K69d%2FSUI4ys8xKiRyDtJScX3%2B6KoBTxxx7ny1LzQeq0CIJ95F5SwDUN62rP%2B%2FHiFvbft6f4c4ejEzFgEaWskLAhw9cu1%2FS6129BT8RWw0VOPCBQ86x84a9%2Be334all4sFcXy0X2u%2F44pvsCMCaEEmG5UBE%2FQyytbkHvhTPcgKwKTVcK8R5O%2B%2FQrkV%2BwlPA1ke1M4EeWmxo%2F3qyW5kzwQipnaLuucLhC0VlmNZ0PCc6Fw%2BvqTPw5CkZ5DPr9VMzcNm%2FGsBg4JPHOMv6JiG3QfwRWp8CmC7nw7cAZUGvrwy2ISyeHMH%2BEkGl3DqdDN6xTQ8jZM3fRHbH9ggcZGEeW57TP%2FrXypSDf547b1RgA4lo7FJFAeRFRC19Q6t0jFKrg668%2FIiQHWQz%2F0vSY7HGtc%2BRIaHRbxM8%2FkoMySh7luz7u2kmgM3cmMdHjMqcTdvT0r%2BzHbVJh%2FgV2MJVRDc%2BzyQoqxonzsQi3dOaFcwksS1zQY6mAGDXvFb%2FlrFjI%2F2PVw7MuyOB6wl%2B8hEC9mPnkx0AqrZsNZbH5kk5KKZOIViAlsGIsWjMX1AVuyCVcfhEo4zdXry99Ak2XnZ1K6TbOaz5EUPzt9s1sd%2FRhxbz3DOEThFdIoN5zvo7oXFXKjP1%2FGUAyg4PxJ1Cm9Vlf8bdIUvFcFnb7c%2BpQMGsDBAhweaydVyNS5OMWpi5yziKQ%3D%3D&Expires=1772973087)

```python
KNOWN_AGENTS = {
    "code-logic-agent": "http://localhost:8001",
    "research-agent":   "http://localhost:8003",
    "test-run-agent":   "http://localhost:8004",
    "validation-agent": "http://localhost:8005",
}

AGENT_DESCRIPTIONS = {
    "code-logic-agent": "Analyzes code structure, logic, and architecture",
    "research-agent":   "Searches codebase for patterns, functions, and dependencies",
    "test-run-agent":   "Generates and executes tests with coverage analysis",
    "validation-agent": "Runs security scans, finds secrets/vulnerabilities",
}
```

***

## Update Your Executor to Call the LLM Loop

In your existing `OrchestratorAgentExecutor.execute()`, replace the workflow branching with:

```python
async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
    updater = TaskUpdater(event_queue, context.task_id, context.context_id)
    await updater.submit()
    await updater.start_work()
    try:
        # Parse incoming message (your existing logic)
        code_text = ""
        s3_key = ""
        for part in context.message.parts:
            if isinstance(part.root, TextPart):
                code_text = part.root.text
            elif isinstance(part.root, DataPart):
                data = dict(part.root.data) or {}
                s3_key = data.get("projectArtifact", "")

        async with httpx.AsyncClient(timeout=300.0) as http_client:
            await orchestrator.discover_agents(http_client)

            # ✅ THIS IS WHERE THE LLM TAKES OVER
            results = await orchestrator.llm_run(
                user_task=code_text or f"Verify project at S3 key: {s3_key}",
                context={"s3key": s3_key, "code": code_text},
                http_client=http_client,
            )

        await updater.add_artifact(
            parts=[
                Part(root=TextPart(text=results.get("summary", "Done"))),
                Part(root=DataPart(data=results)),
            ],
            name="orchestration-results",
        )
        await updater.complete()
    except Exception as exc:
        await updater.failed(message=str(exc))
```

***

## If You're Using AWS Bedrock (given your stack)

Since you're on AWS, swap `anthropic.Anthropic()` for Bedrock:

```python
import boto3, json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

response = bedrock.invoke_model(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": self._build_system_prompt(),
        "messages": messages,
    })
)
result = json.loads(response["body"].read())
llm_text = result["content"][0]["text"]
```

***

## The Key Mental Model

```
User Request
     │
     ▼
  LLM (Claude via Bedrock)  ← system prompt with agent registry
     │
     │ decides: "call validation-agent first"
     ▼
  A2A call → validation-agent → result
23% > use the bedrock aws llm antropic. and use the propmt.txt for orch agent and implement the below plan ```I can see your actual codebase! Your current orchestrator **has no LLM inside it** — it's a pure rule-based router that calls agents sequentially in hardcoded order. Here's exactly what's missing and how to wire an LLM into **your specific `OrchestratorAgentExecutor`**.

***

## What Your Current Orchestrator Does

Right now your `OrchestratorAgentExecutor.execute()` calls agents in a **hardcoded sequence**: code-logic → research → validation → tests. There's no LLM deciding what to do — it's just `if workflow == "verification": run these 4 agents`. That's a scripted pipeline, not an intelligent orchestrator. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/76332706/a223aa98-a338-4d7e-9f18-270bbe86666c/paste.txt?AWSAccessKeyId=ASIA2F3EMEYE6PGJWZPK&Signature=nwW%2BeQ3EFDzKxF5%2FNSY067P8KX0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEEwaCXVzLWVhc3QtMSJHMEUCIQDIi3NfiU9PlB34AGHK00ZqtfmAHf6iQKmNbZsiugerYQIgIgT1wdxNvF%2FkGJPpgIeofbYlMdFOA4zmtg4PvqN56S8q8wQIFRABGgw2OTk3NTMzMDk3MDUiDPKcMVnFOKav7zln3SrQBIOsasx36%2B37TIyWLG1MqOlEEGvcc%2BZCSqU37l3LbtAG6%2BzZiysWWvyAa9HaWN5RbOkTby0sngbocdA9IWxBHdTWaO7yUsBY0Dp5SZvtzPtpWr8lLeufuRWiRI8gA%2F%2BwUhmI3%2B7GV3X%2BM7wgrBcIxQOZbLdk6QSGZwb%2F5MHlDHtVeOPdGYRDtwAZjdDDIjdoKbWWGUxQ23sBkCLQIS6wiTPpulk89Ryen3GN4S4sbUljMid7L0PnoJ7EuR%2FzEr98mdp4joX49fBdCptKCQaTnH6GMhMzJRXRWPD61iwpMbS7OP17R67K69d%2FSUI4ys8xKiRyDtJScX3%2B6KoBTxxx7ny1LzQeq0CIJ95F5SwDUN62rP%2B%2FHiFvbft6f4c4ejEzFgEaWskLAhw9cu1%2FS6129BT8RWw0VOPCBQ86x84a9%2Be334all4sFcXy0X2u%2F44pvsCMCaEEmG5UBE%2FQyytbkHvhTPcgKwKTVcK8R5O%2B%2FQrkV%2BwlPA1ke1M4EeWmxo%2F3qyW5kzwQipnaLuucLhC0VlmNZ0PCc6Fw%2BvqTPw5CkZ5DPr9VMzcNm%2FGsBg4JPHOMv6JiG3QfwRWp8CmC7nw7cAZUGvrwy2ISyeHMH%2BEkGl3DqdDN6xTQ8jZM3fRHbH9ggcZGEeW57TP%2FrXypSDf547b1RgA4lo7FJFAeRFRC19Q6t0jFKrg668%2FIiQHWQz%2F0vSY7HGtc%2BRIaHRbxM8%2FkoMySh7luz7u2kmgM3cmMdHjMqcTdvT0r%2BzHbVJh%2FgV2MJVRDc%2BzyQoqxonzsQi3dOaFcwksS1zQY6mAGDXvFb%2FlrFjI%2F2PVw7MuyOB6wl%2B8hEC9mPnkx0AqrZsNZbH5kk5KKZOIViAlsGIsWjMX1AVuyCVcfhEo4zdXry99Ak2XnZ1K6TbOaz5EUPzt9s1sd%2FRhxbz3DOEThFdIoN5zvo7oXFXKjP1%2FGUAyg4PxJ1Cm9Vlf8bdIUvFcFnb7c%2BpQMGsDBAhweaydVyNS5OMWpi5yziKQ%3D%3D&Expires=1772973087)

***

## Where to Inject the LLM in Your Code

The LLM goes inside `MultiAgentOrchestrator` and replaces the hardcoded `runfullanalysis` / `handleverificationworkflow` logic. Here's the pattern for your existing file structure: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/76332706/a223aa98-a338-4d7e-9f18-270bbe86666c/paste.txt?AWSAccessKeyId=ASIA2F3EMEYE6PGJWZPK&Signature=nwW%2BeQ3EFDzKxF5%2FNSY067P8KX0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEEwaCXVzLWVhc3QtMSJHMEUCIQDIi3NfiU9PlB34AGHK00ZqtfmAHf6iQKmNbZsiugerYQIgIgT1wdxNvF%2FkGJPpgIeofbYlMdFOA4zmtg4PvqN56S8q8wQIFRABGgw2OTk3NTMzMDk3MDUiDPKcMVnFOKav7zln3SrQBIOsasx36%2B37TIyWLG1MqOlEEGvcc%2BZCSqU37l3LbtAG6%2BzZiysWWvyAa9HaWN5RbOkTby0sngbocdA9IWxBHdTWaO7yUsBY0Dp5SZvtzPtpWr8lLeufuRWiRI8gA%2F%2BwUhmI3%2B7GV3X%2BM7wgrBcIxQOZbLdk6QSGZwb%2F5MHlDHtVeOPdGYRDtwAZjdDDIjdoKbWWGUxQ23sBkCLQIS6wiTPpulk89Ryen3GN4S4sbUljMid7L0PnoJ7EuR%2FzEr98mdp4joX49fBdCptKCQaTnH6GMhMzJRXRWPD61iwpMbS7OP17R67K69d%2FSUI4ys8xKiRyDtJScX3%2B6KoBTxxx7ny1LzQeq0CIJ95F5SwDUN62rP%2B%2FHiFvbft6f4c4ejEzFgEaWskLAhw9cu1%2FS6129BT8RWw0VOPCBQ86x84a9%2Be334all4sFcXy0X2u%2F44pvsCMCaEEmG5UBE%2FQyytbkHvhTPcgKwKTVcK8R5O%2B%2FQrkV%2BwlPA1ke1M4EeWmxo%2F3qyW5kzwQipnaLuucLhC0VlmNZ0PCc6Fw%2BvqTPw5CkZ5DPr9VMzcNm%2FGsBg4JPHOMv6JiG3QfwRWp8CmC7nw7cAZUGvrwy2ISyeHMH%2BEkGl3DqdDN6xTQ8jZM3fRHbH9ggcZGEeW57TP%2FrXypSDf547b1RgA4lo7FJFAeRFRC19Q6t0jFKrg668%2FIiQHWQz%2F0vSY7HGtc%2BRIaHRbxM8%2FkoMySh7luz7u2kmgM3cmMdHjMqcTdvT0r%2BzHbVJh%2FgV2MJVRDc%2BzyQoqxonzsQi3dOaFcwksS1zQY6mAGDXvFb%2FlrFjI%2F2PVw7MuyOB6wl%2B8hEC9mPnkx0AqrZsNZbH5kk5KKZOIViAlsGIsWjMX1AVuyCVcfhEo4zdXry99Ak2XnZ1K6TbOaz5EUPzt9s1sd%2FRhxbz3DOEThFdIoN5zvo7oXFXKjP1%2FGUAyg4PxJ1Cm9Vlf8bdIUvFcFnb7c%2BpQMGsDBAhweaydVyNS5OMWpi5yziKQ%3D%3D&Expires=1772973087)

```python
# src/orchestorator_agent/agent.py

import anthropic  # or openai / boto3 for Bedrock

class MultiAgentOrchestrator:
    def __init__(self):
        # Your existing S3 init...
        self.llm = anthropic.Anthropic()  # or use boto3 for Bedrock Claude

    def _build_system_prompt(self) -> str:
        """Inject the agent registry into the LLM's context."""
        agents_info = "\n".join([
            f"- {agent_id}: {AGENT_DESCRIPTIONS[agent_id]}"
            for agent_id in KNOWN_AGENTS
        ])
        return f"""
You are an expert orchestrator agent. Your job is to decompose the user's
request and delegate each subtask to the right specialist agent.

Available agents:
{agents_info}

Rules:
1. Analyze the task and decide WHICH agents are needed and in what ORDER.
2. For each step, respond with JSON:
   {{"action": "call_agent", "agent_id": "<agent_id>", "instruction": "<what to do>"}}
3. After all agents respond, respond with:
   {{"action": "final_answer", "summary": "<synthesized result>"}}
4. Only call agents that are relevant. Not every task needs all 4 agents.
"""

    async def llm_run(
        self,
        user_task: str,
        context: dict,
        http_client: httpx.AsyncClient
    ) -> dict:
        """LLM-driven agentic loop."""
        messages = [{"role": "user", "content": user_task}]
        agent_results = {}

        for _ in range(10):  # max 10 LLM turns
            response = self.llm.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=self._build_system_prompt(),
                messages=messages,
            )

            llm_text = response.content[0].text
            messages.append({"role": "assistant", "content": llm_text})

            try:
                decision = json.loads(llm_text)
            except json.JSONDecodeError:
                break  # LLM gave free text, treat as final answer

            if decision["action"] == "final_answer":
                return {"summary": decision["summary"], "details": agent_results}

            elif decision["action"] == "call_agent":
                agent_id = decision["agent_id"]
                instruction = decision["instruction"]

                # Call the actual A2A agent
                result = await self.call_agent(
                    agent_id,
                    [
                        Part(root=TextPart(text=instruction)),
                        Part(root=DataPart(data=context))
                    ],
                    http_client
                )
                agent_results[agent_id] = result

                # Feed result BACK to LLM so it can decide next step
                messages.append({
                    "role": "user",
                    "content": f"Agent '{agent_id}' completed. Result: {json.dumps(result)[:2000]}"
                })

        return agent_results
```

***

## Add Agent Descriptions (for the Prompt)

Add this constant near your `KNOWN_AGENTS` dict: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/76332706/a223aa98-a338-4d7e-9f18-270bbe86666c/paste.txt?AWSAccessKeyId=ASIA2F3EMEYE6PGJWZPK&Signature=nwW%2BeQ3EFDzKxF5%2FNSY067P8KX0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEEwaCXVzLWVhc3QtMSJHMEUCIQDIi3NfiU9PlB34AGHK00ZqtfmAHf6iQKmNbZsiugerYQIgIgT1wdxNvF%2FkGJPpgIeofbYlMdFOA4zmtg4PvqN56S8q8wQIFRABGgw2OTk3NTMzMDk3MDUiDPKcMVnFOKav7zln3SrQBIOsasx36%2B37TIyWLG1MqOlEEGvcc%2BZCSqU37l3LbtAG6%2BzZiysWWvyAa9HaWN5RbOkTby0sngbocdA9IWxBHdTWaO7yUsBY0Dp5SZvtzPtpWr8lLeufuRWiRI8gA%2F%2BwUhmI3%2B7GV3X%2BM7wgrBcIxQOZbLdk6QSGZwb%2F5MHlDHtVeOPdGYRDtwAZjdDDIjdoKbWWGUxQ23sBkCLQIS6wiTPpulk89Ryen3GN4S4sbUljMid7L0PnoJ7EuR%2FzEr98mdp4joX49fBdCptKCQaTnH6GMhMzJRXRWPD61iwpMbS7OP17R67K69d%2FSUI4ys8xKiRyDtJScX3%2B6KoBTxxx7ny1LzQeq0CIJ95F5SwDUN62rP%2B%2FHiFvbft6f4c4ejEzFgEaWskLAhw9cu1%2FS6129BT8RWw0VOPCBQ86x84a9%2Be334all4sFcXy0X2u%2F44pvsCMCaEEmG5UBE%2FQyytbkHvhTPcgKwKTVcK8R5O%2B%2FQrkV%2BwlPA1ke1M4EeWmxo%2F3qyW5kzwQipnaLuucLhC0VlmNZ0PCc6Fw%2BvqTPw5CkZ5DPr9VMzcNm%2FGsBg4JPHOMv6JiG3QfwRWp8CmC7nw7cAZUGvrwy2ISyeHMH%2BEkGl3DqdDN6xTQ8jZM3fRHbH9ggcZGEeW57TP%2FrXypSDf547b1RgA4lo7FJFAeRFRC19Q6t0jFKrg668%2FIiQHWQz%2F0vSY7HGtc%2BRIaHRbxM8%2FkoMySh7luz7u2kmgM3cmMdHjMqcTdvT0r%2BzHbVJh%2FgV2MJVRDc%2BzyQoqxonzsQi3dOaFcwksS1zQY6mAGDXvFb%2FlrFjI%2F2PVw7MuyOB6wl%2B8hEC9mPnkx0AqrZsNZbH5kk5KKZOIViAlsGIsWjMX1AVuyCVcfhEo4zdXry99Ak2XnZ1K6TbOaz5EUPzt9s1sd%2FRhxbz3DOEThFdIoN5zvo7oXFXKjP1%2FGUAyg4PxJ1Cm9Vlf8bdIUvFcFnb7c%2BpQMGsDBAhweaydVyNS5OMWpi5yziKQ%3D%3D&Expires=1772973087)

```python
KNOWN_AGENTS = {
    "code-logic-agent": "http://localhost:8001",
    "research-agent":   "http://localhost:8003",
    "test-run-agent":   "http://localhost:8004",
    "validation-agent": "http://localhost:8005",
}

AGENT_DESCRIPTIONS = {
    "code-logic-agent": "Analyzes code structure, logic, and architecture",
    "research-agent":   "Searches codebase for patterns, functions, and dependencies",
    "test-run-agent":   "Generates and executes tests with coverage analysis",
    "validation-agent": "Runs security scans, finds secrets/vulnerabilities",
}
```

***

## Update Your Executor to Call the LLM Loop

In your existing `OrchestratorAgentExecutor.execute()`, replace the workflow branching with:

```python
async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
    updater = TaskUpdater(event_queue, context.task_id, context.context_id)
    await updater.submit()
    await updater.start_work()
    try:
        # Parse incoming message (your existing logic)
        code_text = ""
        s3_key = ""
        for part in context.message.parts:
            if isinstance(part.root, TextPart):
                code_text = part.root.text
            elif isinstance(part.root, DataPart):
                data = dict(part.root.data) or {}
                s3_key = data.get("projectArtifact", "")

        async with httpx.AsyncClient(timeout=300.0) as http_client:
            await orchestrator.discover_agents(http_client)

            # ✅ THIS IS WHERE THE LLM TAKES OVER
            results = await orchestrator.llm_run(
                user_task=code_text or f"Verify project at S3 key: {s3_key}",
                context={"s3key": s3_key, "code": code_text},
                http_client=http_client,
            )

        await updater.add_artifact(
            parts=[
                Part(root=TextPart(text=results.get("summary", "Done"))),
                Part(root=DataPart(data=results)),
            ],
            name="orchestration-results",
        )
        await updater.complete()
    except Exception as exc:
        await updater.failed(message=str(exc))
```

***

## If You're Using AWS Bedrock (given your stack)

Since you're on AWS, swap `anthropic.Anthropic()` for Bedrock:

```python
import boto3, json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

response = bedrock.invoke_model(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": self._build_system_prompt(),
        "messages": messages,
    })
)
result = json.loads(response["body"].read())
llm_text = result["content"][0]["text"]
```

***

## The Key Mental Model

```
User Request
     │
     ▼
  LLM (Claude via Bedrock)  ← system prompt with agent registry
     │
     │ decides: "call validation-agent first"
     ▼
  A2A call → validation-agent → result
     │
     └── result fed BACK into LLM messages
     │
     │ decides: "now call test-run-agent"
     ▼
  A2A call → test-run-agent → result
     │
     │ decides: "I have enough, final_answer"
     ▼
  Summary returned to user
```

The LLM **drives the loop** — it sees what agents returned and decides what to do next, rather than your current hardcoded 4-agent sequence. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/76332706/a223aa98-a338-4d7e-9f18-270bbe86666c/paste.txt?AWSAccessKeyId=ASIA2F3EMEYE6PGJWZPK&Signature=nwW%2BeQ3EFDzKxF5%2FNSY067P8KX0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEEwaCXVzLWVhc3QtMSJHMEUCIQDIi3NfiU9PlB34AGHK00ZqtfmAHf6iQKmNbZsiugerYQIgIgT1wdxNvF%2FkGJPpgIeofbYlMdFOA4zmtg4PvqN56S8q8wQIFRABGgw2OTk3NTMzMDk3MDUiDPKcMVnFOKav7zln3SrQBIOsasx36%2B37TIyWLG1MqOlEEGvcc%2BZCSqU37l3LbtAG6%2BzZiysWWvyAa9HaWN5RbOkTby0sngbocdA9IWxBHdTWaO7yUsBY0Dp5SZvtzPtpWr8lLeufuRWiRI8gA%2F%2BwUhmI3%2B7GV3X%2BM7wgrBcIxQOZbLdk6QSGZwb%2F5MHlDHtVeOPdGYRDtwAZjdDDIjdoKbWWGUxQ23sBkCLQIS6wiTPpulk89Ryen3GN4S4sbUljMid7L0PnoJ7EuR%2FzEr98mdp4joX49fBdCptKCQaTnH6GMhMzJRXRWPD61iwpMbS7OP17R67K69d%2FSUI4ys8xKiRyDtJScX3%2B6KoBTxxx7ny1LzQeq0CIJ95F5SwDUN62rP%2B%2FHiFvbft6f4c4ejEzFgEaWskLAhw9cu1%2FS6129BT8RWw0VOPCBQ86x84a9%2Be334all4sFcXy0X2u%2F44pvsCMCaEEmG5UBE%2FQyytbkHvhTPcgKwKTVcK8R5O%2B%2FQrkV%2BwlPA1ke1M4EeWmxo%2F3qyW5kzwQipnaLuucLhC0VlmNZ0PCc6Fw%2BvqTPw5CkZ5DPr9VMzcNm%2FGsBg4JPHOMv6JiG3QfwRWp8CmC7nw7cAZUGvrwy2ISyeHMH%2BEkGl3DqdDN6xTQ8jZM3fRHbH9ggcZGEeW57TP%2FrXypSDf547b1RgA4lo7FJFAeRFRC19Q6t0jFKrg668%2FIiQHWQz%2F0vSY7HGtc%2BRIaHRbxM8%2FkoMySh7luz7u2kmgM3cmMdHjMqcTdvT0r%2BzHbVJh%2FgV2MJVRDc%2BzyQoqxonzsQi3dOaFcwksS1zQY6mAGDXvFb%2FlrFjI%2F2PVw7MuyOB6wl%2B8hEC9mPnkx0AqrZsNZbH5kk5KKZOIViAlsGIsWjMX1AVuyCVcfhEo4zdXry99Ak2XnZ1K6TbOaz5EUPzt9s1sd%2FRhxbz3DOEThFdIoN5zvo7oXFXKjP1%2FGUAyg4PxJ1Cm9Vlf8bdIUvFcFnb7c%2BpQMGsDBAhweaydVyNS5OMWpi5yziKQ%3D%3D&Expires=1772973087)``