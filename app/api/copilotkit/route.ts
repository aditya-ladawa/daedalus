import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";

// 1. Use the empty adapter since we're using a single LangGraph agent
//    (The agent handles all LLM interactions)
const serviceAdapter = new ExperimentalEmptyAdapter();

// 2. Create the CopilotRuntime instance with LangGraph AG-UI integration
const runtime = new CopilotRuntime({
  agents: {
    // Agent name must match the name defined in your FastAPI backend
    daedalus_agent: new LangGraphHttpAgent({
      url: process.env.AGENT_URL || "http://localhost:8000",
    }),
  },
});

// 3. Build the Next.js API route handler
export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};