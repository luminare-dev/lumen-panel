# Official KeyHelp resources

KeyHelp is developed and published by Keyweb AG. These are the official pages lumen-panel's
documentation relies on. Each link was opened on **2026-10-21**: the status is the HTTP answer to a
plain request on that day, and the quote is what the page said then. lumen-panel only links these
pages; it copies nothing from them except the short quotes below.

KeyHelp is a registered trademark of Keyweb AG. lumen-panel is not affiliated with or endorsed by
Keyweb AG.

## Keyweb AG and KeyHelp pages

| Resource | Link | Status on 2026-10-21 | What it says, and where we use it |
|---|---|---|---|
| Product page | <https://www.keyweb.de/en/keyhelp/keyhelp/> | 200. <https://www.keyhelp.de/> and <https://www.keyhelp.de/documentation/> redirect here (302). | "KeyHelp® – the control panel for your server hosting". Lists dark mode among the additional features of KeyHelp Pro (used in [install.md](install.md#activate-lumen-in-the-panel)). Links the forum and the API documentation. |
| Install KeyHelp | <https://www.keyweb.de/en/keyhelp/keyhelp/#install> | 200 (the section `#install` of the product page; the older <https://www.keyweb.de/en/keyhelp/install> redirects here, 301) | Requirements: "Operating system: Ubuntu LTS or Debian", "Memory: at least 2 GB RAM / recommended from 4 GB RAM", a clean system (minimal image), "The installation must be performed as root user."; then the installer command. lumen-panel assumes a panel installed this way. |
| Overview of all functions | <https://www.keyweb.de/en/keyhelp/keyhelp/overview-of-all-functions> | 200 | "With the white-label function, you can tailor the server hosting tool to your design ideas: Use your own logo and adapt styles and functions to your own wishes and needs. In addition, you can also develop your own themes." The two routes of [install.md](install.md) are these two options. |
| Knowledge base (manuals) | <https://kb.keyhelp.de/>, in English <https://kb.keyhelp.de/index.php?ln=en> | 200 | The user and administrator manual. Keyweb's documentation page <https://doc.keyhelp.de/switch/?lang=en> calls it the "Online Documentation", marked up to date, and adds "This manual is not yet complete."; its PDF manual covers versions up to 14.7.2. Administrator area: <https://kb.keyhelp.de/category/administrator-area/78/>. |
| The User Interface | <https://kb.keyhelp.de/article/the-user-interface-61.html> (German: <https://kb.keyhelp.de/article/die-benutzeroberfl%c3%a4che-6.html>) | 200, last updated 13 December 2017 | The main navigation bar on the left, the display area in the middle and the additional navigation bar at the top (account settings, log out). |
| Configuration Files & Storage Paths | <https://kb.keyhelp.de/article/configuration-files-storage-paths-119.html> (German: <https://kb.keyhelp.de/article/konfigurationsdateien-speicherpfade-118.html>) | 200, last updated 15 March 2018 | "Please note that manual changes made by you in the configuration files created by KeyHelp can be overwritten. You should make changes primarily in the configuration GUI." `/home/keyhelp/keyhelp.backup/` holds KeyHelp's internal backups, among them "backups of KeyHelp before a panel update". Used in [install.md](install.md#requirements) and [After a KeyHelp update](install.md#after-a-keyhelp-update). |
| White Label and themes in the knowledge base | | | No article on 2026-10-21. The administrator area has the categories General, Domains, Settings, Security, Logs & Status, Templates (account and email templates), Miscellaneous and Configuration Files & Storage Paths. The panel's own help texts (below) are the reference for these pages. |
| Tutorials | <https://www.keyweb.de/en/support/learn-more/tutorials#keyhelp> | 200 (the older <https://www.keyweb.de/en/keyhelp/support/tutorials> redirects here, 301) | The KeyHelp FAQ series, among them "Install KeyHelp" and "Customize with white label" (videos on YouTube). |
| Changelog | <https://changelog.keyhelp.de/> | 200 (the menu link <https://www.keyweb.de/en/keyhelp/development/changelog> redirects here, 301) | Newest version on the check date: 26.1.1 of 19 August 2026. The entries used in these docs are listed [below](#changelog-entries-used). |
| Community forum | <https://community.keyhelp.de/> | 200 | Calls itself "The official KeyHelp forum of Keyweb AG". The threads used are listed [below](#forum-threads-on-themes). |
| REST API documentation | <https://api.keyhelp.de> | 301 to SwaggerHub, <https://app.swaggerhub.com/apis-docs/keyhelp/api/>, which needs a browser with JavaScript (a plain request gets 404 there) | The registry entry <https://api.swaggerhub.com/apis/keyhelp/api> answers 200 and names "KeyHelp RESTful API", default version 2.15, the same version as the specification the panel ships in `api/openapi.json`, which links api.keyhelp.de itself. lumen-panel does not use the API. |
| Logos and graphics | <https://www.keyweb.de/en/support/downloads> | 200 (the older <https://www.keyweb.de/en/keyhelp/development/logos-and-graphic> redirects to the German page, 301) | The section "KeyHelp – Logos & Graphics" with the KeyHelp logo and signet files. The page states no terms of use. lumen-panel neither uses nor links these files and treats the KeyHelp logos as registered trademarks of Keyweb AG (see the forum post below). |

