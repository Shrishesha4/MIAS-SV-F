import adapter from '@sveltejs/adapter-static';
export default {
  kit: {
    adapter: adapter({
      pages: 'dist', // specifies the output folder
      fallback: 'index.html' // required for SPA mode
    }),
    // Content Security Policy applied to the built HTML shell.
    // unsafe-inline is required for Tailwind + Aqua inline style= attributes.
    // connect-src is left open because the API URL is configurable at runtime.
    csp: {
      directives: {
        'default-src': ['self'],
        'script-src':  ['self'],
        'style-src':   ['self', 'unsafe-inline'],
        'img-src':     ['self', 'data:', 'blob:'],
        'font-src':    ['self'],
        'connect-src': ['self', 'http://localhost:8001', 'https://localhost:8001', 'https://vhealth.saveetha.com'],
        'object-src':  ['none'],
        'base-uri':    ['self'],
        'frame-ancestors': ['none'],
        'form-action': ['self'],
      }
    }
  }
};

