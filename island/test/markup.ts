// Test pages written for this project. They carry only the ids and classes the island reads
// (see src/collect.ts); all names and addresses are examples.

export const INTERNAL_PAGE = `
  <header id="header">
    <nav id="top-nav">
      <div class="level is-mobile">
        <div class="level-left"><a class="level-item" href="?page=dashboard">Home</a></div>
        <div class="level-left">
          <a class="level-item" href="?page=intern&amp;action=return_to_admin">Back to administrator</a>
          <a id="app-user-menu-toggle" class="level-item" href="javascript:void(0)">admin</a>
          <a id="app-sidebar-toggle" class="level-item" href="javascript:void(0)">Menu</a>
        </div>
      </div>
    </nav>
  </header>
  <div id="user-menu" class="is-hidden">
    <a class="dropdown-item" href="?page=profile">Profile</a>
    <a class="dropdown-item" href="?page=logout">Log out</a>
  </div>
  <section id="sidebar">
    <nav id="sidebar-navigation" class="menu">
      <div class="app-menu-group">
        <p class="menu-label">  Domains
        </p>
        <ul class="menu-list">
          <li><a class="is-active" href="?page=domains"><small><span class="icon is-small"><i class="fa"></i></span></small> Domains </a></li>
          <li><a href="?page=ssl_certificates">SSL certificates</a></li>
          <li><a href="javascript:alert(1)">Script</a></li>
          <li><a href="#">Empty</a></li>
          <li><a href="?page=domains">Domains</a></li>
        </ul>
      </div>
      <div class="app-menu-group">
        <p class="menu-label">Email</p>
        <ul class="menu-list">
          <li><a href="?page=email_accounts">Email accounts</a></li>
          <li><a href="https://docs.example.org/" target="_blank">Documentation</a></li>
        </ul>
      </div>
    </nav>
  </section>
  <main id="content"><button id="outside" type="button">Outside</button></main>
`;

export const LOGIN_PAGE = `
  <section class="hero is-fullheight">
    <div class="box"><form><input name="username"><button type="submit">Log in</button></form></div>
  </section>
`;
