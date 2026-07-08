; ============================================================================
;  Ganchos NSIS do instalador do Transcreve (installerHooks do Tauri).
;
;  Por que existem: os modelos de IA (~2,5 GB, cache Hugging Face) não cabem
;  dentro do instalador — o NSIS usa mmap e falha perto de ~2 GB. Em vez de
;  embarcá-los, o instalador os BAIXA durante a instalação, uma única vez,
;  da release fixa `modelos-v1` no GitHub do projeto, direto para o destino
;  final: %ProgramData%\Transcreve\models (fora de Program Files).
;
;  Consequências desse desenho (requisitos do projeto):
;  - Atualizar o app NUNCA rebaixa os 2,5 GB: os arquivos já existem com o
;    tamanho certo e o download é pulado.
;  - Desinstalar oferece a OPÇÃO de remover os modelos (pergunta explícita,
;    padrão "Não") e remove os dados do usuário apenas se o checkbox nativo
;    "Excluir dados do aplicativo" for marcado.
;  - Download interrompido retoma do ponto em que parou (/RESUME) ao rodar o
;    instalador de novo; cada arquivo é verificado por SHA-256.
;
;  O download usa o plugin NScurl (BSD-3, ver nsis-plugins/NScurl.LICENSE.md):
;  HTTPS com validação de certificado, barra de progresso na própria página de
;  instalação e hash embutido. A lista de arquivos/hashes fica em
;  models_manifest.nsh, GERADO por scripts/release.py — não edite à mão.
; ============================================================================

!include "LogicLib.nsh"
!addplugindir /x86-unicode "${__FILEDIR__}\nsis-plugins\x86-unicode"

; Release fixa que hospeda os modelos. Imutável por construção: mudar o
; conjunto de modelos = publicar modelos-v2 e atualizar aqui + release.py.
!define TC_MODELS_URL "https://github.com/Hebert-Almeida/transcreve/releases/download/modelos-v1"
; Caminhos resolvidos em RUNTIME via ReadEnvStr (macro TC_INIT_DIRS): as
; constantes $APPDATA/$LOCALAPPDATA do NSIS mudam de alvo conforme o
; SetShellVarContext (em "all", ambas viram C:\ProgramData) — e este instalador
; perMachine roda em "all". As variáveis de ambiente não sofrem disso.
!define TC_MODELS_ROOT "$TC_ProgramData\Transcreve\models"
!define TC_MODELS_HUB "${TC_MODELS_ROOT}\hub"
!define TC_USERDATA "$TC_LocalAppData\Transcreve"

Var TC_Skip         ; 1 = não baixar mais nada (usuário recusou/cancelou ou erro)
Var TC_Failed       ; 1 = algum download/verificação falhou
Var TC_Explained    ; 1 = a caixa "por que vamos baixar" já foi mostrada
Var TC_ProgramData  ; ex.: C:\ProgramData (modelos, compartilhado na máquina)
Var TC_LocalAppData ; ex.: C:\Users\<user>\AppData\Local (dados por usuário)

; Resolve as raízes de destino a partir do ambiente, com fallback defensivo.
!macro TC_INIT_DIRS
  ReadEnvStr $TC_ProgramData "ProgramData"
  ${If} $TC_ProgramData == ""
    StrCpy $TC_ProgramData "C:\ProgramData"
  ${EndIf}
  ReadEnvStr $TC_LocalAppData "LOCALAPPDATA"
  ${If} $TC_LocalAppData == ""
    ; Sem LOCALAPPDATA no ambiente (caso extremo): usa o perfil do usuário.
    ReadEnvStr $TC_LocalAppData "USERPROFILE"
    StrCpy $TC_LocalAppData "$TC_LocalAppData\AppData\Local"
  ${EndIf}
!macroend

