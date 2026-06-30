"""
Runtime hook do PyInstaller: registra os diretórios de DLL do bundle.

No bundle onedir, o .EXE fica em `binaries/` (vazio) e todas as DLLs em
`_internal/` (= sys._MEIPASS). O torch carrega c10.dll/torch_cpu.dll/... com
LoadLibraryExW(..., LOAD_LIBRARY_SEARCH_DEFAULT_DIRS), cuja busca inclui os
diretórios registrados via os.add_dll_directory(). Registramos _MEIPASS e
_MEIPASS/torch/lib para que essas DLLs e suas dependências sejam encontradas.

OBS: a causa-raiz do WinError 1114 que víamos NÃO era o caminho de busca, e sim
um runtime do Visual C++ MISTURADO no bundle (msvcp140 antigo + vcruntime140
novo). Isso é corrigido no .spec, substituindo o conjunto VC++ pelo do System32.
Este hook permanece como a base correta da busca de DLLs do bundle.
"""
import os
import sys

base = getattr(sys, "_MEIPASS", None)
if base and sys.platform == "win32":
    for sub in ("", os.path.join("torch", "lib")):
        d = os.path.join(base, sub) if sub else base
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except OSError:
                pass
