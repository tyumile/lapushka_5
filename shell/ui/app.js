const currentHost = window.location.hostname || "127.0.0.1";
const modules = {
  sources: {
    description: "Модуль источников: загрузка файлов, реестр и состояние импорта.",
    label: "sources",
    port: "8001",
  },
  documents: {
    description: "Модуль рабочей документации: документы, распознавание и классификация.",
    label: "documents",
    port: "8002",
  },
  project: {
    description: "Проектный модуль: проекты, связи между документами и дефициты материалов.",
    label: "project",
    port: "8003",
  },
};

for (const link of document.querySelectorAll("[data-port]")) {
  const port = link.getAttribute("data-port");
  link.href = `http://${currentHost}:${port}/`;
}

const frame = document.querySelector("#module-frame");
const moduleTag = document.querySelector("#active-module-tag");
const moduleDescription = document.querySelector("#active-module-description");
const modulePort = document.querySelector("#active-module-port");
const moduleLink = document.querySelector("#active-module-link");
const navButtons = document.querySelectorAll("[data-module]");

function setActiveModule(moduleName) {
  const config = modules[moduleName] || modules.sources;
  const moduleUrl = `http://${currentHost}:${config.port}/`;

  window.location.hash = moduleName;

  if (frame) {
    frame.src = moduleUrl;
  }

  if (moduleTag) {
    moduleTag.textContent = config.label;
  }

  if (moduleDescription) {
    moduleDescription.textContent = config.description;
  }

  if (modulePort) {
    modulePort.textContent = `порт ${config.port}`;
  }

  if (moduleLink) {
    moduleLink.href = moduleUrl;
    moduleLink.setAttribute("data-port", config.port);
  }

  for (const button of navButtons) {
    button.classList.toggle("is-active", button.getAttribute("data-module") === moduleName);
  }
}

for (const button of navButtons) {
  button.addEventListener("click", () => {
    setActiveModule(button.getAttribute("data-module"));
  });
}

const initialModule = window.location.hash.replace("#", "");

if (initialModule && modules[initialModule]) {
  setActiveModule(initialModule);
} else if (frame) {
  setActiveModule("sources");
}
