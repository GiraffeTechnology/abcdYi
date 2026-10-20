import { build } from 'vite';
await build({configFile:false,build:{ssr:'src/execution/ExecutionWorkspace.tsx',outDir:'.test-build/component',emptyOutDir:true,rollupOptions:{external:['react','react-dom','react/jsx-runtime'],output:{entryFileNames:'ExecutionWorkspace.mjs'}}}});
