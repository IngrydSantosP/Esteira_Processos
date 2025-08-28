from utils.ia_assistant import IAAssistant
from functools import lru_cache

# Inicializar assistente IA (lazy loading)
_ia_assistant = None

def get_ia_assistant():
    global _ia_assistant
    if _ia_assistant is None:
        _ia_assistant = IAAssistant()
    return _ia_assistant

@lru_cache(maxsize=100)
def gerar_feedback_ia_vaga_cached(total, alta_compatibilidade, media_compatibilidade, baixa_compatibilidade):
    """Versão cached do feedback IA"""
    # Garantir que todos os valores são inteiros
    total = total or 0
    alta_compatibilidade = alta_compatibilidade or 0
    media_compatibilidade = media_compatibilidade or 0
    baixa_compatibilidade = baixa_compatibilidade or 0

    if total == 0:
        return {
            'texto': 'Nenhum candidato ainda',
            'cor': 'text-gray-500',
            'icone': '📋'
        }

    if alta_compatibilidade > 0:
        percentual_alto = (alta_compatibilidade / total) * 100
        if percentual_alto >= 50:
            return {
                'texto':
                f'{alta_compatibilidade} candidato(s) com perfil excelente (80%+)',
                'cor': 'text-green-600',
                'icone': '🎯'
            }
        else:
            return {
                'texto':
                f'{alta_compatibilidade} candidato(s) muito compatível(eis)',
                'cor': 'text-green-500',
                'icone': '✅'
            }

    if media_compatibilidade > 0:
        return {
            'texto':
            f'{media_compatibilidade} candidato(s) com bom potencial (60-79%)',
            'cor': 'text-yellow-600',
            'icone': '⚡'
        }

    return {
        'texto': f'{total} candidato(s) - revisar requisitos da vaga',
        'cor': 'text-orange-500',
        'icone': '⚠️'
    }


