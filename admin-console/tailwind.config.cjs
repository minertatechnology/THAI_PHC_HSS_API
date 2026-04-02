const defaultTheme = require("tailwindcss/defaultTheme");

module.exports = {
    content: [
        "./index.html",
        "./src/**/*.{ts,tsx,js,jsx}"
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ["Inter", ...defaultTheme.fontFamily.sans],
            },
        },
    },
    plugins: [],
};
