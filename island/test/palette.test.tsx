import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Palette } from "../src/Palette";
import { isApplePlatform } from "../src/page";
import type { Entry } from "../src/types";

const ENTRIES: Entry[] = [
  { id: "e0", label: "Dashboard", group: "Overview", href: "https://panel.example.org/?page=dashboard", newTab: false, current: true },
  { id: "e1", label: "Domains", group: "Domains", href: "https://panel.example.org/?page=domains", newTab: false, current: false },
  { id: "e2", label: "SSL certificates", group: "Domains", href: "https://panel.example.org/?page=ssl", newTab: false, current: false },
  { id: "e3", label: "Email accounts", group: "Email", href: "https://panel.example.org/?page=email", newTab: false, current: false },
  { id: "e4", label: "Documentation", group: "Links", href: "https://docs.example.org/", newTab: true, current: false },
];

function setup(props: Partial<Parameters<typeof Palette>[0]> = {}) {
  const navigate = vi.fn();
  const getEntries = vi.fn(() => ENTRIES);
  const user = userEvent.setup();
  const view = render(
    <>
      <button type="button">Before</button>
      <Palette getEntries={getEntries} navigate={navigate} {...props} />
    </>,
  );
  return { navigate, getEntries, user, view };
}

async function openWithShortcut(user: ReturnType<typeof userEvent.setup>) {
  await user.keyboard("{Control>}k{/Control}");
  return screen.getByRole("dialog");
}

const input = () => screen.getByRole("combobox");
const selected = () => screen.getAllByRole("option").find((o) => o.getAttribute("aria-selected") === "true");

beforeEach(() => {
  document.documentElement.setAttribute("lang", "en");
  document.documentElement.setAttribute("dir", "ltr");
  document.body.className = "default-mode";
});

afterEach(() => {
  cleanup();
});

