// Gallery sections: our own markup, written with the Bulma classes and ids the panel uses, so
// every rule of the Lumen stylesheet can be seen in light, dark, LTR and RTL. All names,
// domains and addresses are examples (example.org, 192.0.2.0/24, 2001:db8::/32).
import { useEffect, useState } from "react";
import { Icon, Svg } from "./Icon.jsx";

function Card({ icon, title, children, footer, collapsible = false, id }) {
  return (
    <div className="card has-margin-bottom-large" id={id}>
      <div className={`card-header${collapsible ? " is-collapsible" : ""}`}>
        <div className="card-header-icon">
          <Icon name={icon} />
        </div>
        <div className="card-header-title">{title}</div>
        {collapsible && (
          <div className="card-header-icon">
            <span className="icon is-medium has-text-grey-light">
              <Svg name="down" />
            </span>
          </div>
        )}
      </div>
      <div className="card-content">{children}</div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  );
}

function Usage({ label, percent, current, max }) {
  const level = percent <= 79 ? "low" : percent <= 89 ? "medium" : "high";
  return (
    <div className="usage-indicator has-ws-no-wrap">
      <div className="level has-margin-bottom-xsmall is-mobile">
        <div className="level-left">
          <p className="level-item has-text-weight-bold">{label}</p>
        </div>
        <div className="level-right">
          <p className="level-item">{current ? `${current} / ${max}` : `${percent} %`}</p>
        </div>
      </div>
      <progress className="progress is-xsmall" data-load-level={level} value={percent} max="100">
        {percent} %
      </progress>
    </div>
  );
}

export function Dashboard() {
  return (
    <section id="dashboard" aria-labelledby="dashboard-title">
      <h2 className="title is-5" id="dashboard-title">Dashboard</h2>
      <div className="columns">
        <div className="column is-7">
          <Card icon="server" title="Server information" collapsible>
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
                    <th>Operating system</th>
                    <td>Linux, 64 bit</td>
                  </tr>
                  <tr>
                    <th>Uptime</th>
                    <td>
                      12 days <span className="has-text-grey">(since 2026-10-09)</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        </div>
        <div className="column is-5">
          <Card
            icon="gauge"
            title="Utilisation"
            footer={
              <div className="card-footer-item">
                <a href="#tables">Show details</a>
              </div>
            }
          >
            <Usage label="CPU" percent={23} />
            <Usage label="Memory" percent={84} />
            <Usage label="Disk /" percent={93} current="186 GB" max="200 GB" />
          </Card>
        </div>
      </div>
    </section>
  );
}

const DOMAINS = [
  ["example.org", "web1", "Let's Encrypt", "is-success", "valid"],
  ["app.example.net", "web2", "Let's Encrypt", "is-warning", "renews in 9 days"],
  ["mail.example.com", "web1", "none", "is-danger", "missing"],
  ["docs.example.org", "web3", "custom", "is-info", "valid"],
  ["test.example", "web2", "self-signed", "is-light", "self-signed"],
];

export function Tables() {
  return (
    <section id="tables" aria-labelledby="tables-title">
      <h2 className="title is-5" id="tables-title">Tables and pagination</h2>
      <Card icon="globe" title="Domains">
        <div className="table-container">
          <table className="table is-fullwidth is-striped is-hoverable has-valigned-cells">
            <thead>
              <tr>
                <th className="is-narrow">
                  <label className="checkbox">
                    <input type="checkbox" aria-label="Select all" />
                  </label>
                </th>
                <th>Domain</th>
                <th>Account</th>
                <th>Certificate</th>
                <th className="has-text-right">Status</th>
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
        <nav className="pagination is-centered has-margin-top-large" aria-label="Pagination">
          <a className="pagination-previous" disabled aria-disabled="true">
            Previous page
          </a>
          <a className="pagination-next" href="#tables">
            Next page
          </a>
          <ul className="pagination-list">
            <li>
              <a className="pagination-link is-current" href="#tables" aria-current="page">
                1
              </a>
            </li>
            <li>
              <a className="pagination-link" href="#tables">
                2
              </a>
            </li>
            <li>
              <span className="pagination-ellipsis">&hellip;</span>
            </li>
            <li>
              <a className="pagination-link" href="#tables">
                9
              </a>
            </li>
          </ul>
        </nav>
      </Card>
    </section>
  );
}

