/** Tailwind build config. Only layout utilities are used; components live in app.css. */
module.exports = {
  content: [
    "./src/templates/**/*.html",
    "./src/static/js/**/*.js",
  ],
  theme: { extend: {} },
  plugins: [],
};
