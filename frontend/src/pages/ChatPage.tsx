
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
    AlertCircle,
    Bot,
    FileText,
    Loader2,
    RefreshCw,
    Send,
    UserRound,
} from "lucide-react";

import { documentsApi } from "../api/documentsApi";
import { askApi } from "../api/askApi";
import { SourceCitations } from "../components/chat/SourceCitations";

import type {
    AskResponse,
    CitationSource,
    DocumentListItem,
} from "../api/types";

type ChatMessage = {
    id: number;
    role: "user" | "assistant";
    content: string;
    abstained?: boolean;
    sources?: CitationSource[];
};

const ABSTENTION_MESSAGE =
    "I could not find this information in the provided document.";

export function ChatPage() {
    const [documents, setDocuments] = useState<DocumentListItem[]>([]);
    const [documentsLoading, setDocumentsLoading] = useState(true);
    const [documentsError, setDocumentsError] = useState<string | null>(null);
    const [documentRequest, setDocumentRequest] = useState({ selectedId: "" });

    const [documentId, setDocumentId] = useState("");
    const [question, setQuestion] = useState("");
    const [topK, setTopK] = useState(5);

    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [asking, setAsking] = useState(false);
    const [chatError, setChatError] = useState<string | null>(null);

    const messageIdRef = useRef(0);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Load available documents.
    useEffect(() => {
        let active = true;

        async function loadDocuments() {
            try {
                const response = await documentsApi.getAll();

                if (!active) return;

                const previousId = documentRequest.selectedId;
                const selectedStillExists = response.documents.some(
                    (document) => document.id === previousId,
                );
                const nextId = selectedStillExists
                    ? previousId
                    : response.documents[0]?.id ?? "";

                setDocuments(response.documents);
                setDocumentsError(null);
                setDocumentId(nextId);

                if (nextId !== previousId) {
                    setMessages([]);
                    setQuestion("");
                    setChatError(null);
                }
            } catch (err) {
                if (!active) return;

                setDocumentsError(
                    err instanceof Error
                        ? err.message
                        : "Unable to load documents.",
                );
            } finally {
                if (active) {
                    setDocumentsLoading(false);
                }
            }
        }

        void loadDocuments();

        return () => {
            active = false;
        };
    }, [documentRequest]);

    // Scroll to the latest message.
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({
            behavior: "smooth",
        });
    }, [messages, asking]);

    function nextMessageId(): number {
        messageIdRef.current += 1;
        return messageIdRef.current;
    }

    function handleDocumentChange(nextDocumentId: string) {
        if (asking || documentsLoading) return;

        setDocumentId(nextDocumentId);
        setMessages([]);
        setChatError(null);
        setQuestion("");
    }

    function handleRefreshDocuments() {
        if (asking || documentsLoading) return;

        setDocumentsLoading(true);
        setDocumentRequest({ selectedId: documentId });
    }

    async function handleAsk(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        const trimmedQuestion = question.trim();

        if (documentsLoading || !documentId || !trimmedQuestion || asking) {
            return;
        }

        const userMessage: ChatMessage = {
            id: nextMessageId(),
            role: "user",
            content: trimmedQuestion,
        };

        setMessages((current) => [...current, userMessage]);
        setQuestion("");
        setAsking(true);
        setChatError(null);

        try {
            const response: AskResponse = await askApi.ask({
                document_id: documentId,
                question: trimmedQuestion,
                top_k: topK,
            });

            const assistantMessage: ChatMessage = {
                id: nextMessageId(),
                role: "assistant",
                content: response.answer,
                abstained: response.answer.trim() === ABSTENTION_MESSAGE,
                sources: response.sources,
            };

            setMessages((current) => [
                ...current,
                assistantMessage,
            ]);
        } catch (err) {
            // Remove the failed attempt so a retry displays one question bubble.
            setMessages((current) =>
                current.filter((message) => message.id !== userMessage.id),
            );

            setChatError(
                err instanceof Error
                    ? err.message
                    : "Unable to generate an answer.",
            );

            // Restore the question for retry.
            setQuestion(trimmedQuestion);
        } finally {
            setAsking(false);
        }
    }

    return (
        <div className="mx-auto flex max-w-5xl flex-col gap-6">
            {/* Page header */}
            <div>
                <h1 className="text-2xl font-bold text-slate-900">
                    AI Chat
                </h1>

                <p className="mt-2 text-sm text-slate-600">
                    Ask questions about your indexed documents.
                    Answers are generated using retrieved evidence.
                </p>
            </div>

            {/* Document selection */}
            <section className="rounded-xl border border-slate-200 bg-white p-5">
                <div className="mb-3 flex items-center justify-between">
                    <label
                        htmlFor="chat-document"
                        className="text-sm font-medium text-slate-700"
                    >
                        Knowledge source
                    </label>

                    <button
                        type="button"
                        aria-label="Refresh documents"
                        onClick={handleRefreshDocuments}
                        disabled={documentsLoading || asking}
                        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-50"
                    >
                        <RefreshCw
                            size={18}
                            className={
                                documentsLoading
                                    ? "animate-spin"
                                    : ""
                            }
                        />
                    </button>
                </div>

                <div className="relative">
                    <FileText
                        size={18}
                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    />

                    <select
                        id="chat-document"
                        value={documentId}
                        onChange={(event) =>
                            handleDocumentChange(event.target.value)
                        }
                        disabled={
                            documentsLoading ||
                            documents.length === 0 ||
                            asking
                        }
                        className="w-full rounded-lg border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
                    >
                        {documents.length === 0 && (
                            <option value="">
                                {documentsLoading
                                    ? "Loading documents..."
                                    : "No documents available"}
                            </option>
                        )}

                        {documents.map((document) => (
                            <option
                                key={document.id}
                                value={document.id}
                            >
                                {document.filename}
                            </option>
                        ))}
                    </select>
                </div>

                {documentsError && (
                    <p
                        role="alert"
                        className="mt-3 text-sm text-red-600"
                    >
                        {documentsError}
                    </p>
                )}

                <p className="mt-3 text-xs text-slate-500">
                    Switching documents starts a new conversation.
                    Messages are stored only in this page's memory.
                </p>
            </section>

            {/* Conversation */}
            <section className="flex min-h-[420px] flex-col rounded-xl border border-slate-200 bg-white">
                <div className="border-b border-slate-200 px-5 py-4">
                    <div className="flex items-center gap-2">
                        <Bot
                            size={20}
                            className="text-indigo-600"
                        />
                        <h2 className="font-semibold text-slate-900">
                            Conversation
                        </h2>
                    </div>
                </div>

                <div
                    aria-label="Chat messages"
                    aria-live="polite"
                    className="flex max-h-[550px] min-h-[300px] flex-1 flex-col gap-5 overflow-y-auto p-5"
                >
                    {messages.length === 0 && !asking && (
                        <div className="flex flex-1 flex-col items-center justify-center text-center">
                            <Bot
                                size={42}
                                className="mb-4 text-indigo-400"
                            />

                            <h3 className="font-semibold text-slate-900">
                                Ask your first question
                            </h3>

                            <p className="mt-2 max-w-md text-sm text-slate-500">
                                Select an indexed document and ask
                                a question about its contents.
                            </p>
                        </div>
                    )}

                    {messages.map((message) => (
                        <div
                            key={message.id}
                            className={[
                                "flex gap-3",
                                message.role === "user"
                                    ? "justify-end"
                                    : "justify-start",
                            ].join(" ")}
                        >
                            {message.role === "assistant" && (
                                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700">
                                    <Bot size={18} />
                                </div>
                            )}

                            <div
                                className={[
                                    "max-w-[85%] rounded-xl px-4 py-3 text-sm leading-7",
                                    message.role === "user"
                                        ? "bg-indigo-600 text-white"
                                        : message.abstained
                                          ? "border border-amber-200 bg-amber-50 text-amber-900"
                                          : "bg-slate-100 text-slate-800",
                                ].join(" ")}
                            >
                                {message.abstained && (
                                    <div className="mb-2 flex items-center gap-2 font-semibold">
                                        <AlertCircle size={16} />
                                        Insufficient evidence
                                    </div>
                                )}

                                <p className="whitespace-pre-wrap">
                                    {message.content}
                                </p>

                                {message.role === "assistant" &&
                                  !message.abstained &&
                                  message.sources &&
                                  message.sources.length > 0 && (
                                      <SourceCitations sources={message.sources} />
                                  )}
                            </div>

                            {message.role === "user" && (
                                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-200 text-slate-700">
                                    <UserRound size={18} />
                                </div>
                            )}
                        </div>
                    ))}

                    {asking && (
                        <div
                            role="status"
                            className="flex items-center gap-3 text-sm text-slate-500"
                        >
                            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-indigo-700">
                                <Bot size={18} />
                            </div>

                            <Loader2
                                size={18}
                                className="animate-spin"
                            />

                            Retrieving evidence and generating answer...
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Error notification */}
                {chatError && (
                    <div
                        role="alert"
                        className="mx-5 mb-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
                    >
                        <AlertCircle
                            size={18}
                            className="shrink-0"
                        />
                        {chatError}
                    </div>
                )}

                {/* Question input */}
                <form
                    onSubmit={(event) => void handleAsk(event)}
                    className="border-t border-slate-200 p-5"
                >
                    <label
                        htmlFor="chat-question"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Your question
                    </label>

                    <textarea
                        id="chat-question"
                        value={question}
                        onChange={(event) =>
                            setQuestion(event.target.value)
                        }
                        rows={3}
                        maxLength={4000}
                        disabled={documentsLoading || !documentId || asking}
                        placeholder="Ask a question about the selected document..."
                        className="w-full resize-y rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none disabled:bg-slate-50"
                    />

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                            <label
                                htmlFor="chat-top-k"
                                className="text-xs text-slate-500"
                            >
                                Top K
                            </label>

                            <select
                                id="chat-top-k"
                                value={topK}
                                onChange={(event) =>
                                    setTopK(Number(event.target.value))
                                }
                                disabled={asking}
                                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
                            >
                                {[1, 3, 5, 10, 20].map((value) => (
                                    <option
                                        key={value}
                                        value={value}
                                    >
                                        {value}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <button
                            type="submit"
                            disabled={
                                documentsLoading ||
                                asking ||
                                !documentId ||
                                !question.trim()
                            }
                            className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {asking ? (
                                <>
                                    <Loader2
                                        size={18}
                                        className="animate-spin"
                                    />
                                    Thinking...
                                </>
                            ) : (
                                <>
                                    <Send size={18} />
                                    Send question
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </section>
        </div>
    );
}
