import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { DetectionOverlay } from "../components/DetectionOverlay";
import { Markdown } from "../components/Markdown";
import { ErrorBanner, MethodBadge } from "../components/ui";
import { cameraError, openCamera } from "../lib/camera";
import { AuthProvider } from "../lib/auth";
import AuthPage from "../pages/AuthPage";

describe("MethodBadge", () => {
  it("labels provenance explicitly", () => {
    render(<MethodBadge method="heuristic" />);
    expect(screen.getByText("heuristic")).toBeInTheDocument();
    render(<MethodBadge method="closeup_fallback" />);
    expect(screen.getByText("close-up fallback")).toBeInTheDocument();
  });
});

describe("DetectionOverlay", () => {
  it("draws one rectangle per detection with confidence labels", () => {
    const { container } = render(
      <DetectionOverlay width={100} height={100} boxes={[
        { box: [0, 0, 10, 10], score: 0.9, low_confidence: false },
        { box: [20, 20, 40, 40], score: 0.3, low_confidence: true },
      ]} />,
    );
    expect(container.querySelectorAll("rect")).toHaveLength(2);
    expect(screen.getByText("90%")).toBeInTheDocument();
    // low-confidence boxes are dashed
    expect(container.querySelectorAll("rect")[1].getAttribute("stroke-dasharray")).not.toBeNull();
  });
});

describe("Markdown", () => {
  it("renders headings, tables and safe links only", () => {
    render(<Markdown text={"# Title\n\n| a | b |\n|---|---|\n| 1 | **2** |\n\n[ok](https://x.org) [bad](javascript:alert(1))"} />);
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("2").tagName).toBe("STRONG");
    expect(screen.getByText("ok").closest("a")).toHaveAttribute("href", "https://x.org");
    // the javascript: link must not become an anchor - only the https link is a link
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(screen.queryByRole("link", { name: /bad/ })).toBeNull();
    expect(document.body.textContent).toContain("bad");
  });
});

describe("camera errors", () => {
  it("maps permission denial to a readable message", () => {
    expect(cameraError({ name: "NotAllowedError" }).kind).toBe("denied");
    expect(cameraError({ name: "NotFoundError" }).kind).toBe("not_found");
    expect(cameraError({ name: "NotReadableError" }).kind).toBe("busy");
  });
  it("refuses insecure contexts", async () => {
    vi.stubGlobal("isSecureContext", false);
    await expect(openCamera({})).rejects.toMatchObject({ kind: "insecure" });
    vi.unstubAllGlobals();
  });
  it("reports missing getUserMedia", async () => {
    vi.stubGlobal("isSecureContext", true);
    Object.defineProperty(navigator, "mediaDevices", { value: undefined, configurable: true });
    await expect(openCamera({})).rejects.toMatchObject({ kind: "unsupported" });
    vi.unstubAllGlobals();
  });
});

describe("ErrorBanner", () => {
  it("renders nothing without an error and an alert with one", () => {
    const { container, rerender } = render(<ErrorBanner error={null} />);
    expect(container).toBeEmptyDOMElement();
    rerender(<ErrorBanner error="Backend unreachable" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Backend unreachable");
  });
});

describe("AuthPage", () => {
  it("shows the password policy on registration", () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    render(<AuthProvider><MemoryRouter><AuthPage mode="register" /></MemoryRouter></AuthProvider>);
    expect(screen.getByLabelText("Registration form")).toBeInTheDocument();
    expect(screen.getByText(/at least 10 characters/i)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});

describe("SpeciesInfoPanel", () => {
  it("shows botany as reference knowledge, with the fruit limitation and AI support status", async () => {
    const { SpeciesInfoPanel } = await import("../components/SpeciesInfo");
    const body = {
      botany_scope: "General knowledge, not inferred from the image.",
      fruit_recognition: "Pollinex does not detect or recognise fruit in images.",
      species: [{
        id: "strawberry", common_name: "Strawberry", scientific_name: "Fragaria x ananassa", ai_support: "not_supported",
        primary_mechanism: "air_assisted", flower_type: "", botany: {
          family: "Rosaceae", flower: "Five-petalled", petals: "Five, white", reproductive_structures: "Many pistils",
          flowering: "Spring", flowering_period: "Spring", pollination_mechanism: "Self plus insects", pollinators: ["bees"],
          breeding_system: "Self-fertile", agricultural_relevance: "Berry crop",
          fruit: { name: "strawberry", type: "aggregate accessory fruit", characteristics: "Swollen receptacle" },
          sources: [{ id: "powo", title: "POWO", url: "https://powo.science.kew.org/" }],
        },
      }],
    };
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } }))));
    render(<SpeciesInfoPanel speciesId="strawberry" />);
    expect(await screen.findByText("About Strawberry")).toBeInTheDocument();
    expect(screen.getByText(/reference knowledge · not from this image/)).toBeInTheDocument();
    expect(screen.getByText(/not AI-supported/)).toBeInTheDocument();
    expect(screen.getByText(/does not detect or recognise fruit/)).toBeInTheDocument();
    expect(screen.getByText("POWO").closest("a")).toHaveAttribute("href", "https://powo.science.kew.org/");
    vi.unstubAllGlobals();
  });

  it("explains that nothing is shown for an unknown species", async () => {
    const { SpeciesInfoPanel } = await import("../components/SpeciesInfo");
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ species: [] }), { status: 200, headers: { "Content-Type": "application/json" } }))));
    render(<SpeciesInfoPanel speciesId="unknown" />);
    expect(screen.getByText(/not recognised, so no species information/)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
