"""
Configuração e detecção de hardware do sidecar.

Centraliza a escolha de device (CPU/GPU) e de modelo, respeitando o requisito de
autodetecção com possibilidade de override pelo usuário (Configurações da UI).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Device = Literal["auto", "cpu", "cuda"]
ComputeType = Literal["int8", "int8_float16", "float16", "float32"]


@dataclass(frozen=True)
class HardwareInfo:
    """Resumo do hardware disponível para a UI exibir e decidir o device."""

    has_cuda: bool
    cuda_device_name: str | None
    total_ram_gb: float | None


def detect_hardware() -> HardwareInfo:
    """
    Detecta GPU CUDA e RAM. Tolerante a ausência de torch (sidecar ainda sem IA),
    para que o /health e a UI funcionem antes de instalar o WhisperX.
    """
    has_cuda = False
    cuda_name: str | None = None
    try:
        import torch  # type: ignore

        has_cuda = bool(torch.cuda.is_available())
        if has_cuda:
            cuda_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    total_ram_gb: float | None = None
    try:
        import psutil  # type: ignore

        total_ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    except Exception:
        try:
            import os

            pages = os.sysconf("SC_PHYS_PAGES")  # type: ignore[attr-defined]
            page_size = os.sysconf("SC_PAGE_SIZE")  # type: ignore[attr-defined]
            total_ram_gb = round(pages * page_size / (1024**3), 1)
        except Exception:
            pass

    return HardwareInfo(
        has_cuda=has_cuda,
        cuda_device_name=cuda_name,
        total_ram_gb=total_ram_gb,
    )


def resolve_device(requested: Device) -> str:
    """Converte a escolha do usuário ('auto'/'cpu'/'cuda') no device efetivo."""
    if requested == "cpu":
        return "cpu"
    if requested == "cuda":
        return "cuda"
    # auto
    hw = detect_hardware()
    return "cuda" if hw.has_cuda else "cpu"


def default_compute_type(device: str) -> ComputeType:
    """Tipo de cálculo adequado: float16 em GPU, int8 em CPU (mais leve)."""
    return "float16" if device == "cuda" else "int8"


def suggest_model(requested_model: str | None) -> str:
    """
    Modelo padrão é 'large-v3-turbo'. Em máquinas com pouca RAM, sugerimos um
    modelo menor automaticamente quando o usuário não fixou um.
    """
    if requested_model:
        return requested_model
    hw = detect_hardware()
    if hw.total_ram_gb is not None and hw.total_ram_gb < 9 and not hw.has_cuda:
        return "small"
    return "large-v3-turbo"
