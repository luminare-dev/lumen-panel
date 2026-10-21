import { act, fireEvent, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HOST_ID, mount, TRIGGER_ID, type Mounted } from "../src/mount";
import { INTERNAL_PAGE, LOGIN_PAGE } from "./markup";

let mounted: Mounted | null = null;

function start(navigate = vi.fn()) {
  act(() => {
    mounted = mount(document, navigate);
  });
  return navigate;
}

function shadow(id: string) {
  const root = document.getElementById(id)?.shadowRoot;
  if (!root) throw new Error(`${id} has no shadow root`);
  return within(root as unknown as HTMLElement);
}

beforeEach(() => {
  document.body.className = "default-mode";
  document.body.innerHTML = INTERNAL_PAGE;
});

afterEach(() => {
  act(() => mounted?.unmount());
  mounted = null;
  document.body.innerHTML = "";
});

describe("mount", () => {
  it("does nothing on the login page and other layouts without the sidebar", () => {
    document.body.innerHTML = LOGIN_PAGE;
    start();
    expect(mounted).toBeNull();
    expect(document.getElementById(HOST_ID)).toBeNull();
    expect(document.getElementById(TRIGGER_ID)).toBeNull();
  });

  it("renders into its own shadow roots and only once", () => {
    start();
    const host = document.getElementById(HOST_ID)!;
    expect(host.parentElement).toBe(document.body);
    expect(host.shadowRoot?.querySelector("style")).not.toBeNull();
    const trigger = document.getElementById(TRIGGER_ID)!;
    expect(trigger.nextElementSibling?.id).toBe("app-user-menu-toggle");
    expect(trigger.classList.contains("level-item")).toBe(true);
    expect(trigger.shadowRoot?.querySelector("button")).not.toBeNull();
    // No palette element in the page's own DOM: the panel's CSS and scripts cannot reach it.
    expect(document.querySelector(".lm, [role='dialog'], [role='listbox']")).toBeNull();
    expect(mount(document)).toBeNull();
    expect(document.querySelectorAll(`#${HOST_ID}`)).toHaveLength(1);
  });

  it("works without the user menu toggle (no header button)", () => {
    document.getElementById("app-user-menu-toggle")!.remove();
    start();
    expect(mounted?.trigger).toBeNull();
    expect(document.getElementById(HOST_ID)).not.toBeNull();
  });

  it("opens with Ctrl+K, lists the page's navigation and opens an entry with Enter", () => {
    const navigate = start();
    act(() => {
      fireEvent.keyDown(document.body, { key: "k", ctrlKey: true });
    });
    const palette = shadow(HOST_ID);
    expect(palette.getByRole("dialog")).toBeTruthy();
    const labels = palette.getAllByRole("option").map((o) => o.querySelector(".label")?.textContent);
    expect(labels).toEqual(["Domains", "SSL certificates", "Email accounts", "Documentation", "Back to administrator", "Profile", "Log out"]);
    const input = palette.getByRole("combobox");
    act(() => {
      fireEvent.change(input, { target: { value: "mail" } });
    });
    act(() => {
      fireEvent.keyDown(input, { key: "Enter" });
    });
    expect(navigate).toHaveBeenCalledWith(expect.objectContaining({ label: "Email accounts", newTab: false }));
    expect(palette.queryByRole("dialog")).toBeNull();
  });

  it("opens from the header button", () => {
    start();
    act(() => {
      shadow(TRIGGER_ID).getByRole("button").click();
    });
    expect(shadow(HOST_ID).getByRole("dialog")).toBeTruthy();
  });

  it("removes everything it added on unmount", () => {
    start();
    act(() => mounted?.unmount());
    mounted = null;
    expect(document.getElementById(HOST_ID)).toBeNull();
    expect(document.getElementById(TRIGGER_ID)).toBeNull();
  });
});

describe("entry script", () => {
  it("starts on the internal layout and stays silent elsewhere", async () => {
    vi.resetModules();
    document.body.innerHTML = LOGIN_PAGE;
    await act(async () => {
      await import("../src/main");
    });
    expect(document.getElementById(HOST_ID)).toBeNull();

    vi.resetModules();
    document.body.innerHTML = INTERNAL_PAGE;
    await act(async () => {
      await import("../src/main");
    });
    expect(document.getElementById(HOST_ID)).not.toBeNull();
    // Started by the entry script, not by start(): clean up by hand.
    document.getElementById(HOST_ID)?.remove();
  });
});
