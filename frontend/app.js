// Acá vive el frontend, ya que es la parte más simple de la aplicación

const API = "/api";
const EXAMPLE = `INICIO
  LEER n
  SI n < 0 ENTONCES
    IMPRIMIR "Número inválido"
    TERMINAR
  FIN SI
  suma <- 0
  PARA i DESDE 1 HASTA n HACER
    SI i MOD 2 = 0 ENTONCES
      suma <- suma + i
    FIN SI
  FIN PARA
  IMPRIMIR "La suma de los pares es: ", suma
FIN`;

const $ = (sel) => document.querySelector(sel);
const state = { languages: [], current: null, generating: false };
let pseudoEditor, codeEditor, monacoRef;

function toast(msg, isErr = false) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast show" + (isErr ? " err" : "");
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.className = "toast"), 3500);
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

function langById(id) {
  return state.languages.find((l) => l.id === id);
}

function setCodeLanguage(langId) {
  const lang = langById(langId);
  monacoRef.editor.setModelLanguage(codeEditor.getModel(), lang ? lang.monaco : "plaintext");
}

function setActions(enabled) {
  ["#copy", "#save", "#download"].forEach((s) => ($(s).disabled = !enabled));
}

async function checkHealth() {
  const el = $("#status");
  try {
    const h = await api("/health");
    if (h.ollama && h.model_ready) {
      el.className = "status ok";
      el.querySelector(".status-text").textContent = `Ollama · ${h.model}`;
    } else if (h.ollama) {
      el.className = "status";
      el.querySelector(".status-text").textContent = `Descargando ${h.model}…`;
    } else {
      el.className = "status err";
      el.querySelector(".status-text").textContent = "Ollama no disponible";
    }
  } catch {
    el.className = "status err";
    el.querySelector(".status-text").textContent = "API no disponible";
  }
}

async function loadHistory() {
  const list = $("#history-list");
  const items = await api("/history").catch(() => []);
  list.innerHTML = "";
  if (!items.length) {
    list.innerHTML = '<li class="empty">Aún no hay código generado.</li>';
    return;
  }
  for (const it of items) {
    const li = document.createElement("li");
    li.dataset.id = it.id;
    if (state.current && state.current.id === it.id) li.classList.add("active");
    const date = new Date(it.created_at).toLocaleString();
    li.innerHTML = `
      <div class="meta">
        <div class="title"></div>
        <div class="sub"><span class="tag">${it.language}</span>${date}</div>
      </div>
      <button class="del" title="Eliminar">✕</button>`;
    li.querySelector(".title").textContent = it.name;
    li.addEventListener("click", () => openItem(it.id));
    li.querySelector(".del").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(`¿Eliminar "${it.name}"?`)) return;
      await api(`/history/${it.id}`, { method: "DELETE" });
      if (state.current && state.current.id === it.id) {
        state.current = null;
        codeEditor.setValue("");
        $("#saved-path").textContent = "";
        setActions(false);
      }
      loadHistory();
    });
    list.appendChild(li);
  }
}

async function openItem(id) {
  try {
    const item = await api(`/history/${id}`);
    showItem(item);
    pseudoEditor.setValue(item.pseudocode);
    $("#language").value = item.language;
    $("#name").value = item.name;
    loadHistory();
  } catch (e) {
    toast(e.message, true);
  }
}

function showItem(item) {
  state.current = item;
  setCodeLanguage(item.language);
  codeEditor.setValue(item.code);
  $("#saved-path").textContent = `generated/${item.path}`;
  $("#output-title").textContent = item.name;
  setActions(true);
}

async function generate() {
  const pseudocode = pseudoEditor.getValue().trim();
  if (pseudocode.length < 3) return toast("Escribe algo de pseudocódigo primero", true);
  const language = $("#language").value;

  state.generating = true;
  state.current = null;
  $("#generate").disabled = true;
  $("#generate").textContent = "Generando…";
  setActions(false);
  setCodeLanguage(language);
  codeEditor.setValue("");
  $("#saved-path").textContent = "";
  $("#output-title").textContent = "Generando…";

  let buffer = "";
  let streamed = "";
  try {
    const res = await fetch(`${API}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pseudocode, language, name: $("#name").value.trim() || null }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl + 1);
        if (!line) continue;
        const ev = JSON.parse(line);
        if (ev.type === "token") {
          streamed += ev.content;
          codeEditor.setValue(streamed);
          codeEditor.revealLine(codeEditor.getModel().getLineCount());
        } else if (ev.type === "done") {
          showItem(ev.item);
          toast(`Guardado en generated/${ev.item.path}`);
          loadHistory();
        } else if (ev.type === "error") {
          throw new Error(ev.message);
        }
      }
    }
  } catch (e) {
    $("#output-title").textContent = "Código generado";
    toast(e.message, true);
  } finally {
    state.generating = false;
    $("#generate").disabled = false;
    $("#generate").textContent = "Generar ▶";
  }
}

async function saveEdits() {
  if (!state.current) return;
  try {
    state.current = await api(`/history/${state.current.id}`, {
      method: "PUT",
      body: JSON.stringify({ code: codeEditor.getValue() }),
    });
    toast("Cambios guardados");
  } catch (e) {
    toast(e.message, true);
  }
}

require.config({ paths: { vs: "vendor/monaco/vs" } });
require(["vs/editor/editor.main"], async () => {
  monacoRef = monaco;
  window.registerRpgle(monaco);

  const common = {
    theme: "vs-dark",
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 14,
    scrollBeyondLastLine: false,
  };
  pseudoEditor = monaco.editor.create($("#pseudo-editor"), { ...common, language: "plaintext", value: EXAMPLE, wordWrap: "on" });
  codeEditor = monaco.editor.create($("#code-editor"), { ...common, language: "python", value: "" });

  pseudoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => !state.generating && generate());
  codeEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, saveEdits);

  state.languages = await api("/languages").catch(() => []);
  $("#language").innerHTML = state.languages.map((l) => `<option value="${l.id}">${l.label}</option>`).join("");
  $("#language").addEventListener("change", (e) => !state.current && setCodeLanguage(e.target.value));

  $("#generate").addEventListener("click", generate);
  $("#example").addEventListener("click", () => pseudoEditor.setValue(EXAMPLE));
  $("#refresh").addEventListener("click", loadHistory);
  $("#save").addEventListener("click", saveEdits);
  $("#copy").addEventListener("click", async () => {
    await navigator.clipboard.writeText(codeEditor.getValue());
    toast("Copiado al portapapeles");
  });
  $("#download").addEventListener("click", () => {
    if (state.current) window.location.href = `${API}/history/${state.current.id}/download`;
  });

  checkHealth();
  setInterval(checkHealth, 10000);
  loadHistory();
});
