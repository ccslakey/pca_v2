// Prototype `sidecar` variant: CopilotKit's Node runtime in front of Django.
// The model and loop live here; data comes from Django's /api/copilot/tool/.
import { createServer } from "node:http";
import { AbstractAgent, EventType } from "@ag-ui/client";
import {
  BuiltInAgent,
  CopilotRuntime,
  convertJsonSchemaToZodSchema,
  defineTool,
} from "@copilotkit/runtime/v2";
import { createCopilotNodeListener } from "@copilotkit/runtime/v2/node";
import { Observable } from "rxjs";

const DJANGO = process.env.DJANGO_URL ?? "http://localhost:8000";
const PORT = Number(process.env.COPILOT_PORT ?? 4000);
const MODEL = process.env.COPILOT_MODEL ?? "claude-haiku-5-5";

async function loadContract() {
  for (let attempt = 0; ; attempt++) {
    try {
      const res = await fetch(`${DJANGO}/api/copilot/tools/`);
      if (res.ok) return await res.json();
    } catch {}
    if (attempt === 0) console.log(`waiting for Django at ${DJANGO} ...`);
    await new Promise((r) => setTimeout(r, 1000));
  }
}

async function callDjango(name, args) {
  const res = await fetch(`${DJANGO}/api/copilot/tool/`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name, args }),
  });
  return await res.json();
}

class UnavailableAgent extends AbstractAgent {
  run(input) {
    return new Observable((sub) => {
      const { threadId, runId } = input;
      const messageId = crypto.randomUUID();
      sub.next({ type: EventType.RUN_STARTED, threadId, runId });
      sub.next({ type: EventType.TEXT_MESSAGE_START, messageId, role: "assistant" });
      sub.next({
        type: EventType.TEXT_MESSAGE_CONTENT,
        messageId,
        delta: "Chat is unavailable: the sidecar has no ANTHROPIC_API_KEY configured.",
      });
      sub.next({ type: EventType.TEXT_MESSAGE_END, messageId });
      sub.next({ type: EventType.RUN_FINISHED, threadId, runId });
      sub.complete();
    });
  }
}

const { tools, system } = await loadContract();
const agent = process.env.ANTHROPIC_API_KEY
  ? new BuiltInAgent({
      model: `anthropic:${MODEL}`,
      prompt: system,
      maxSteps: 8,
      maxOutputTokens: 2048,
      providerOptions: { anthropic: { effort: "low" } },
      tools: tools.map((t) =>
        defineTool({
          name: t.name,
          description: t.description,
          parameters: convertJsonSchemaToZodSchema(t.input_schema, true),
          execute: (args) => callDjango(t.name, args),
        }),
      ),
    })
  : new UnavailableAgent();

const runtime = new CopilotRuntime({ agents: { default: agent } });
createServer(createCopilotNodeListener({ runtime, basePath: "/api/copilotkit" })).listen(PORT, () =>
  console.log(`copilot sidecar on :${PORT} (model ${MODEL}, ${tools.length} tools from ${DJANGO})`),
);
