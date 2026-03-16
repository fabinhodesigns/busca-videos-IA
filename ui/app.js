const $ = (id) => document.getElementById(id);

function showLoading(on) {
  const loading = $("loading");
  if (on) {
    loading.classList.remove("hidden");
  } else {
    loading.classList.add("hidden");
  }
}

function fmtTime(t) {
  const mm = String(Math.floor(t / 60)).padStart(2, "0");
  const ss = String(Math.floor(t % 60)).padStart(2, "0");
  return `${mm}:${ss}`;
}

function renderResults(results) {
  const box = $("results");
  box.innerHTML = "";

  if (!results.length) {
    box.innerHTML = `<div class="item"><div class="itemTop"><div>Nada encontrado.</div></div></div>`;
    return;
  }

  results.forEach(r => {
    const hits = r.hits.map(h => `${fmtTime(h.t)} — ${h.text}`).join("<br/>");
    const el = document.createElement("div");
    el.className = "item";
    el.innerHTML = `
      <div class="itemTop">
        <div>
          <div><b>${r.name}</b></div>
          <div class="small">${hits || "Encontrado no texto (sem trecho exato)"}</div>
        </div>
        <div style="display:flex; flex-direction:column; gap:8px; align-items:flex-end;">
          <div class="badge">${r.ext}</div>
          <button class="link" data-path="${r.path}">Abrir no Finder</button>
        </div>
      </div>
    `;
    box.appendChild(el);
  });

  box.querySelectorAll("button.link").forEach(btn => {
    btn.addEventListener("click", async () => {
      const path = btn.getAttribute("data-path");
      await window.pywebview.api.reveal(path);
    });
  });
}

async function waitIndexFinish() {
  while (true) {
    const st = await window.pywebview.api.status();
    
    if (st.total > 0) {
      const pct = Math.round((st.processed / st.total) * 100);
      $("progressBar").style.width = `${pct}%`;
      $("loadingText").innerHTML = `Transcrevendo ${st.processed} de ${st.total} arquivos...<br><small style="color:var(--muted-color)">Atual: ${st.current}</small>`;
    } else {
      $("progressBar").style.width = `0%`;
      $("loadingText").innerHTML = st.current || "Iniciando...";
    }

    if (!st.indexing) {
      if (st.cancelled) {
        $("progressBar").style.width = `100%`;
        $("progressBar").style.backgroundColor = `#ef4444`; // Fica vermelho se cancelar
        $("loadingText").innerHTML = "Indexação Cancelada!";
      } else {
        $("progressBar").style.width = `100%`;
        $("progressBar").style.backgroundColor = `var(--primary-color)`; 
        $("loadingText").innerHTML = "Tudo pronto!";
      }
      break;
    }

    await new Promise(r => setTimeout(r, 1000)); 
  }
}

// Evento do botão Cancelar
$("btnCancel").addEventListener("click", async () => {
  $("btnCancel").disabled = true;
  $("btnCancel").innerText = "Cancelando (aguarde o arquivo atual fechar)...";
  await window.pywebview.api.cancel_index();
});

$("btnFolder").addEventListener("click", async () => {
  const res = await window.pywebview.api.choose_folder();
  if (res.ok) {
      $("folder").textContent = res.folder;
      $("btnSearch").disabled = true; 
  }
});

$("btnIndex").addEventListener("click", async () => {
  $("btnIndex").disabled = true; 
  
  // Reseta visual do botão de cancelar e da barra
  $("btnCancel").style.display = "block";
  $("btnCancel").disabled = false;
  $("btnCancel").innerText = "Cancelar Indexação";
  $("progressBar").style.backgroundColor = `var(--primary-color)`;
  
  showLoading(true);
  
  const res = await window.pywebview.api.start_index("small");

  if (res.ok) {
    await waitIndexFinish();
  } else {
    alert(res.error);
  }

  setTimeout(async () => {
    const st = await window.pywebview.api.status();
    showLoading(false);
    $("btnSearch").disabled = false;
    $("btnIndex").disabled = false;
    
    if (st.cancelled) {
        alert("Indexação foi interrompida! Os arquivos processados até agora já podem ser pesquisados.");
    } else {
        alert("Indexação finalizada! Você já pode pesquisar.");
    }
  }, 1000);
});

$("btnSearch").addEventListener("click", async () => {
  const q = $("q").value;
  if (!q) return;

  $("loadingText").innerHTML = "Buscando...";
  $("progressBar").style.width = "100%";
  $("progressBar").style.backgroundColor = `var(--primary-color)`;
  $("btnCancel").style.display = "none"; // Esconde o botão de cancelar durante a busca
  
  showLoading(true);
  
  const res = await window.pywebview.api.search(q, 30);
  
  showLoading(false);
  $("btnCancel").style.display = "block"; // Volta o botão pro lugar

  if (res.ok) {
    renderResults(res.results);
  } else {
    alert(res.error);
  }
});

$("q").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("btnSearch").click();
});