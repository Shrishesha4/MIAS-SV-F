import adapter from '@sveltejs/adapter-static';
export default {
  kit: {
    adapter: adapter({
      pages: 'dist', // specifies the output folder
      fallback: 'index.html' // required for SPA mode
    })
  }
};

