
<div align="center">
  <h1>🎬 Busca de Vídeos com IA</h1>
  <p><em>Encontre o momento exato em que uma frase foi dita no meio de dezenas de arquivos brutos.</em></p>

  ![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white)
  ![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-green?style=for-the-badge&logo=ffmpeg&logoColor=white)
  ![Faster Whisper](https://img.shields.io/badge/AI-Faster_Whisper-orange?style=for-the-badge)
</div>

<br>

> Uma ferramenta desktop ultrarrápida desenvolvida para resolver uma das maiores dores da edição de vídeo e motion design: a caça ao tesouro na timeline.

Este projeto utiliza **Inteligência Artificial (OpenAI Whisper)** rodando localmente na sua máquina para transcrever arquivos de vídeo e áudio, criando um buscador instantâneo. O que antes levava horas procurando, agora leva segundos.

## ✨ Funcionalidades

- **🤖 IA Local e Privada:** Transcrições precisas sem precisar de internet ou enviar seus arquivos para a nuvem.
- **⚡ Busca Ultrarrápida:** Sistema de cache em memória RAM que permite pesquisar milhares de palavras em milissegundos após a primeira leitura.
- **🎯 Busca Inteligente:** Ignora pontuações, acentos e diferenças entre maiúsculas/minúsculas.
- **🛑 Controle Total:** Interface amigável com barra de progresso em tempo real e botão para cancelar a indexação a qualquer momento.
- **🛡️ Robusto:** Ignora automaticamente arquivos ocultos do macOS (como os `._`) para evitar travamentos em HDs/SSDs externos.
- **📂 Suporte a Múltiplos Formatos:** `.mp4`, `.mov`, `.m4a`, `.m4v`, `.mkv`, `.avi` e `.webm`.

---

## 🛠️ Pré-requisitos

Para rodar este projeto, você precisará ter instalado no seu computador:
1. **[Python 3.9+](https://www.python.org/downloads/)**
2. **[FFmpeg](https://ffmpeg.org/)** (Motor de extração de áudio obrigatório).

No **macOS**, instale o FFmpeg facilmente pelo terminal usando o [Homebrew](https://brew.sh/):
```bash
brew install ffmpeg
