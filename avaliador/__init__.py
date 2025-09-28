
from .avaliador_local import AvaliadorLocal
from .avaliador_hf import AvaliadorHuggingFace

def get_avaliador(modo_ia):
    """Factory para criar o avaliador baseado no modo configurado"""
    if modo_ia == 'huggingface':
        return AvaliadorHuggingFace()
    else:
        return AvaliadorLocal()

def criar_avaliador(modo_ia):
    """Alias para get_avaliador para compatibilidade"""
    return get_avaliador(modo_ia)
