// Components: our own markup, written with the Bulma classes the panel uses, so every rule of
// the Lumen stylesheet can be seen in light, dark, LTR and RTL. All names, domains and addresses
// are examples (example.org, 192.0.2.0/24, 2001:db8::/32).
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { AnchorHTMLAttributes } from "react";
import { Card, Icon, Lead } from "../parts";

export function Cards() {
  return (
    <>
      <Lead>Every section of a panel page is a card: an icon and a title in the header, the content, sometimes a footer.</Lead>
      <div className="columns">
        <div className="column">
          <Card icon="server" title="Card with a collapsible header" collapsible>
            <p>Click targets in the header get a hover surface; the chevron shows that the card folds.</p>
          </Card>
        </div>
        <div className="column">
          <Card
            icon="mail"
            title="Card with footer actions"
            footer={
              <>
                <div className="card-footer-item">
                  <a href="#cards">Edit</a>
                </div>
                <div className="card-footer-item">
                  <a href="#cards">Show log</a>
                </div>
              </>
            }
          >
            <p>Footer items are separated by hairlines and keep a 44px tall click target.</p>
          </Card>
        </div>
      </div>
      <Card icon="layout" title="Card on card">
        <div className="card is-card-on-card">
          <div className="card-content">
            <p>A nested card uses the sunken surface, so the levels stay visible without a second shadow.</p>
          </div>
        </div>
      </Card>
      <div className="box">
        <p className="has-text-weight-semibold">Box</p>
        <p>The login form sits in a box: one surface, one border, the large radius.</p>
      </div>
    </>
  );
}

const DOMAINS = [
  ["example.org", "web1", "Let's Encrypt", "is-success", "valid"],
  ["app.example.net", "web2", "Let's Encrypt", "is-warning", "renews in 9 days"],
  ["mail.example.com", "web1", "none", "is-danger", "missing"],
  ["docs.example.org", "web3", "custom", "is-info", "valid"],
  ["test.example", "web2", "self-signed", "is-light", "self-signed"],
] as const;

