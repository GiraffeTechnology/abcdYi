import {build} from 'vite';
// Keep the default entry build unchanged; this produces a separate host bundle.
await build({build:{outDir:'dist-execution-host',rollupOptions:{input:'execution-host.html'}}});
