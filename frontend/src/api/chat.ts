import api from "./client";

export type HistoryMessage = {
  role: string;
  content: string;
};

export type ChatIntentRequest = {
  session_id?: string;
  message: string;
  history?: HistoryMessage[];
  model_name?: string;
};

export type ChatIntentData = {
  session_id: string;
  intent: "chat" | "business_query";
  is_followup: boolean;
  confidence: number;
  merged_query: string;
  rewritten_query: string;
  threshold: number;
};

export type ChatIntentResponse = {
  code: number;
  message: string;
  data: ChatIntentData;
};

export async function postChatIntent(payload: ChatIntentRequest): Promise<ChatIntentResponse> {
  const response = await api.post<ChatIntentResponse>("/chat/intent", payload);
  return response.data;
}

