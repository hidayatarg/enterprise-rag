// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { askApi } from "../api/askApi";
import { documentsApi } from "../api/documentsApi";
import type { AskResponse, DocumentListResponse } from "../api/types";
import { ChatPage } from "./ChatPage";

vi.mock("../api/documentsApi", () => ({
    documentsApi: { getAll: vi.fn() },
}));

vi.mock("../api/askApi", () => ({
    askApi: { ask: vi.fn() },
}));

const documentId = "18e3b4ed-fcc3-4163-b647-93647b94c9c8";

const indexedDocuments: DocumentListResponse = {
    documents: [
        {
            id: documentId,
            filename: "sample-policy.txt",
            content_type: "text/plain",
            created_at: "2026-11-18T10:00:00Z",
            chunk_count: 1,
        },
    ],
    total: 1,
};

const groundedResponse: AskResponse = {
    question: "How long does it take to process approved refunds?",
    answer: "Approved refunds are processed within 5 business days.",
    context_found: true,
    sources: [
        {
            reference: 1,
            filename: "sample-policy.txt",
            page_number: 1,
            chunk_index: 0,
            similarity: 0.690697188848761,
        },
    ],
};

const originalScrollIntoView = Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    "scrollIntoView",
);

beforeAll(() => {
    // ChatPage scrolls to the latest message. jsdom has no layout engine.
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
        configurable: true,
        value: vi.fn(),
    });
});

afterAll(() => {
    if (originalScrollIntoView) {
        Object.defineProperty(
            HTMLElement.prototype,
            "scrollIntoView",
            originalScrollIntoView,
        );
    } else {
        Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
    }
});

beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(documentsApi.getAll).mockResolvedValue(indexedDocuments);
});

afterEach(cleanup);

async function submitQuestion(question: string) {
    await screen.findByRole("option", { name: "sample-policy.txt" });

    fireEvent.change(screen.getByRole("textbox", { name: "Your question" }), {
        target: { value: question },
    });

    fireEvent.click(screen.getByRole("button", { name: "Send question" }));
}

describe("ChatPage", () => {
    it("loads and selects the first indexed document", async () => {
        render(<ChatPage />);

        await screen.findByRole("option", { name: "sample-policy.txt" });

        const selector = screen.getByRole<HTMLSelectElement>("combobox", {
            name: "Knowledge source",
        });

        expect(selector.value).toBe(documentId);
        expect(documentsApi.getAll).toHaveBeenCalled();
    });

    it("sends the selected document and renders the answer with its source", async () => {
        vi.mocked(askApi.ask).mockResolvedValue(groundedResponse);
        render(<ChatPage />);

        await submitQuestion(groundedResponse.question);

        expect(await screen.findByText(groundedResponse.answer)).toBeTruthy();

        expect(askApi.ask).toHaveBeenCalledExactlyOnceWith({
            document_id: documentId,
            question: groundedResponse.question,
            top_k: 5,
        });

        const citations = screen.getByRole("region", { name: "Answer sources" });

        expect(within(citations).getByText("[1] sample-policy.txt")).toBeTruthy();
        expect(within(citations).getByText("69.07%")).toBeTruthy();
    });

    it("displays an abstention when retrieval found context without an answer", async () => {
        const question = "Which bank processes refunds?";
        const answer = "I could not find this information in the provided document.";

        vi.mocked(askApi.ask).mockResolvedValue({
            question,
            answer,
            context_found: true,
            sources: [],
        });

        render(<ChatPage />);
        await submitQuestion(question);

        expect(await screen.findByText("Insufficient evidence")).toBeTruthy();
        expect(screen.getByText(answer)).toBeTruthy();
        expect(screen.queryByRole("region", { name: "Answer sources" })).toBeNull();
    });
});