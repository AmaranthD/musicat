# Local web app: palco e som no navegador

O Musicat é um web app local de usuário único: um backend Python (FastAPI) serve um front-end vanilla-JS em `localhost`, guarda os arquivos e o SQLite, e faz stream do áudio. A reprodução e a análise de batida acontecem **no navegador**, via Web Audio API (`AnalyserNode`); o Python nunca decodifica nem toca áudio.

Alternativas consideradas: reprodução no Python (pygame/VLC/librosa) com análise enviada ao front por rede — rejeitada porque sincronizar animação com áudio via rede é frágil e introduz latência; front estático sem backend — rejeitada porque o usuário quer backend Python e os arquivos precisam ser guardados no servidor.