; ----------------------------------------------------------------------------
;  Garante um arquivo do cache de modelos: pula se já existe com o tamanho
;  exato (atualizações caem sempre aqui), senão baixa com progresso e confere
;  o SHA-256. Na primeira necessidade real de download, explica ao usuário o
;  que vai acontecer e por quê (transparência = confiança).
;    SNAPDIR  pasta relativa sob hub\ (models--...\snapshots\<hash>)
;    FILENAME nome do arquivo dentro da pasta
;    ASSET    nome do asset na release modelos-v1
;    SIZE     tamanho exato em bytes
;    SHA256   hash esperado (hex minúsculo)
; ----------------------------------------------------------------------------
!macro TC_FETCH_FILE SNAPDIR FILENAME ASSET SIZE SHA256
  ${If} $TC_Skip != 1
    StrCpy $9 "${TC_MODELS_HUB}\${SNAPDIR}\${FILENAME}"
    StrCpy $8 ""
    ${If} ${FileExists} "$9"
      FileOpen $7 "$9" r
      ${If} $7 != ""
        FileSeek $7 0 END $8
        FileClose $7
      ${EndIf}
    ${EndIf}
    ${If} $8 != "${SIZE}"
      ${If} $TC_Explained != 1
        StrCpy $TC_Explained 1
        ${IfNot} ${Silent}
          MessageBox MB_OKCANCEL|MB_ICONINFORMATION "O Transcreve usa modelos de inteligência artificial (aprox. 2,5 GB) para transcrever e analisar os áudios DENTRO do seu computador — nenhum áudio ou dado seu é enviado para a internet.$\r$\n$\r$\nComo esses arquivos são grandes demais para caber no instalador, eles serão baixados agora, uma única vez, da página oficial do projeto no GitHub. O progresso aparece na tela de instalação.$\r$\n$\r$\nAtualizações futuras do Transcreve NÃO repetem este download.$\r$\n$\r$\nClique em OK para baixar os modelos agora, ou em Cancelar para deixar para depois (basta executar este instalador novamente)." /SD IDOK IDOK +2
            StrCpy $TC_Skip 1
        ${EndIf}
      ${EndIf}
      ${If} $TC_Skip != 1
        DetailPrint "Baixando ${ASSET}…"
        CreateDirectory "${TC_MODELS_HUB}\${SNAPDIR}"
        NScurl::http GET "${TC_MODELS_URL}/${ASSET}" "$9" \
          /CANCEL /INSIST /RESUME /CONNECTTIMEOUT 30s \
          /STRING TITLE "Modelos de IA do Transcreve — download único" \
          /STRING TEXT "${ASSET}: @XFERSIZE@ de @FILESIZE@ (@SPEED@, restante: @TIMEREMAINING@)" \
          /END
        Pop $5
        ${If} $5 == "OK"
          DetailPrint "Verificando a integridade de ${ASSET}…"
          NScurl::sha256 -file "$9"
          Pop $5
          ${If} $5 != "${SHA256}"
            ; Arquivo corrompido ou adulterado: melhor nenhum modelo do que um
            ; modelo errado. Apaga para o próximo /RESUME começar do zero.
            Delete "$9"
            DetailPrint "Falha na verificação de ${ASSET} (hash não confere)."
            StrCpy $TC_Failed 1
            StrCpy $TC_Skip 1
          ${EndIf}
        ${Else}
          DetailPrint "Download de ${ASSET} não concluído: $5"
          StrCpy $TC_Failed 1
          StrCpy $TC_Skip 1
        ${EndIf}
      ${EndIf}
    ${EndIf}
  ${EndIf}
!macroend

; Grava hub\<modelo>\refs\main com o hash do snapshot — é assim que o
; huggingface_hub resolve "main" offline. Idempotente (regrava sempre).
!macro TC_WRITE_REF MODELDIR HASH
  CreateDirectory "${TC_MODELS_HUB}\${MODELDIR}\refs"
  FileOpen $7 "${TC_MODELS_HUB}\${MODELDIR}\refs\main" w
  ${If} $7 != ""
    FileWrite $7 "${HASH}"
    FileClose $7
  ${EndIf}
!macroend

; Lista TC_MODELS_FILES / TC_MODELS_REFS (gerada a partir do cache HF local).
!include "${__FILEDIR__}\models_manifest.nsh"

