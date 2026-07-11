import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createTheme, MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import { App } from "./app/App";

const theme = createTheme({
  fontFamily: '"Source Sans 3", "IBM Plex Sans", "PingFang SC", "Microsoft YaHei", sans-serif',
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MantineProvider theme={theme}>
      <App />
    </MantineProvider>
  </StrictMode>,
);
