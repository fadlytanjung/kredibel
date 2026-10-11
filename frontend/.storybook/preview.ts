import type { Preview } from "@storybook/react";
import "../src/app/styles/tokens.css";
import "../src/app/styles/tailwind-theme.css";
import "../src/index.css";
import "@fontsource-variable/archivo";

const customViewports = {
  mobile: {
    name: "Mobile (Compact)",
    styles: {
      width: "390px",
      height: "844px",
    },
  },
  tablet: {
    name: "Tablet (Medium)",
    styles: {
      width: "834px",
      height: "1194px",
    },
  },
  desktop: {
    name: "Desktop (Large)",
    styles: {
      width: "1440px",
      height: "900px",
    },
  },
};

const preview: Preview = {
  parameters: {
    viewport: {
      viewports: customViewports,
      defaultViewport: "desktop",
    },
    a11y: {
      test: "error",
    },
  },
};

export default preview;
