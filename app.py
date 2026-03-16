import unicodedata
import string
import json
import re
import hashlib
import threading
import subprocess
from pathlib import Path
import webview

from faster_whisper import WhisperModel

# Extensões suportadas (incluindo .m4a)
VIDEO_EXTS = {".mp4", ".mov", ".m4a", ".m4v", ".mkv", ".avi", ".webm"}

def normalize(s: str) -> str:
    if not s:
        return ""
    # 1. Tudo minúsculo
    s = s.lower()
    # 2. Remove acentos
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8')
    # 3. Remove pontuações
    s = s.translate(str.maketrans('', '', string.punctuation))
    # 4. Remove espaços extras
    return re.sub(r"\s+", " ", s).strip()

def sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def extract_audio(video: Path, wav: Path):
    cmd = ["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", str(wav)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

class API:
    def __init__(self):
        self.folder: Path | None = None
        self.index_dir: Path | None = None
        self.model = None
        self.indexing = False
        
        # Variáveis de progresso
        self.total_files = 0
        self.processed_files = 0
        self.current_file = ""
        
        # Cache de busca na memória RAM
        self.search_cache = None
        
        # Variáveis do Cancelamento
        self.cancel_requested = False
        self.was_cancelled = False

    def choose_folder(self):
        folder = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        if not folder:
            return {"ok": False}
        self.folder = Path(folder[0])
        self.index_dir = self.folder / ".video_index"
        self.index_dir.mkdir(exist_ok=True)
        
        # Reseta o cache ao trocar de pasta
        self.search_cache = None 
        return {"ok": True, "folder": str(self.folder)}

    def cancel_index(self):
        if self.indexing:
            self.cancel_requested = True
        return {"ok": True}

    def _ensure_model(self, model_size="small"):
        if self.model is None:
            # Usando modelo "small" para maior precisão, como conversamos
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def start_index(self, model_size="small"):
        if not self.folder or not self.index_dir:
            return {"ok": False, "error": "Selecione uma pasta primeiro."}
        if self.indexing:
            return {"ok": True, "status": "indexing"}

        self.indexing = True
        self.cancel_requested = False
        self.was_cancelled = False
        self.total_files = 0
        self.processed_files = 0
        self.current_file = "Preparando modelo e lendo arquivos..."

        def job():
            print(f"\n🤖 [Iniciando] Preparando indexação na pasta: {self.folder}")
            try:
                self._ensure_model(model_size=model_size)

                meta_json = self.index_dir / "files.json"
                files_map = {}
                if meta_json.exists():
                    try:
                        files_map = json.loads(meta_json.read_text(encoding="utf-8"))
                    except Exception:
                        files_map = {}

                videos = [p for p in self.folder.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
                self.total_files = len(videos)
                print(f"📁 [Arquivos] Total de mídias encontradas: {self.total_files}")

                for v in videos:
                    # Verifica se o usuário apertou cancelar
                    if self.cancel_requested:
                        print("\n🛑 [Cancelado] Indexação interrompida pelo usuário.")
                        self.was_cancelled = True
                        break

                    self.current_file = v.name
                    print(f"⏳ [Processando {self.processed_files + 1}/{self.total_files}] Arquivo: {v.name}")
                    
                    try:
                        sig = sha1_file(v)
                    except Exception:
                        self.processed_files += 1
                        continue

                    files_map[sig] = str(v)
                    out_json = self.index_dir / f"{sig}.json"
                    if out_json.exists():
                        print(f"⏩ [Pulando] Já indexado anteriormente: {v.name}")
                        self.processed_files += 1
                        continue

                    tmp_wav = self.index_dir / f"{sig}.wav"
                    try:
                        extract_audio(v, tmp_wav)
                        print(f"🎙️ [Transcrição] Transcrevendo áudio... (Isso pode levar alguns segundos)")
                        segments, _ = self.model.transcribe(str(tmp_wav), vad_filter=True, language="pt")

                        segs = []
                        full = []
                        for s in segments:
                            t = (s.text or "").strip()
                            if t:
                                segs.append({"start": float(s.start), "end": float(s.end), "text": t})
                                full.append(t)

                        payload = {"file": str(v), "text": " ".join(full), "segments": segs}
                        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                        print(f"✅ [Concluído] Arquivo salvo no index!")
                    except Exception as e:
                        print(f"❌ [Erro] Falha em {v.name}: {e}")
                    finally:
                        if tmp_wav.exists():
                            try: tmp_wav.unlink()
                            except Exception: pass
                        
                        self.processed_files += 1

                meta_json.write_text(json.dumps(files_map, ensure_ascii=False, indent=2), encoding="utf-8")
                
                if not self.was_cancelled:
                    print("\n🎉 [Sucesso] Indexação finalizada!")
            finally:
                self.indexing = False
                if self.was_cancelled:
                    self.current_file = "Cancelado"
                else:
                    self.current_file = "Concluído"
                self.search_cache = None 

        threading.Thread(target=job, daemon=True).start()
        return {"ok": True, "status": "started"}

    def status(self):
        return {
            "ok": True, 
            "indexing": self.indexing,
            "total": self.total_files,
            "processed": self.processed_files,
            "current": self.current_file,
            "cancelled": self.was_cancelled
        }

    def search(self, query: str, limit: int = 30):
        if not self.folder or not self.index_dir:
            return {"ok": False, "error": "Selecione uma pasta primeiro."}
        q = normalize(query)
        if not q:
            return {"ok": False, "error": "Digite uma frase."}

        meta_json = self.index_dir / "files.json"
        if not meta_json.exists():
            return {"ok": False, "error": "Clique em Indexar primeiro."}

        # Carrega os arquivos para a RAM na primeira busca
        if self.search_cache is None:
            self.search_cache = []
            try:
                files_map = json.loads(meta_json.read_text(encoding="utf-8"))
            except Exception:
                files_map = {}
                
            for sig, path_str in files_map.items():
                idx_json = self.index_dir / f"{sig}.json"
                if not idx_json.exists():
                    continue
                try:
                    data = json.loads(idx_json.read_text(encoding="utf-8"))
                    p = Path(path_str)
                    self.search_cache.append({
                        "name": p.name,
                        "path": str(p),
                        "ext": p.suffix.lower(),
                        "data": data
                    })
                except Exception:
                    continue

        results = []
        for item in self.search_cache:
            data = item["data"]
            
            # Compara a query normalizada com o texto normalizado
            if q in normalize(data.get("text", "")):
                hits = []
                for seg in data.get("segments", []):
                    if q in normalize(seg.get("text", "")):
                        hits.append({"t": seg["start"], "text": seg["text"]})
                        if len(hits) >= 3:
                            break

                results.append({
                    "name": item["name"], 
                    "path": item["path"], 
                    "ext": item["ext"], 
                    "hits": hits
                })
                if len(results) >= limit:
                    break

        return {"ok": True, "results": results}

    def reveal(self, path: str):
        p = Path(path)
        if p.exists():
            subprocess.run(["open", "-R", str(p)])
            return {"ok": True}
        return {"ok": False}

def main():
    api = API()
    webview.create_window(
        "Busca de Vídeos",
        url=str(Path("ui/index.html").resolve()), # Certifique-se de que a pasta ui existe, se seus arquivos html estiverem na mesma pasta mude para "index.html"
        width=980,
        height=640,
        resizable=True,
        js_api=api,
    )
    webview.start(gui="cocoa", debug=False)

if __name__ == "__main__":
    main()