export function DomainTable() {
  return (
    <div className="table-container">
      <table className="table is-fullwidth is-striped is-hoverable has-valigned-cells">
        <thead>
          <tr>
            <th className="is-narrow">
              <label className="checkbox">
                <input type="checkbox" aria-label="Select all" />
              </label>
            </th>
            <th scope="col">Domain</th>
            <th scope="col">Account</th>
            <th scope="col">Certificate</th>
            <th scope="col" className="has-text-right">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {DOMAINS.map(([domain, user, cert, tag, status]) => (
            <tr key={domain}>
              <td>
                <label className="checkbox">
                  <input type="checkbox" aria-label={`Select ${domain}`} />
                </label>
              </td>
              <td>
                <a href="#tables">{domain}</a>
              </td>
              <td className="has-text-grey">{user}</td>
              <td>{cert}</td>
              <td className="has-text-right">
                <span className={`tag ${tag}`}>{status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Tables() {
  return (
    <>
      <Lead>Lists of domains, accounts and mailboxes are striped, hoverable tables; detail pages use key/value tables.</Lead>
      <Card icon="globe" title="Domains">
        <DomainTable />
      </Card>
      <Card icon="server" title="Key/value table">
        <div className="table-container">
          <table className="table is-fullwidth is-striped is-hoverable">
            <tbody>
              <tr>
                <th style={{ width: "34%" }}>Hostname</th>
                <td>panel.example.org</td>
              </tr>
              <tr>
                <th>IP addresses</th>
                <td>
                  <ul className="horizontal-separated-list">
                    <li>192.0.2.10</li>
                    <li>2001:db8::10</li>
                  </ul>
                </td>
              </tr>
              <tr>
                <th>PHP versions</th>
                <td>8.3, 8.4</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

// The panel marks a disabled pagination link with a disabled attribute on the <a>; React's types
// do not list it for links, so it is set on the element directly.
function PageLink({ disabled, ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { disabled: boolean }) {
  const ref = useRef<HTMLAnchorElement>(null);
  useLayoutEffect(() => {
    ref.current?.toggleAttribute("disabled", disabled);
  }, [disabled]);
  return <a ref={ref} aria-disabled={disabled ? "true" : undefined} {...props} />;
}

export function Pagination() {
  const [page, setPage] = useState(1);
  const pages = [1, 2, 3, null, 9] as const;
  const link = (n: number) => (
    <a
      className={`pagination-link${n === page ? " is-current" : ""}`}
      href="#pagination"
      aria-label={`Page ${n}`}
      aria-current={n === page ? "page" : undefined}
      onClick={(event) => {
        event.preventDefault();
        setPage(n);
      }}
    >
      {n}
    </a>
  );
  return (
    <>
      <Lead>Long tables page with the panel's centred pagination; the previous link is disabled on the first page.</Lead>
      <Card icon="table" title="Pagination">
        <nav className="pagination is-centered" aria-label="Pagination">
          <PageLink
            className="pagination-previous"
            href="#pagination"
            disabled={page === 1}
            onClick={(event) => {
              event.preventDefault();
              if (page > 1) setPage(page === 9 ? 3 : page - 1);
            }}
          >
            Previous page
          </PageLink>
          <PageLink
            className="pagination-next"
            href="#pagination"
            disabled={page === 9}
            onClick={(event) => {
              event.preventDefault();
              if (page < 9) setPage(page === 3 ? 9 : page + 1);
            }}
          >
            Next page
          </PageLink>
          <ul className="pagination-list">
            {pages.map((n, i) => (
              <li key={n ?? `gap-${i}`}>{n === null ? <span className="pagination-ellipsis">&hellip;</span> : link(n)}</li>
            ))}
          </ul>
        </nav>
      </Card>
      <Card icon="table" title="Small pagination">
        <nav className="pagination is-small" aria-label="Small pagination">
          <ul className="pagination-list">
            <li>
              <a className="pagination-link is-current" href="#pagination" aria-current="page" aria-label="Page 1">
                1
              </a>
            </li>
            <li>
              <a className="pagination-link" href="#pagination" aria-label="Page 2">
                2
              </a>
            </li>
          </ul>
        </nav>
      </Card>
    </>
  );
}

export function Forms() {
  const [shown, setShown] = useState(false);
  return (
    <>
      <Lead>Labels above fields, grey help text, addons for units and the show-password button, clear error states.</Lead>
      <Card icon="form" title="Mailbox settings">
        <div className="columns">
          <div className="column">
            <div className="field has-margin-bottom-medium">
              <label className="label" htmlFor="f-address">
                Email address
              </label>
              <p className="has-margin-bottom-small has-text-grey" id="f-address-help">
                The address the mailbox receives mail for.
              </p>
              <div className="control">
                <input id="f-address" className="input" type="text" defaultValue="info@example.org" aria-describedby="f-address-help" />
              </div>
            </div>
            <div className="field has-margin-bottom-medium">
              <label className="label" htmlFor="f-password">
                Password
              </label>
              <div className="field has-addons">
                <div className="control is-expanded">
                  <input id="f-password" className="input" type={shown ? "text" : "password"} defaultValue="correct horse" />
                </div>
                <div className="control">
                  <button className="button is-link" type="button" aria-pressed={shown} onClick={() => setShown(!shown)}>
                    {shown ? "Hide" : "Show"}
                  </button>
                </div>
              </div>
            </div>
            <div className="field has-margin-bottom-medium">
              <label className="label" htmlFor="f-quota">
                Quota
              </label>
              <div className="field has-addons">
                <div className="control is-expanded">
                  <input id="f-quota" className="input" type="number" defaultValue="2048" min="0" />
                </div>
                <div className="control">
                  <span className="button is-static">MB</span>
                </div>
              </div>
            </div>
            <div className="field has-margin-bottom-medium">
              <label className="label" htmlFor="f-invalid">
                Forwarding address
              </label>
              <div className="control">
                <input
                  id="f-invalid"
                  className="input is-danger"
                  type="text"
                  defaultValue="not-an-address"
                  aria-invalid="true"
                  aria-describedby="f-invalid-help"
                />
              </div>
              <p className="help has-text-danger" id="f-invalid-help">
                Enter a complete address, for example name@example.org.
              </p>
            </div>
            <div className="field">
              <span className="label">Certificate file</span>
              <div className="file is-link has-name">
                <label className="file-label">
                  <input className="file-input" type="file" name="certificate" />
                  <span className="file-cta">
                    <span className="file-label">Choose a file</span>
                  </span>
                  <span className="file-name">no file selected</span>
                </label>
              </div>
            </div>
          </div>
          <div className="column">
            <div className="field has-margin-bottom-medium">
              <label className="label" htmlFor="f-owner">
                Owner (native select)
              </label>
              <div className="control">
                <div className="select is-fullwidth">
                  <select id="f-owner" defaultValue="web1">
                    <option value="web1">web1 (Client A)</option>
                    <option value="web2">web2 (Client B)</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="field has-margin-bottom-medium">
              <span className="label" id="f-s2-label">
                Owner (search field)
              </span>
              <span className="select2 select2-container select2-container--default" style={{ width: "100%" }}>
                <span className="selection">
                  <span
                    className="select2-selection select2-selection--single"
                    role="combobox"
                    aria-labelledby="f-s2-label"
                    aria-expanded="false"
                    tabIndex={0}
                  >
                    <span className="select2-selection__rendered">web2 (Client B)</span>
                    <span className="select2-selection__arrow" role="presentation">
                      <b role="presentation" />
                    </span>
                  </span>
                </span>
              </span>
            </div>
            <fieldset className="field has-margin-bottom-medium">
              <legend className="label">Spam filter</legend>
              <div className="control">
                <label className="radio">
                  <input type="radio" name="f-spam" defaultChecked /> Mark as spam
                </label>
                <label className="radio">
                  <input type="radio" name="f-spam" /> Move to junk folder
                </label>
              </div>
            </fieldset>
            <div className="field has-margin-bottom-medium">
              <label className="checkbox">
                <input type="checkbox" defaultChecked /> Keep a copy of forwarded mail
              </label>
            </div>
            <div className="field has-margin-bottom-medium">
              <label className="label" htmlFor="f-note">
                Note
              </label>
              <textarea id="f-note" className="textarea" rows={3} placeholder="Only visible to administrators" />
            </div>
            <div className="field">
              <label className="label" htmlFor="f-disabled">
                Disabled field
              </label>
              <input id="f-disabled" className="input" type="text" defaultValue="cannot be changed" disabled />
            </div>
          </div>
        </div>
        <div className="buttons">
          <button className="button is-link" type="button">
            Save
          </button>
          <button className="button" type="button">
            Cancel
          </button>
        </div>
      </Card>
    </>
  );
}

const BUTTON_STYLES = [
  ["is-link", "Save"],
  ["is-danger", "Delete"],
  ["is-dark", "Grey"],
  ["", "Default"],
  ["is-success", "Success"],
  ["is-warning", "Warning"],
  ["is-info", "Info"],
] as const;

export function Buttons() {
  return (
    <>
      <Lead>Primary actions use the link style, destructive ones the danger style; every button has a visible focus ring.</Lead>
      <Card icon="button" title="Solid">
        <div className="buttons">
          {BUTTON_STYLES.map(([cls, label]) => (
            <button key={label} className={`button ${cls}`.trim()} type="button">
              {label}
            </button>
          ))}
        </div>
      </Card>
      <Card icon="button" title="Outlined and light">
        <div className="buttons">
          {BUTTON_STYLES.filter(([cls]) => cls).map(([cls, label]) => (
            <button key={label} className={`button is-outlined ${cls}`} type="button">
              {label}
            </button>
          ))}
        </div>
        <div className="buttons">
          {BUTTON_STYLES.filter(([cls]) => cls).map(([cls, label]) => (
            <button key={label} className={`button is-light ${cls}`} type="button">
              {label}
            </button>
          ))}
        </div>
      </Card>
      <Card icon="button" title="States and sizes">
        <div className="buttons">
          <button className="button is-link" type="button">
            <Icon name="check" />
            <span>With icon</span>
          </button>
          <button className="button is-link is-loading" type="button" aria-label="Saving">
            Saving
          </button>
          <button className="button is-link" type="button" disabled>
            Disabled
          </button>
          <button className="button is-text" type="button">
            Text button
          </button>
          <button className="button is-small" type="button">
            Small
          </button>
          <button className="button is-medium is-link" type="button">
            Medium
          </button>
        </div>
      </Card>
    </>
  );
}

export function Tags() {
  return (
    <>
      <Lead>Tags mark states in tables: valid, expiring, outdated. Each colour keeps 4.5:1 for its text.</Lead>
      <Card icon="tag" title="Status tags">
        <div className="tags">
          <span className="tag">default</span>
          <span className="tag is-info">beta</span>
          <span className="tag is-success">active</span>
          <span className="tag is-warning">expires soon</span>
          <span className="tag is-danger">outdated</span>
          <span className="tag is-link">link</span>
          <span className="tag is-dark">locked</span>
          <span className="tag is-light">light</span>
        </div>
        <div className="tags has-addons">
          <span className="tag is-dark">KeyHelp</span>
          <span className="tag is-info">26.1.1</span>
        </div>
      </Card>
      <Card icon="tag" title="Text helpers">
        <p>
          <span className="has-text-success">success</span> · <span className="has-text-warning">warning</span> ·{" "}
          <span className="has-text-danger">danger</span> · <span className="has-text-info">info</span> ·{" "}
          <span className="has-text-grey">grey</span> · <span className="has-text-grey-light">grey light</span> ·{" "}
          <a href="#tags">a link</a>
        </p>
      </Card>
    </>
  );
}

const MESSAGES = [
  ["is-info", "Info", "A new version is available. The update runs tonight at 03:00."],
  ["is-success", "Done", "The settings were saved."],
  ["is-warning", "Warning", "The certificate for app.example.net expires in 9 days."],
  ["is-danger", "Error", "The backup could not reach its storage. Check the connection settings."],
] as const;

export function Notifications() {
  const [hidden, setHidden] = useState<string[]>([]);
  return (
    <>
      <Lead>The panel shows its events as messages above the page content; each can be dismissed.</Lead>
      {MESSAGES.filter(([cls]) => !hidden.includes(cls)).map(([cls, label, text]) => (
        <article className={`message ${cls} has-delete`} key={cls}>
          <div className="message-body">
            <strong>{label}:</strong> {text} <a href="#notifications">More</a>
            <button className="delete" type="button" aria-label={`Dismiss: ${label}`} onClick={() => setHidden([...hidden, cls])} />
          </div>
        </article>
      ))}
      {hidden.length > 0 && (
        <p className="has-margin-bottom-medium">
          <button className="button is-small" type="button" onClick={() => setHidden([])}>
            Show all messages again
          </button>
        </p>
      )}
      <div className="notification">A neutral notification without a colour.</div>
    </>
  );
}

export function Modals() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);
  return (
    <>
      <Lead>Modals show connection data and DKIM records; dropdowns and tooltips float above the page.</Lead>
      <Card icon="window" title="Overlays">
        <div className="columns">
          <div className="column">
            <button className="button is-link" type="button" onClick={() => setOpen(true)}>
              Open modal
            </button>
          </div>
          <div className="column">
            <div className="dropdown-content gallery-static">
              <a href="#modals" className="dropdown-item">
                Profile
              </a>
              <hr className="dropdown-divider" />
              <a href="#modals" className="dropdown-item is-active">
                Dark mode
              </a>
            </div>
          </div>
          <div className="column">
            <div className="tippy-box gallery-static" data-theme="light-border" data-placement="top" role="tooltip">
              <div className="tippy-content">A tooltip in the panel's light-border style.</div>
            </div>
          </div>
        </div>
      </Card>
      {open && (
        <div className="modal is-active">
          <div className="modal-background" onClick={() => setOpen(false)} />
          <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="gallery-modal-title">
            <header className="modal-card-head">
              <p className="modal-card-title" id="gallery-modal-title">
                Connection data
              </p>
              <button className="delete" type="button" aria-label="Close" onClick={() => setOpen(false)} />
            </header>
            <section className="modal-card-body">
              <table className="table is-fullwidth">
                <tbody>
                  <tr>
                    <th>Server</th>
                    <td>mail.example.org</td>
                  </tr>
                  <tr>
                    <th>Port</th>
                    <td>993 (IMAP, TLS)</td>
                  </tr>
                </tbody>
              </table>
            </section>
            <footer className="modal-card-foot">
              <button className="button is-link" type="button" onClick={() => setOpen(false)}>
                Save
              </button>
              <button className="button" type="button" onClick={() => setOpen(false)}>
                Cancel
              </button>
            </footer>
          </div>
        </div>
      )}
    </>
  );
}

export function Tabs() {
  const [tab, setTab] = useState(0);
  const items = ["General", "PHP", "Redirects", "Security"];
  return (
    <>
      <Lead>Settings pages split into boxed, centred tabs; the active tab joins its panel.</Lead>
      <Card icon="tabs" title="Domain settings">
        <div className="tabs is-centered is-boxed">
          <ul>
            {items.map((label, i) => (
              <li key={label} className={i === tab ? "is-active" : undefined}>
                <a
                  href="#tabs"
                  aria-current={i === tab ? "page" : undefined}
                  onClick={(event) => {
                    event.preventDefault();
                    setTab(i);
                  }}
                >
                  <span>{label}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
        <div className="tabs-content">
          {items.map((label, i) => (
            <div key={label} className={`tabs-panel${i === tab ? " is-active" : ""}`}>
              <p>
                Settings for <strong>{label}</strong>.
              </p>
            </div>
          ))}
        </div>
      </Card>
      <Card icon="tabs" title="Underlined tabs">
        <div className="tabs">
          <ul>
            <li className="is-active">
              <a href="#tabs" aria-current="page">
                Overview
              </a>
            </li>
            <li>
              <a href="#tabs">Log</a>
            </li>
            <li>
              <a href="#tabs">Statistics</a>
            </li>
          </ul>
        </div>
      </Card>
    </>
  );
}