## Changelog entries used

From <https://changelog.keyhelp.de/>, checked 2026-10-21:

| Version | Date | Entry |
|---|---|---|
| 19.1 | 6 May 2019 | "External themes now will be properly recognized and can be configured via additional configuration file / screenshot" (the `_settings.json` and `_screenshot.png` of a theme folder) |
| 19.2 | 16 July 2019 | "Custom themes are now transferred to the new KeyHelp version during panel update process" |
| 19.3 | 29 October 2019 | "Template cache now gets deleted when switching between themes" |
| 25.1 | 19 June 2025 | "Performed a comprehensive rework of the template engine and all associated UI templates, focusing on structure, maintainability, and visual consistency" |
| 26.1 | 14 August 2026 | "Refactored and streamlined template macros, reducing duplication and unifying the API" (section "Template system") |
| 26.1.1 | 19 August 2026 | the version lumen-panel is tested with |

## Forum threads on themes

| Thread | Post | What it says |
|---|---|---|
| [KeyHelp Themes](https://community.keyhelp.de/viewtopic.php?t=10363) | Alexander, Keyweb AG, 6 March 2021 | An own theme is possible without the White Label feature "by creating a sub-folder within the /theme/ directory". "KeyHelp and all of its assigned logos / images are a registered trademark of the Keyweb AG company"; the KeyHelp logo should not be changed, while renaming the panel and using an own logo is fine. |
| [Theme Bearbeiten](https://community.keyhelp.de/viewtopic.php?t=8502) (German) | Martin, 29 August 2019; Alexander, Keyweb AG, 2 September 2019 | An own theme belongs in a folder of its own, because the original theme's folder is overwritten by updates. Keyweb confirms that own themes are carried over to new versions and that this needs an own folder name. |
| [Theme zerstört Panel](https://community.keyhelp.de/viewtopic.php?t=10272) (German) | Alexander, Keyweb AG, 22 January 2021 | When a theme breaks the panel: delete the theme's folder, and in KeyHelp's database, table `settings`, set the value of `category` general, `name` default_theme to `bulma`. Used in [install.md](install.md#if-the-panel-cannot-show-the-theme-page). |
| [Theme Gestaltung](https://community.keyhelp.de/viewtopic.php?t=13240) (German) | Tobi, community moderator, 10 June 2024 | Asks a theme author why the White Label settings are not enough: try White Label first ([route B](install.md#route-b-white-label-only)). |

## The panel's own texts

Labels and help texts of KeyHelp 26.1.1, read from its English and German message catalogues on
the server (quoted briefly; the templates themselves are described, never copied):

- **Configuration → Appearance → Theme:** "Change the theme for all accounts on this server.", a
  note that the white label settings may need an update to work with the selected theme, and per
  theme its Description, Version, Author, Website and "Default design mode" (Default, Dark mode).
- **Configuration → Appearance → White Label:** the "All languages" settings "apply to all
  accounts, regardless of the language used" and "can be overwritten by the language-specific
  settings"; "Additional CSS" ("You can define your own CSS styles and override the current
  design."), "Additional JavaScript" ("You can define your own JavaScript code - jQuery can be
  used."), "Trusted sources", the page title, favicon and logo fields, and the note that KeyHelp
  is a registered trademark of Keyweb AG which may not be presented as your own.
- **Administrator accounts:** "Main administrators can edit and delete other administrator
  accounts. They can access license management and white label settings."
- **Maintenance Intervals → Update control panel:** "Keeps the control panel up-to-date and
  installs newer versions as soon as they are released."

## Links that changed

The first list of sources (collected on 2026-10-21) had these links; use the new ones:

| Old link | On 2026-10-21 | Use |
|---|---|---|
| <https://www.keyweb.de/en/keyhelp/install> | 301 | <https://www.keyweb.de/en/keyhelp/keyhelp/#install> |
| <https://www.keyweb.de/en/keyhelp/support/tutorials> | 301 | <https://www.keyweb.de/en/support/learn-more/tutorials#keyhelp> |
| <https://www.keyweb.de/en/keyhelp/development/logos-and-graphic> | 301 to the German downloads page | <https://www.keyweb.de/en/support/downloads> |
| <https://app.swaggerhub.com/apis-docs/keyhelp/api/> | 404 to a plain request, a browser page with JavaScript | <https://api.keyhelp.de>, the link KeyHelp's own API specification gives |

## Checking the links again

```bash
for u in https://www.keyweb.de/en/keyhelp/keyhelp/ https://changelog.keyhelp.de/ https://kb.keyhelp.de/; do
  curl -s -o /dev/null -w "%{http_code} %{redirect_url} $u\n" "$u"
done
```

A redirect is fine when it lands on a page that still says what is quoted here; update this page
and its date when a page moves or changes.