describe("opening and closing", () => {
  it("renders nothing until Ctrl+K, then a labelled modal dialog with the focus in the search field", async () => {
    const { user, getEntries } = setup();
    expect(screen.queryByRole("dialog")).toBeNull();
    const dialog = await openWithShortcut(user);
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(screen.getByRole("dialog", { name: "Go to a page" })).toBe(dialog);
    expect(document.activeElement).toBe(input());
    expect(getEntries).toHaveBeenCalledTimes(1);
    expect(screen.getAllByRole("option")).toHaveLength(ENTRIES.length);
  });

  it("opens with Cmd+K too and toggles closed with the same shortcut", async () => {
    const { user } = setup();
    await user.keyboard("{Meta>}k{/Meta}");
    expect(screen.getByRole("dialog")).toBeTruthy();
    await user.keyboard("{Control>}k{/Control}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("ignores Ctrl+Shift+K and Ctrl+K inside a code editor", async () => {
    const { user } = setup();
    await user.keyboard("{Control>}{Shift>}k{/Shift}{/Control}");
    expect(screen.queryByRole("dialog")).toBeNull();
    const editor = document.createElement("div");
    editor.className = "CodeMirror";
    const area = document.createElement("textarea");
    editor.append(area);
    document.body.append(editor);
    area.focus();
    await user.keyboard("{Control>}k{/Control}");
    expect(screen.queryByRole("dialog")).toBeNull();
    editor.remove();
  });

  it("closes with Escape and gives the focus back", async () => {
    const { user } = setup();
    const before = screen.getByRole("button", { name: "Before" });
    before.focus();
    await openWithShortcut(user);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(before);
  });

  it("closes with the close button and on a click on the backdrop", async () => {
    const { user } = setup();
    await openWithShortcut(user);
    await user.click(screen.getByRole("button", { name: "Close (Esc)" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    const dialog = await openWithShortcut(user);
    fireEvent.mouseDown(dialog);
    expect(screen.getByRole("dialog")).toBeTruthy();
    fireEvent.mouseDown(dialog.parentElement!);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("listbox navigation", () => {
  it("points aria-activedescendant at the highlighted option and moves with the arrow keys", async () => {
    const { user } = setup();
    await openWithShortcut(user);
    expect(input().getAttribute("aria-activedescendant")).toBe(selected()!.id);
    expect(selected()!.textContent).toContain("Dashboard");
    await user.keyboard("{ArrowDown}");
    expect(selected()!.textContent).toContain("Domains");
    expect(input().getAttribute("aria-activedescendant")).toBe(selected()!.id);
    await user.keyboard("{ArrowUp}{ArrowUp}");
    expect(selected()!.textContent).toContain("Documentation");
    await user.keyboard("{PageUp}");
    expect(selected()!.textContent).toContain("Dashboard");
    await user.keyboard("{PageDown}");
    expect(selected()!.textContent).toContain("Documentation");
  });

  it("filters while typing and opens the highlighted entry with Enter", async () => {
    const { user, navigate } = setup();
    await openWithShortcut(user);
    await user.keyboard("ssl");
    expect(selected()!.textContent).toContain("SSL certificates");
    expect(screen.getByRole("status").textContent).toBe("1 page");
    await user.keyboard("{Enter}");
    expect(navigate).toHaveBeenCalledWith(ENTRIES[2]);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens an entry on click", async () => {
    const { user, navigate } = setup();
    await openWithShortcut(user);
    await user.click(screen.getByRole("option", { name: /Email accounts/u }));
    expect(navigate).toHaveBeenCalledWith(ENTRIES[3]);
  });

  it("says so when nothing matches and points at no option", async () => {
    const { user, navigate } = setup();
    await openWithShortcut(user);
    await user.keyboard("zzzz");
    expect(screen.queryAllByRole("option")).toHaveLength(0);
    expect(screen.getByText("No page matches.")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toBe("0 pages");
    expect(input().hasAttribute("aria-activedescendant")).toBe(false);
    await user.keyboard("{ArrowDown}{Enter}");
    expect(navigate).not.toHaveBeenCalled();
  });

  it("names the current page, the group and links that open a new tab", async () => {
    const { user } = setup();
    await openWithShortcut(user);
    expect(screen.getByRole("option", { name: "Dashboard, current page, Overview" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Documentation, opens in a new tab, Links" })).toBeTruthy();
  });
});

describe("focus trap", () => {
  it("cycles Tab and Shift+Tab between the search field and the close button", async () => {
    const { user } = setup();
    await openWithShortcut(user);
    const close = screen.getByRole("button", { name: "Close (Esc)" });
    await user.keyboard("{Tab}");
    expect(document.activeElement).toBe(close);
    await user.keyboard("{Tab}");
    expect(document.activeElement).toBe(input());
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(document.activeElement).toBe(close);
  });

  it("brings the focus back when something outside takes it", async () => {
    const { user } = setup();
    await openWithShortcut(user);
    act(() => screen.getByRole("button", { name: "Before" }).focus());
    expect(document.activeElement).toBe(input());
  });

  it("keeps the panel's own key handlers out of the palette", async () => {
    const { user } = setup();
    const onKey = vi.fn();
    document.addEventListener("keydown", onKey);
    await openWithShortcut(user);
    onKey.mockClear();
    await user.keyboard("dom{ArrowDown}");
    expect(onKey).not.toHaveBeenCalled();
    document.removeEventListener("keydown", onKey);
  });
});

describe("header button", () => {
  it("opens the palette, reports its state and gets the focus back", async () => {
    const container = document.createElement("div");
    document.body.append(container);
    const { user } = setup({ triggerContainer: container });
    const button = screen.getByRole("button", { name: /^Search pages/u });
    expect(button.getAttribute("aria-haspopup")).toBe("dialog");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(button.getAttribute("aria-keyshortcuts")).toBe("Control+K Meta+K");
    await user.click(button);
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(button.getAttribute("aria-expanded")).toBe("true");
    await user.keyboard("{Escape}");
    expect(document.activeElement).toBe(button);
    container.remove();
  });
});

describe("page state", () => {
  it("follows the panel language, direction and dark mode", async () => {
    document.documentElement.setAttribute("lang", "de-AT");
    document.documentElement.setAttribute("dir", "rtl");
    document.body.className = "dark-mode";
    const { user } = setup();
    const dialog = await openWithShortcut(user);
    expect(screen.getByRole("dialog", { name: "Zu einer Seite wechseln" })).toBe(dialog);
    expect(dialog.getAttribute("dir")).toBe("rtl");
    expect(dialog.closest(".lm")?.classList.contains("is-dark")).toBe(true);
    act(() => {
      document.body.className = "default-mode";
    });
    await waitFor(() => expect(screen.getByRole("dialog").closest(".lm")?.classList.contains("is-dark")).toBe(false));
  });

  it("shows the Command key on Apple platforms only", () => {
    expect(isApplePlatform({ platform: "MacIntel", userAgent: "" })).toBe(true);
    expect(isApplePlatform({ userAgentData: { platform: "macOS" } })).toBe(true);
    expect(isApplePlatform({ platform: "Linux x86_64", userAgent: "Mozilla/5.0 (X11; Linux x86_64)" })).toBe(false);
    expect(isApplePlatform(null)).toBe(false);
  });
});

describe("privacy", () => {
  it("makes no network request and stores nothing", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const xhr = vi.spyOn(XMLHttpRequest.prototype, "open");
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const getItem = vi.spyOn(Storage.prototype, "getItem");
    const { user, navigate } = setup();
    await openWithShortcut(user);
    await user.keyboard("dom{ArrowDown}{Enter}");
    expect(navigate).toHaveBeenCalled();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(xhr).not.toHaveBeenCalled();
    expect(setItem).not.toHaveBeenCalled();
    expect(getItem).not.toHaveBeenCalled();
  });
});
