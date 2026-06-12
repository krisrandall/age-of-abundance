// @ts-check
import { defineConfig } from 'astro/config';

// Deployed to GitHub Pages as a project site:
//   https://krisrandall.github.io/age-of-abundance/
// If you later add a custom domain (e.g. ageofabundance.org), change `base` to '/'
// and update `site` to the new origin.
export default defineConfig({
  site: 'https://krisrandall.github.io',
  base: '/age-of-abundance',
  trailingSlash: 'ignore',
});
