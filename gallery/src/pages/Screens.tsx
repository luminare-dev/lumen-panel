// Whole screens: the dashboard after login and the login page (layout/extern in the panel).
import { Card } from "../parts";
import { DomainTable } from "./Components";

function Usage({ label, percent, current, max }: { label: string; percent: number; current?: string; max?: string }) {
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
      <progress className="progress is-xsmall" data-load-level={level} value={percent} max={100} aria-label={label}>
        {percent} %
      </progress>
    </div>
  );
}

export function Dashboard() {
  return (
    <>
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
      <article className="message is-warning">
        <div className="message-body">
          <strong>Warning:</strong> The certificate for app.example.net expires in 9 days.
        </div>
      </article>
      <Card icon="globe" title="Domains">
        <DomainTable />
      </Card>
    </>
  );
}

export function Login({ dark }: { dark: boolean }) {
  return (
    <>
      <p className="gallery-lead has-text-grey">
        The login and password pages use the panel's external layout. On the live panel this is a full-height page; here it
        is shown inside the gallery.
      </p>
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
    </>
  );
}
