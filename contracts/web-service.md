# Web Service Contract

The Web service provides an installable responsive PWA. Unauthenticated users can access only `/login`. API requests use same-site HttpOnly cookies. Voice capture requires explicit interaction and shows recording/upload/error states.

Today and Week are combined at `/agenda` with a range switch. Tasks and standalone reminders are sibling workspace tabs. Mobile navigation has exactly five targets—Chat, Agenda, Tasks, Radar and More—with Settings, Install and Sign out inside More.

Every authenticated screen shows a localized notification-state indicator derived from both browser permission/subscription state and the server's boolean push status. Permission is requested only after a user clicks Enable. A blocked state gives browser-settings recovery guidance; enabled state remains visibly confirmed.

On viewports up to 767 pixels wide, the primary chat is a viewport application surface: the desktop heading and command-example panel are hidden, bottom navigation and composer remain visible, and only message history scrolls. The notification-state banner, when shown, consumes space inside the same bounded viewport.

Email addresses rendered in chat messages are keyboard-accessible buttons. Selecting one inserts that exact address into the composer, focuses the composer and never sends the command automatically.

The notification test targets the browser's current PushSubscription and distinguishes push-service acceptance from confirmed operating-system display. The commitment-radar view is responsive down to 320 pixels, groups grounded findings by ownership, and routes proposed follow-up into an editable chat draft rather than executing a side effect.

## Browser locale and application icons (REQ-027, REQ-050, AP-018)

Internal locale v1: supported values are ru/en. The first supported preference
wins; unknown/empty preferences resolve to en. Initial rendering reads at most
4096 characters and 32 ranges from Accept-Language, sorts valid q values in
descending order with stable ties and ignores zero or malformed weights. The
server passes this same locale to the HTML lang attribute and shared client
provider. Hydration must render the server locale first; afterwards navigator.languages
(or navigator.language for an empty list) is authoritative. languagechange updates
all consumers and html.lang. No cookie, database setting or localStorage locale
override is created. API requests continue to send the resolved browser locale.

Public icon v1 paths remain /icon.svg, /apple-touch-icon.png, /icon-192.png and
/icon-512.png; they stay accessible without a session. The common mark is a white
calendar sheet with blue AI lettering on blue. The PNGs are 180/192/512 square
pixels; 512 is maskable with foreground in its central 80% safe circle. Metadata,
manifest and notification assets use a calendar-ai-1 query revision to refresh
cached icons. The navigation retains the UMEC logo.

Errors: unsupported/malformed language preferences deterministically select en.
Hydration/locale errors are detectable in the browser console and tested; missing
or malformed icons are detected by unauthenticated HTTP and PNG dimension checks.

Build boundary (AP-018): production Web uses the repository workspace package-lock.json and npm ci, with Next 16.3.6 pinned to a patched release in the existing production minor line. The root Docker context is allowlisted to Web source and dependency manifests; secrets, .env files, backups, other service sources and generated files are excluded. Standalone tracing includes the workspace root; runtime starts services/web/server.js.
