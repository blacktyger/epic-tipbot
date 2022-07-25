const { resolve } = require('path');

module.exports = {
  plugins: [],
  root: resolve('./static'),
  base: '/static/',
  server: {
    host: 'localhost',
    port: 3000,
    open: false,
    watch: {
      usePolling: true,
      disableGlobbing: false,
    },
  },
  resolve: {
    extensions: ['.jsx', '.js', '.json'],
  },
  build: {
    outDir: resolve('./static/dist'),
    assetsDir: '',
    manifest: true,
    emptyOutDir: true,
    target: 'es2015',
    rollupOptions: {
      input: {
        main: resolve('./static/js/main.jsx'),
      },
      output: {
        chunkFileNames: undefined,
      },
    },
  },
};
