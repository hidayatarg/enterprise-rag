
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AppLayout } from "./AppLayout";

describe("AppLayout", () => {
  it("renders navigation and child page", () => {
    render(
      <MemoryRouter initialEntries={["/documents"]}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route
              path="/documents"
              element={<h1>Document workspace</h1>}
            />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("navigation", {
        name: "Main navigation",
      }),
    ).toBeTruthy();

    expect(
      screen.getByRole("heading", {
        name: "Document workspace",
      }),
    ).toBeTruthy();

    expect(
      screen.getByRole("link", {
        name: "Documents",
      }).getAttribute("aria-current"),
    ).toBe("page");
  });
});