export function Forms() {
  const [shown, setShown] = useState(false);
  return (
    <section id="forms" aria-labelledby="forms-title">
      <h2 className="title is-5" id="forms-title">Forms</h2>
      <Card icon="form" title="Mailbox settings">
        <div className="columns">
          <div className="column">
            <div className="field has-margin-bottom-medium">
              <label className="label" htmlFor="f-address">
                Email address
              </label>
              <p className="has-margin-bottom-small has-text-grey">The address the mailbox receives mail for.</p>
              <div className="control">
                <input id="f-address" className="input" type="text" defaultValue="info@example.org" />
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
                  <button className="button is-link" type="button" onClick={() => setShown(!shown)}>
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
                <input id="f-invalid" className="input is-danger" type="text" defaultValue="not-an-address" aria-invalid="true" aria-describedby="f-invalid-help" />
              </div>
              <p className="help has-text-danger" id="f-invalid-help">
                Enter a complete address, for example name@example.org.
              </p>
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
                  <span className="select2-selection select2-selection--single" role="combobox" aria-labelledby="f-s2-label" aria-expanded="false" tabIndex={0}>
                    <span className="select2-selection__rendered">web2 (Client B)</span>
                    <span className="select2-selection__arrow" role="presentation">
                      <b role="presentation" />
                    </span>
                  </span>
                </span>
              </span>
            </div>
            <div className="field has-margin-bottom-medium">
              <span className="label">Spam filter</span>
              <div className="control">
                <label className="radio">
                  <input type="radio" name="f-spam" defaultChecked /> Mark as spam
                </label>
                <label className="radio">
                  <input type="radio" name="f-spam" /> Move to junk folder
                </label>
              </div>
            </div>
            <div className="field has-margin-bottom-medium">
              <label className="checkbox">
                <input type="checkbox" defaultChecked /> Keep a copy of forwarded mail
              </label>
            </div>
            <div className="field has-margin-bottom-medium">
              <label className="label" htmlFor="f-note">
                Note
              </label>
              <textarea id="f-note" className="textarea" rows="3" placeholder="Only visible to administrators" />
            </div>
            <div className="field">
              <label className="label" htmlFor="f-disabled">
                Disabled field
              </label>
              <input id="f-disabled" className="input" type="text" defaultValue="cannot be changed" disabled />
            </div>
          </div>
        </div>
      </Card>
    </section>
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
];

export function Buttons() {
  return (
    <section id="buttons" aria-labelledby="buttons-title">
      <h2 className="title is-5" id="buttons-title">Buttons</h2>
      <Card icon="button" title="Button styles">
        <div className="buttons">
          {BUTTON_STYLES.map(([cls, label]) => (
            <button key={label} className={`button ${cls}`.trim()} type="button">
              {label}
            </button>
          ))}
        </div>
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
        <div className="buttons">
          <button className="button is-link" type="button">
            <span className="icon is-medium">
              <Svg name="check" />
            </span>
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
        </div>
      </Card>
    </section>
  );
}

export function Tags() {
  return (
    <section id="tags" aria-labelledby="tags-title">
      <h2 className="title is-5" id="tags-title">Tags</h2>
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
        <p>
          Text helpers: <span className="has-text-success">success</span> · <span className="has-text-warning">warning</span> ·{" "}
          <span className="has-text-danger">danger</span> · <span className="has-text-info">info</span> ·{" "}
          <span className="has-text-grey">grey</span> · <span className="has-text-grey-light">grey light</span> ·{" "}
          <a href="#tags">a link</a>
        </p>
      </Card>
    </section>
  );
}

export function Messages() {
  return (
    <section id="messages" aria-labelledby="messages-title">
      <h2 className="title is-5" id="messages-title">Messages and notifications</h2>
      {[
        ["is-info", "A new version is available. The update runs tonight at 03:00."],
        ["is-success", "The settings were saved."],
        ["is-warning", "The certificate for app.example.net expires in 9 days."],
        ["is-danger", "The backup could not reach its storage. Check the connection settings."],
      ].map(([cls, text]) => (
        <article className={`message ${cls}`} key={cls}>
          <div className="message-body">
            <strong>{cls.slice(3)}:</strong> {text} <a href="#messages">More</a>
          </div>
        </article>
      ))}
      <div className="notification">A neutral notification without a colour.</div>
    </section>
  );
}

export function Tabs() {
  const [tab, setTab] = useState(0);
  const items = ["General", "PHP", "Redirects", "Security"];
  return (
    <section id="tabs" aria-labelledby="tabs-title">
      <h2 className="title is-5" id="tabs-title">Tabs</h2>
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
        <div className="tabs has-margin-top-large">
          <ul>
            <li className="is-active">
              <a href="#tabs">Underline tab</a>
            </li>
            <li>
              <a href="#tabs">Second</a>
            </li>
          </ul>
        </div>
      </Card>
    </section>
  );
}

export function Overlays() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);
  return (
    <section id="overlays" aria-labelledby="overlays-title">
      <h2 className="title is-5" id="overlays-title">Modal, dropdown and tooltip</h2>
      <Card icon="window" title="Overlays">
        <div className="columns">
          <div className="column">
            <button className="button is-link" type="button" onClick={() => setOpen(true)}>
              Open modal
            </button>
          </div>
          <div className="column">
            <div className="dropdown-content gallery-static">
              <a href="#overlays" className="dropdown-item">
                Profile
              </a>
              <hr className="dropdown-divider" />
              <a href="#overlays" className="dropdown-item is-active">
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
    </section>
  );
}

export function Login({ dark }) {
  return (
    <section id="login" aria-labelledby="login-title">
      <h2 className="title is-5" id="login-title">Login page</h2>
      <div className="hero is-primary is-fullheight lumen-extern gallery-login">
        <div className="hero-body">
          <div className="container">
            <div className="columns is-centered">
              <div className="column is-6-tablet is-5-desktop is-4-widescreen">
                <div className="box">
                  <figure className="has-margin-y-medium">
                    <img
                      className="lumen-logo lumen-logo--login"
                      src={`./brand/luminare-lockup-horizontal-${dark ? "dark" : "light"}.svg`}
                      width="300"
                      height="114"
                      alt="Luminare Development"
                    />
                  </figure>
                  <form onSubmit={(event) => event.preventDefault()}>
                    <div className="field has-margin-bottom-medium">
                      <label className="label" htmlFor="l-user">
                        Username
                      </label>
                      <input id="l-user" className="input" type="text" autoComplete="off" />
                    </div>
                    <div className="field has-margin-bottom-medium">
                      <label className="label" htmlFor="l-pass">
                        Password
                      </label>
                      <input id="l-pass" className="input" type="password" autoComplete="off" />
                    </div>
                    <button className="button is-link is-fullwidth" type="submit">
                      Log in
                    </button>
                  </form>
                  <p className="has-text-centered has-text-link has-margin-top-medium">
                    <a href="#login">Forgot your password?</a>
                  </p>
                </div>
                <div className="has-text-centered is-size-7 has-text-grey-lighter">
                  <p>Panel footer text</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export { Icon };
