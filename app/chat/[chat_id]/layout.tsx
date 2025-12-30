"use client";

import { useParams } from "next/navigation";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const chatId = params.chat_id as string;

  return (
    <CopilotKit 
      runtimeUrl="/api/copilotkit" 
      agent="daedalus_agent"
      threadId={chatId}
    >
      {children}
    </CopilotKit>
  );
}
