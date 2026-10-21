/** One page the palette can open, read from the panel's own navigation. */
export interface Entry {
  /** Stable within one collection: "e0", "e1", ... */
  id: string;
  /** Link text, whitespace collapsed. */
  label: string;
  /** Sidebar section, or the "Account" group for the user menu. */
  group: string;
  /** Absolute http(s) URL. */
  href: string;
  /** The link opens in a new tab (target="_blank"). */
  newTab: boolean;
  /** The link is the page being shown (a.is-active in the sidebar). */
  current: boolean;
}

/** What fuzzy search needs from an entry. */
export interface Searchable {
  label: string;
  group?: string;
}

export interface Match<T extends Searchable = Entry> {
  entry: T;
  score: number;
  /** Positions of the matched characters in `entry.label` (code points). */
  indices: number[];
}
