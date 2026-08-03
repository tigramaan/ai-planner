# Web Service Contract

The Web service provides an installable responsive PWA. Unauthenticated users can access only `/login`. API requests use same-site HttpOnly cookies. Voice capture requires explicit interaction and shows recording/upload/error states.

Every authenticated screen shows a localized notification-state indicator derived from both browser permission/subscription state and the server's boolean push status. Permission is requested only after a user clicks Enable. A blocked state gives browser-settings recovery guidance; enabled state remains visibly confirmed.
