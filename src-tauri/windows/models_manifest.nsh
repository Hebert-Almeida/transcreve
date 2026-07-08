; ==========================================================================
; GERADO por scripts/release.py — NÃO EDITE À MÃO.
; Lista de arquivos dos modelos (baixados pelo instalador) e os refs/main.
; Fonte: cache Hugging Face local (~/.cache/huggingface/hub).
; Release dos modelos: modelos-v1
; ==========================================================================

; Baixa/verifica cada arquivo. Assinatura:
;   TC_FETCH_FILE SNAPDIR FILENAME ASSET SIZE SHA256
!macro TC_MODELS_FILES
  ; --- large-v3-turbo (models--mobiuslabsgmbh--faster-whisper-large-v3-turbo) ---
  !insertmacro TC_FETCH_FILE "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo\snapshots\0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf" "config.json" "large-v3-turbo--config.json" 2263 "b0253ea6c0d3bea6b1e19e91a02acfd3b53f4467362efcb5a3e6b16c9b3a9b7e"
  !insertmacro TC_FETCH_FILE "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo\snapshots\0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf" "model.bin" "large-v3-turbo--model.bin" 1617884929 "e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da"
  !insertmacro TC_FETCH_FILE "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo\snapshots\0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf" "preprocessor_config.json" "large-v3-turbo--preprocessor_config.json" 340 "7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711"
  !insertmacro TC_FETCH_FILE "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo\snapshots\0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf" "tokenizer.json" "large-v3-turbo--tokenizer.json" 2710337 "297b13372ac43916285644fb9687add3cc62ee2a1adb60da3dc25cc94c1871fd"
  !insertmacro TC_FETCH_FILE "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo\snapshots\0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf" "vocabulary.json" "large-v3-turbo--vocabulary.json" 1068114 "c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1"
  ; --- small (models--Systran--faster-whisper-small) ---
  !insertmacro TC_FETCH_FILE "models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120" "config.json" "small--config.json" 2370 "b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828"
  !insertmacro TC_FETCH_FILE "models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120" "model.bin" "small--model.bin" 483546902 "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671"
  !insertmacro TC_FETCH_FILE "models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120" "tokenizer.json" "small--tokenizer.json" 2203239 "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"
  !insertmacro TC_FETCH_FILE "models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120" "vocabulary.txt" "small--vocabulary.txt" 459861 "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913"
  ; --- sentiment-pt (models--pysentimiento--bertweet-pt-sentiment) ---
  !insertmacro TC_FETCH_FILE "models--pysentimiento--bertweet-pt-sentiment\snapshots\726612815d49447cbfe3f55bbfc2993c1f5fad10" "added_tokens.json" "sentiment-pt--added_tokens.json" 22 "73912929ac0f567224032a57d3b3e6a54613afcdc851aba46c3059b4d4ef5254"
  !insertmacro TC_FETCH_FILE "models--pysentimiento--bertweet-pt-sentiment\snapshots\726612815d49447cbfe3f55bbfc2993c1f5fad10" "bpe.codes" "sentiment-pt--bpe.codes" 1042340 "398a63a3ea4137a5a4205e5913cf8e0cccc4dee7a461dc385ea50546a0f543c4"
  !insertmacro TC_FETCH_FILE "models--pysentimiento--bertweet-pt-sentiment\snapshots\726612815d49447cbfe3f55bbfc2993c1f5fad10" "config.json" "sentiment-pt--config.json" 952 "7f0b6fbd123333201c8a60db66c159ad204e236bccfd2c1184df70c70a4fda73"
  !insertmacro TC_FETCH_FILE "models--pysentimiento--bertweet-pt-sentiment\snapshots\726612815d49447cbfe3f55bbfc2993c1f5fad10" "model.safetensors" "sentiment-pt--model.safetensors" 539646660 "ff666dd48ce086345516ff2e2ee1e38a90235505d1193ed64461cf295875bace"
  !insertmacro TC_FETCH_FILE "models--pysentimiento--bertweet-pt-sentiment\snapshots\726612815d49447cbfe3f55bbfc2993c1f5fad10" "special_tokens_map.json" "sentiment-pt--special_tokens_map.json" 167 "d05497f1da52c5e09554c0cd874037a083e1dc1b9cfd48034d1c717f1afc07a7"
  !insertmacro TC_FETCH_FILE "models--pysentimiento--bertweet-pt-sentiment\snapshots\726612815d49447cbfe3f55bbfc2993c1f5fad10" "tokenizer_config.json" "sentiment-pt--tokenizer_config.json" 562 "b5c75a92c5ffb7276ec8e9ecff387d631faddb7be75a296e35c08979004e1400"
  !insertmacro TC_FETCH_FILE "models--pysentimiento--bertweet-pt-sentiment\snapshots\726612815d49447cbfe3f55bbfc2993c1f5fad10" "vocab.txt" "sentiment-pt--vocab.txt" 799173 "fb6b15bc5d77bef93b8ddbd86e32bda786d4394029b2a9a1d060edb58a7890f1"
!macroend

; Grava refs\main de cada modelo (resolução offline do 'main').
;   TC_WRITE_REF MODELDIR HASH
!macro TC_MODELS_REFS
  !insertmacro TC_WRITE_REF "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo" "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf"
  !insertmacro TC_WRITE_REF "models--Systran--faster-whisper-small" "536b0662742c02347bc0e980a01041f333bce120"
  !insertmacro TC_WRITE_REF "models--pysentimiento--bertweet-pt-sentiment" "726612815d49447cbfe3f55bbfc2993c1f5fad10"
!macroend
