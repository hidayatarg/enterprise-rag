
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { SourceCitations } from "./SourceCitations";

describe("SourceCitations", () => {
    it("renders source metadata", () => {
        render(
            <SourceCitations
                sources={[
                    {
                        reference: 1,
                        filename: "sample-policy.txt",
                        page_number: 1,
                        chunk_index: 0,
                        similarity: 0.690697188848761,
                    },
                ]}
            />,
        );

        expect(
            screen.getByText(/\[1\] sample-policy.txt/),
        ).toBeTruthy();

        expect(screen.getByText("69.07%")).toBeTruthy();
        expect(screen.getByText("Sources (1)")).toBeTruthy();
    });

    it("renders multiple citations", () => {
        render(
            <SourceCitations
                sources={[
                    {
                        reference: 1,
                        filename: "refund-policy.txt",
                        page_number: 1,
                        chunk_index: 0,
                        similarity: 0.81,
                    },
                    {
                        reference: 2,
                        filename: "refund-policy.txt",
                        page_number: 2,
                        chunk_index: 3,
                        similarity: 0.74,
                    },
                ]}
            />,
        );

        expect(screen.getByText("Sources (2)")).toBeTruthy();
        expect(screen.getByText("81.00%")).toBeTruthy();
        expect(screen.getByText("74.00%")).toBeTruthy();
    });

    it("handles missing page metadata", () => {
        render(
            <SourceCitations
                sources={[
                    {
                        reference: 1,
                        filename: "policy.txt",
                        page_number: null,
                        chunk_index: 0,
                        similarity: 0.7,
                    },
                ]}
            />,
        );

        expect(screen.getByText("N/A")).toBeTruthy();
    });

    it("renders nothing when sources are empty", () => {
        const { container } = render(
            <SourceCitations sources={[]} />,
        );

        expect(container.firstChild).toBeNull();
    });
});
