
from .base_avaliador import BaseAvaliador

class AvaliadorLocal(BaseAvaliador):
    """Avaliador que usa método local simples de matching por palavras-chave"""
    
    def calcular_score(self, texto_curriculo, requisitos_vaga, pretensao_salarial, salario_oferecido):
        """Calcula score usando método local simples"""
        score_requisitos = self.calcular_score_requisitos(texto_curriculo, requisitos_vaga)
        score_salarial = self.calcular_score_salarial(pretensao_salarial, salario_oferecido)
        
        score_total = score_requisitos + score_salarial
        return min(score_total, 100)
    
    def calcular_score_requisitos(self, texto_curriculo, requisitos_vaga):
        """Calcula score baseado nos requisitos (70% do peso total)"""
        if not texto_curriculo or not requisitos_vaga:
            return 0
        
        # Divide os requisitos e conta quantos aparecem no currículo
        requisitos_lista = [req.strip().lower() for req in requisitos_vaga.split(',') if req.strip()]
        texto_curriculo_lower = texto_curriculo.lower()
        
        if not requisitos_lista:
            return 35  # Score médio se não tiver requisitos
        
        requisitos_encontrados = 0
        for requisito in requisitos_lista:
            if requisito in texto_curriculo_lower:
                requisitos_encontrados += 1
        
        # Score baseado na porcentagem de requisitos encontrados
        porcentagem_match = requisitos_encontrados / len(requisitos_lista)
        return porcentagem_match * 70
