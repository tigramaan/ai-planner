# Web Service Contract

The Web service provides an installable responsive PWA. Unauthenticated users can access only `/login`. API requests use same-site HttpOnly cookies. Voice capture requires explicit interaction and shows recording/upload/error states.

Every authenticated screen shows a localized notification-state indicator derived from both browser permission/subscription state and the server's boolean push status. Permission is requested only after a user clicks Enable. A blocked state gives browser-settings recovery guidance; enabled state remains visibly confirmed.

On viewports up to 767 pixels wide, the primary chat is a viewport application surface: the desktop heading and command-example panel are hidden, bottom navigation and composer remain visible, and only message history scrolls. The notification-state banner, when shown, consumes space inside the same bounded viewport.

Email addresses rendered in chat messages are keyboard-accessible buttons. Selecting one inserts that exact address into the composer, focuses the composer and never sends the command automatically.

The notification test targets the browser's current PushSubscription and distinguishes push-service acceptance from confirmed operating-system display. The commitment-radar view is responsive down to 320 pixels, groups grounded findings by ownership, and routes proposed follow-up into an editable chat draft rather than executing a side effect.
