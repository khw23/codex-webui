(() => {
        try {
          const mode = localStorage.getItem("codex-webui.theme-mode");
          const normalizedMode = mode === "light" || mode === "dark" ? mode : "system";
          const resolved = normalizedMode === "dark" || (normalizedMode === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches)
            ? "dark"
            : "light";
          document.documentElement.dataset.themeMode = normalizedMode;
          document.documentElement.dataset.theme = resolved;
          document.documentElement.style.colorScheme = resolved;
          const meta = document.querySelector('meta[name="theme-color"]');
          if (meta) {
            meta.setAttribute("content", resolved === "dark" ? "#0b1220" : "#f8fafc");
          }
        } catch {}
      })();
