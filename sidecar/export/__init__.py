"""Exportadores do Transcreve (transcrição e resultados de análise).

Cada exportador devolve `(bytes, media_type, filename)` para o handler HTTP
servir com `Content-Disposition`. O frontend escolhe onde gravar (save dialog);
o sidecar nunca escreve fora da pasta de dados. Formatos tabulares (CSV/TSV/JSON)
miram o RStudio; SRT/VTT reaproveitam a transcrição em vídeo; DOCX/PDF geram
relatório legível.
"""