; ============================================================================
;  Pós-instalação: migra dados antigos e garante os modelos.
; ============================================================================
!macro NSIS_HOOK_POSTINSTALL
  !insertmacro TC_INIT_DIRS
  StrCpy $TC_Skip 0
  StrCpy $TC_Failed 0
  StrCpy $TC_Explained 0

  ; --- Migração (v0.1.0 guardava banco/áudios em <instalação>\data) ---------
  ; Move para %LOCALAPPDATA%\Transcreve\data, o local atual — resolve o órfão
  ; de desinstalação e mantém os dados do usuário fora de Program Files.
  ${If} ${FileExists} "$INSTDIR\data\*.*"
    ${IfNot} ${FileExists} "${TC_USERDATA}\data"
      CreateDirectory "${TC_USERDATA}"
      ClearErrors
      Rename "$INSTDIR\data" "${TC_USERDATA}\data"
      ${If} ${Errors}
        DetailPrint "Aviso: não movi os dados antigos de $INSTDIR\data (siga usando-os manualmente)."
      ${Else}
        DetailPrint "Dados de versões anteriores movidos para ${TC_USERDATA}\data."
      ${EndIf}
    ${EndIf}
  ${EndIf}

  ; --- Modelos de IA ---------------------------------------------------------
  DetailPrint "Conferindo os modelos de IA em ${TC_MODELS_ROOT}…"
  !insertmacro TC_MODELS_FILES

  ${If} $TC_Failed = 1
    ${IfNot} ${Silent}
      MessageBox MB_OK|MB_ICONEXCLAMATION "O download dos modelos de IA não foi concluído.$\r$\n$\r$\nO Transcreve foi instalado mesmo assim, mas a transcrição só funcionará quando os modelos estiverem no computador.$\r$\n$\r$\nPara concluir: conecte-se à internet e execute este instalador de novo — o download continua do ponto em que parou."
    ${EndIf}
    DetailPrint "Modelos de IA incompletos — rode o instalador novamente para retomar."
  ${ElseIf} $TC_Skip = 1
    DetailPrint "Download dos modelos adiado a pedido do usuário — rode o instalador novamente para concluir."
  ${Else}
    !insertmacro TC_MODELS_REFS
    DetailPrint "Modelos de IA prontos."
  ${EndIf}
!macroend

; ============================================================================
;  Pós-desinstalação: remoções opcionais, NUNCA durante atualização.
; ============================================================================
!macro NSIS_HOOK_POSTUNINSTALL
  !insertmacro TC_INIT_DIRS
  ${If} $UpdateMode <> 1
    ; Modelos: pergunta explícita, padrão "Não" (manter = atualizar/reinstalar
    ; sem baixar 2,5 GB de novo). Em modo silencioso, sempre mantém.
    ${IfNot} ${Silent}
    ${AndIf} ${FileExists} "${TC_MODELS_HUB}"
      MessageBox MB_YESNO|MB_ICONQUESTION|MB_DEFBUTTON2 "Deseja remover também os modelos de inteligência artificial (aprox. 2,5 GB) baixados pelo Transcreve?$\r$\n$\r$\nSe você pretende reinstalar ou atualizar o Transcreve mais tarde, escolha Não — assim não será preciso baixar tudo de novo." /SD IDNO IDNO +3
        RMDir /r "${TC_MODELS_ROOT}"
        RMDir "$TC_ProgramData\Transcreve"
    ${EndIf}

    ; Dados do usuário (projetos, transcrições, áudios): só se o usuário marcou
    ; "Excluir os dados do aplicativo" na tela de confirmação (checkbox nativo
    ; do Tauri; $DeleteAppDataCheckboxState vem do template).
    ${If} $DeleteAppDataCheckboxState = 1
      RMDir /r "${TC_USERDATA}\data"
      RMDir "${TC_USERDATA}"
      RMDir /r "$INSTDIR\data" ; resíduo de instalações antigas (v0.1.0)
    ${EndIf}
  ${EndIf}
!macroend
