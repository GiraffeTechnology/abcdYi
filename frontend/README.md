# abcdYi web entry

This frontend opens the existing MyAivan application for inquiry, quotation, and
order confirmation. It does not duplicate Aivan's workflow or implement a second
login, approval, or order-confirmation UI. The preserved pages under `src/pages/`
are not the active entry.

## Configuration

MyAivan chooses a free port at startup (never 443) and writes it to its port file.
Set `MYAIVAN_PORT_FILE` to that file and `MYAIVAN_PUBLIC_HOST` to its host, and the
build derives the entry `scheme://host:<chosen port>/app`. Set `VITE_MYAIVAN_URL`
only to override it with a complete MyAivan web entry URL. The dev server also
picks a free port unless `VITE_DEV_PORT` is set.
The authoritative Aivan application exposes `/app` (and `/`) and owns its `/static`
assets. A deployment mounted under another prefix must supply its externally
reachable entry URL. No host, web port, reverse proxy, or TLS listener is inferred.
The entry accepts absolute HTTP(S) URLs only, without credentials, query strings,
or fragments. The URL must state its port explicitly; any port is accepted except
443, which is owned by SSH on CTYun hosts. A missing or invalid value displays a configuration status and no
navigation link. Never place credentials, API keys, tenant IDs, or business data
in a `VITE_*` value: these values are public browser configuration.

MyAivan handles login and establishes its own authenticated, tenant-bound session.
This link transfers no abcdYi token and does not claim cross-application SSO.
Navigation is user initiated, so browser Back works normally without a redirect
loop. No commercial message is sent by opening this entry.

Source reference: [Aivan web routes at ab81668](https://github.com/GiraffeTechnology/aivan/blob/ab81668fb1e52460d537baa71ebb93598b3ca583/src/aivan/api/main.py).
This inspected source revision is not itself a deployment or merged-release claim.

## Local checks and build

Run `npm ci`, `npm test`, and `npm run build`. Vite reads `VITE_MYAIVAN_URL` at dev
server startup or production build time; changing a deployed static build requires
a rebuild. The repository's existing Compose frontend is a development server;
its deployment operator must explicitly supply this value using the approved
deployment configuration. The Compose file and its bindings are unchanged here.

Deployment must confirm the URL, authentication, tenant and private-data mapping,
and the complete user workflow. Aivan persists confirmed POs to the private
provider; no abcdYi consumer/association for those POs was identified in the
inspected baseline. This entry does not add that handoff. A consumer of the same
selected provider can supply it without a direct Aivan execution API call.
See `../docs/NON_DEPLOYMENT_ACCEPTANCE.md`
for this remaining implementation gap and the verification boundary.
