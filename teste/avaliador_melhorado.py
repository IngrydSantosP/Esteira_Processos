"""
Avaliador Melhorado com Sistema de Personalização de Score
Permite que empresas personalizem os critérios e pesos de avaliação
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple


class AvaliadorPersonalizavel:
    """Avaliador que permite personalização completa dos critérios de score"""

    def __init__(self, configuracao_empresa: Optional[Dict[str, Any]] = None):
        """
        Inicializa o avaliador com configuração personalizada da empresa
        
        Args:
            configuracao_empresa: Dicionário com configurações personalizadas
        """
        self.configuracao = self._carregar_configuracao_padrao()
        if configuracao_empresa:
            self.configuracao = self._mesclar_configuracoes(
                self.configuracao, configuracao_empresa
            )

    def _carregar_configuracao_padrao(self) -> Dict[str, Any]:
        """Carrega a configuração padrão do sistema"""
        return {
            "pesos_categorias": {
                "salarial": {"peso": 20, "ativo": True},
                "requisitos": {"peso": 40, "ativo": True},
                "experiencia": {"peso": 15, "ativo": True},
                "diferenciais": {"peso": 10, "ativo": True},
                "localizacao": {"peso": 10, "ativo": True},
                "formacao": {"peso": 5, "ativo": True}
            },
            "criterios_personalizados": {
                "salarial": {
                    "faixas_bonus": [
                        {"multiplicador": 1.5, "pontos": 20},
                        {"multiplicador": 1.2, "pontos": 18},
                        {"multiplicador": 1.0, "pontos": 15}
                    ],
                    "faixas_penalidade": [
                        {"percentual": 0.1, "pontos": 12},
                        {"percentual": 0.2, "pontos": 8},
                        {"percentual": 0.3, "pontos": 5},
                        {"percentual": float('inf'), "pontos": 2}
                    ]
                },
                "requisitos": {
                    "tecnologias_personalizadas": [
                        'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node',
                        'php', 'laravel', 'django', 'flask', 'spring', 'docker', 'kubernetes',
                        'aws', 'azure', 'git', 'sql', 'mysql', 'postgresql', 'mongodb',
                        'html', 'css', 'bootstrap', 'tailwind', 'typescript'
                    ],
                    "habilidades_soft_personalizadas": [
                        'liderança', 'comunicação', 'trabalho em equipe', 'proatividade',
                        'criatividade', 'organização', 'responsabilidade', 'autonomia'
                    ],
                    "peso_tecnologias": 25,
                    "peso_habilidades_soft": 10,
                    "peso_experiencia_anos": 5
                },
                "experiencia": {
                    "limites_anos": {"senior": 8, "pleno": 4, "junior": 1},
                    "pontos_senioridade": {"senior": 15, "pleno": 12, "junior": 8, "iniciante": 5},
                    "palavras_senior": ['senior', 'sênior', 'líder', 'lead', 'coordenador', 'gerente', 'diretor', 'arquiteto'],
                    "palavras_pleno": ['pleno', 'analista', 'desenvolvedor', 'especialista'],
                    "palavras_junior": ['junior', 'júnior', 'estagiário', 'trainee', 'assistente']
                },
                "diferenciais": {
                    "certificacoes_personalizadas": ['certificação', 'certificado', 'aws', 'azure', 'google cloud', 'pmp', 'scrum master'],
                    "idiomas_personalizados": ['inglês', 'english', 'espanhol', 'francês', 'alemão'],
                    "pontos_certificacao": 2,
                    "pontos_idioma": 1.5,
                    "pontos_outros": 0.5
                },
                "localizacao": {
                    "pontos_remota": 10,
                    "pontos_presencial": {"mesma_cidade": 10, "mesmo_estado": 6, "regioes_proximas": 3, "outros": 0},
                    "pontos_hibrida": {"mesma_cidade": 8, "mesmo_estado": 5, "regioes_proximas": 2, "outros": 1}
                },
                "formacao": {
                    "pontos_formacao": {
                        "pos_requisita_possui": 5,
                        "superior_requisita_possui": 4,
                        "pos_possui": 4,
                        "superior_possui": 3,
                        "area_relacionada": 2,
                        "outros": 1
                    },
                    "formacoes_superiores": ['bacharelado', 'licenciatura', 'graduação', 'superior completo'],
                    "pos_graduacao": ['especialização', 'pós-graduação', 'mba', 'mestrado', 'doutorado'],
                    "areas_tech": ['computação', 'informática', 'sistemas', 'engenharia', 'tecnologia']
                }
            }
        }

    def _mesclar_configuracoes(self, padrao: Dict[str, Any], personalizada: Dict[str, Any]) -> Dict[str, Any]:
        """Mescla configuração personalizada com a padrão"""
        resultado = padrao.copy()
        
        # Mesclar pesos das categorias
        if "pesos_categorias" in personalizada:
            for categoria, config in personalizada["pesos_categorias"].items():
                if categoria in resultado["pesos_categorias"]:
                    resultado["pesos_categorias"][categoria].update(config)
        
        # Mesclar critérios personalizados
        if "criterios_personalizados" in personalizada:
            for categoria, criterios in personalizada["criterios_personalizados"].items():
                if categoria in resultado["criterios_personalizados"]:
                    resultado["criterios_personalizados"][categoria].update(criterios)
        
        return resultado

    def calcular_score(self, curriculo: str, requisitos: str, pretensao_salarial: float, 
                      salario_oferecido: float, diferenciais: Optional[str] = None,
                      candidato_endereco: Optional[str] = None, vaga_endereco: Optional[str] = None,
                      tipo_vaga: str = 'Presencial') -> Tuple[int, Dict[str, Any]]:
        """
        Calcula o score total do candidato com base na configuração personalizada
        
        Returns:
            Tuple[int, Dict[str, Any]]: Score total e detalhamento por categoria
        """
        score_total = 0
        detalhes_score = {}

        # Calcular score para cada categoria ativa
        categorias = self.configuracao["pesos_categorias"]

        if categorias["salarial"]["ativo"]:
            score_salarial = self._calcular_score_salarial(pretensao_salarial, salario_oferecido)
            score_total += score_salarial
            detalhes_score['salarial'] = {
                'score': score_salarial,
                'peso_maximo': categorias["salarial"]["peso"],
                'detalhes': self._obter_detalhes_salarial(pretensao_salarial, salario_oferecido)
            }

        if categorias["requisitos"]["ativo"]:
            score_requisitos = self._calcular_score_requisitos(curriculo, requisitos)
            score_total += score_requisitos
            detalhes_score['requisitos'] = {
                'score': score_requisitos,
                'peso_maximo': categorias["requisitos"]["peso"],
                'detalhes': self._obter_detalhes_requisitos(curriculo, requisitos)
            }

        if categorias["experiencia"]["ativo"]:
            score_experiencia = self._calcular_score_experiencia(curriculo)
            score_total += score_experiencia
            detalhes_score['experiencia'] = {
                'score': score_experiencia,
                'peso_maximo': categorias["experiencia"]["peso"],
                'detalhes': self._obter_detalhes_experiencia(curriculo)
            }

        if categorias["diferenciais"]["ativo"]:
            score_diferenciais = self._calcular_score_diferenciais(curriculo, diferenciais)
            score_total += score_diferenciais
            detalhes_score['diferenciais'] = {
                'score': score_diferenciais,
                'peso_maximo': categorias["diferenciais"]["peso"],
                'detalhes': self._obter_detalhes_diferenciais(curriculo, diferenciais)
            }

        if categorias["localizacao"]["ativo"]:
            score_localizacao = self._calcular_score_localizacao(candidato_endereco, vaga_endereco, tipo_vaga)
            score_total += score_localizacao
            detalhes_score['localizacao'] = {
                'score': score_localizacao,
                'peso_maximo': categorias["localizacao"]["peso"],
                'detalhes': self._obter_detalhes_localizacao(candidato_endereco, vaga_endereco, tipo_vaga)
            }

        if categorias["formacao"]["ativo"]:
            score_formacao = self._calcular_score_formacao(curriculo, requisitos)
            score_total += score_formacao
            detalhes_score['formacao'] = {
                'score': score_formacao,
                'peso_maximo': categorias["formacao"]["peso"],
                'detalhes': self._obter_detalhes_formacao(curriculo, requisitos)
            }

        return min(score_total, 100), detalhes_score

    def _calcular_score_salarial(self, pretensao_salarial: float, salario_oferecido: float) -> int:
        """Calcula score salarial baseado na configuração personalizada"""
        if not pretensao_salarial or not salario_oferecido:
            return 10  # Score neutro

        config = self.configuracao["criterios_personalizados"]["salarial"]

        if salario_oferecido >= pretensao_salarial:
            # Verificar faixas de bônus
            ratio = salario_oferecido / pretensao_salarial
            for faixa in config["faixas_bonus"]:
                if ratio >= faixa["multiplicador"]:
                    return faixa["pontos"]
        else:
            # Verificar faixas de penalidade
            diferenca_percentual = (pretensao_salarial - salario_oferecido) / salario_oferecido
            for faixa in config["faixas_penalidade"]:
                if diferenca_percentual <= faixa["percentual"]:
                    return faixa["pontos"]

        return 2  # Fallback

    def _calcular_score_requisitos(self, curriculo: str, requisitos: str) -> int:
        """Calcula score de requisitos baseado na configuração personalizada"""
        if not curriculo or not requisitos:
            return 0

        config = self.configuracao["criterios_personalizados"]["requisitos"]
        curriculo_lower = curriculo.lower()
        requisitos_lower = requisitos.lower()

        score = 0

        # Tecnologias
        tecnologias_vaga = [tech for tech in config["tecnologias_personalizadas"] if tech in requisitos_lower]
        tecnologias_candidato = [tech for tech in tecnologias_vaga if tech in curriculo_lower]
        
        if tecnologias_vaga:
            score += (len(tecnologias_candidato) / len(tecnologias_vaga)) * config["peso_tecnologias"]

        # Habilidades soft
        habilidades_vaga = [skill for skill in config["habilidades_soft_personalizadas"] if skill in requisitos_lower]
        habilidades_candidato = [skill for skill in habilidades_vaga if skill in curriculo_lower]
        
        if habilidades_vaga:
            score += (len(habilidades_candidato) / len(habilidades_vaga)) * config["peso_habilidades_soft"]

        # Experiência em anos
        anos_necessarios = self._extrair_anos_experiencia(requisitos_lower)
        anos_candidato = self._extrair_anos_experiencia_candidato(curriculo_lower)
        
        if anos_necessarios:
            if anos_candidato >= anos_necessarios:
                score += config["peso_experiencia_anos"]
            elif anos_candidato >= anos_necessarios * 0.7:
                score += config["peso_experiencia_anos"] * 0.6

        return min(int(score), self.configuracao["pesos_categorias"]["requisitos"]["peso"])

    def _calcular_score_experiencia(self, curriculo: str) -> int:
        """Calcula score de experiência baseado na configuração personalizada"""
        config = self.configuracao["criterios_personalizados"]["experiencia"]
        curriculo_lower = curriculo.lower()
        
        anos_experiencia = self._extrair_anos_experiencia_candidato(curriculo_lower)
        
        # Verificar palavras-chave de senioridade
        if any(palavra in curriculo_lower for palavra in config["palavras_senior"]) or anos_experiencia >= config["limites_anos"]["senior"]:
            return config["pontos_senioridade"]["senior"]
        elif any(palavra in curriculo_lower for palavra in config["palavras_pleno"]) or anos_experiencia >= config["limites_anos"]["pleno"]:
            return config["pontos_senioridade"]["pleno"]
        elif any(palavra in curriculo_lower for palavra in config["palavras_junior"]) or anos_experiencia >= config["limites_anos"]["junior"]:
            return config["pontos_senioridade"]["junior"]
        else:
            return config["pontos_senioridade"]["iniciante"]

    def _calcular_score_diferenciais(self, curriculo: str, diferenciais: Optional[str]) -> int:
        """Calcula score de diferenciais baseado na configuração personalizada"""
        if not diferenciais or not curriculo:
            return 0

        config = self.configuracao["criterios_personalizados"]["diferenciais"]
        curriculo_lower = curriculo.lower()
        diferenciais_lower = diferenciais.lower()

        score = 0

        # Certificações
        for cert in config["certificacoes_personalizadas"]:
            if cert in curriculo_lower and cert in diferenciais_lower:
                score += config["pontos_certificacao"]

        # Idiomas
        for idioma in config["idiomas_personalizados"]:
            if idioma in curriculo_lower and idioma in diferenciais_lower:
                score += config["pontos_idioma"]

        # Outros diferenciais
        palavras_diferenciais = self._extrair_palavras_chave(diferenciais_lower)
        for palavra in palavras_diferenciais:
            if palavra in curriculo_lower:
                score += config["pontos_outros"]

        return min(int(score), self.configuracao["pesos_categorias"]["diferenciais"]["peso"])

    def _calcular_score_localizacao(self, candidato_endereco: Optional[str], 
                                   vaga_endereco: Optional[str], tipo_vaga: str) -> int:
        """Calcula score de localização baseado na configuração personalizada"""
        config = self.configuracao["criterios_personalizados"]["localizacao"]
        
        if tipo_vaga == 'Remota':
            return config["pontos_remota"]

        if not candidato_endereco or not vaga_endereco:
            return 0

        candidato_lower = candidato_endereco.lower()
        vaga_lower = vaga_endereco.lower()

        candidato_cidade = self._extrair_cidade(candidato_lower)
        vaga_cidade = self._extrair_cidade(vaga_lower)
        candidato_estado = self._extrair_estado(candidato_lower)
        vaga_estado = self._extrair_estado(vaga_lower)

        pontos_config = config["pontos_presencial"] if tipo_vaga == 'Presencial' else config["pontos_hibrida"]

        if candidato_cidade and vaga_cidade and candidato_cidade == vaga_cidade:
            return pontos_config["mesma_cidade"]
        elif candidato_estado and vaga_estado and candidato_estado == vaga_estado:
            return pontos_config["mesmo_estado"]
        elif self._regioes_proximas(candidato_estado, vaga_estado):
            return pontos_config["regioes_proximas"]
        else:
            return pontos_config["outros"]

    def _calcular_score_formacao(self, curriculo: str, requisitos: str) -> int:
        """Calcula score de formação baseado na configuração personalizada"""
        config = self.configuracao["criterios_personalizados"]["formacao"]
        curriculo_lower = curriculo.lower()
        requisitos_lower = requisitos.lower()

        # Verificar se requisitos pedem formação específica
        pede_superior = any(form in requisitos_lower for form in config["formacoes_superiores"])
        pede_pos = any(pos in requisitos_lower for pos in config["pos_graduacao"])

        # Verificar formação do candidato
        tem_superior = any(form in curriculo_lower for form in config["formacoes_superiores"])
        tem_pos = any(pos in curriculo_lower for pos in config["pos_graduacao"])
        area_relacionada = any(area in curriculo_lower for area in config["areas_tech"])

        pontos = config["pontos_formacao"]

        if pede_pos and tem_pos:
            return pontos["pos_requisita_possui"]
        elif pede_superior and tem_superior:
            return pontos["superior_requisita_possui"]
        elif tem_pos:
            return pontos["pos_possui"]
        elif tem_superior:
            return pontos["superior_possui"]
        elif area_relacionada:
            return pontos["area_relacionada"]
        else:
            return pontos["outros"]

    # Métodos auxiliares para obter detalhes dos cálculos
    def _obter_detalhes_salarial(self, pretensao_salarial: float, salario_oferecido: float) -> Dict[str, Any]:
        """Retorna detalhes do cálculo salarial"""
        if not pretensao_salarial or not salario_oferecido:
            return {"explicacao": "Informação salarial não disponível, score neutro aplicado"}
        
        if salario_oferecido >= pretensao_salarial:
            ratio = salario_oferecido / pretensao_salarial
            return {
                "pretensao": pretensao_salarial,
                "oferecido": salario_oferecido,
                "ratio": ratio,
                "explicacao": f"Salário oferecido é {ratio:.1f}x a pretensão salarial"
            }
        else:
            diferenca_percentual = (pretensao_salarial - salario_oferecido) / salario_oferecido
            return {
                "pretensao": pretensao_salarial,
                "oferecido": salario_oferecido,
                "diferenca_percentual": diferenca_percentual,
                "explicacao": f"Pretensão salarial é {diferenca_percentual:.1%} acima do oferecido"
            }

    def _obter_detalhes_requisitos(self, curriculo: str, requisitos: str) -> Dict[str, Any]:
        """Retorna detalhes do cálculo de requisitos"""
        config = self.configuracao["criterios_personalizados"]["requisitos"]
        curriculo_lower = curriculo.lower()
        requisitos_lower = requisitos.lower()

        tecnologias_vaga = [tech for tech in config["tecnologias_personalizadas"] if tech in requisitos_lower]
        tecnologias_candidato = [tech for tech in tecnologias_vaga if tech in curriculo_lower]
        
        habilidades_vaga = [skill for skill in config["habilidades_soft_personalizadas"] if skill in requisitos_lower]
        habilidades_candidato = [skill for skill in habilidades_vaga if skill in curriculo_lower]
        
        anos_necessarios = self._extrair_anos_experiencia(requisitos_lower)
        anos_candidato = self._extrair_anos_experiencia_candidato(curriculo_lower)

        return {
            "tecnologias_vaga": tecnologias_vaga,
            "tecnologias_candidato": tecnologias_candidato,
            "habilidades_vaga": habilidades_vaga,
            "habilidades_candidato": habilidades_candidato,
            "anos_necessarios": anos_necessarios,
            "anos_candidato": anos_candidato
        }

    def _obter_detalhes_experiencia(self, curriculo: str) -> Dict[str, Any]:
        """Retorna detalhes do cálculo de experiência"""
        config = self.configuracao["criterios_personalizados"]["experiencia"]
        curriculo_lower = curriculo.lower()
        anos_experiencia = self._extrair_anos_experiencia_candidato(curriculo_lower)
        
        nivel = "iniciante"
        if any(palavra in curriculo_lower for palavra in config["palavras_senior"]) or anos_experiencia >= config["limites_anos"]["senior"]:
            nivel = "senior"
        elif any(palavra in curriculo_lower for palavra in config["palavras_pleno"]) or anos_experiencia >= config["limites_anos"]["pleno"]:
            nivel = "pleno"
        elif any(palavra in curriculo_lower for palavra in config["palavras_junior"]) or anos_experiencia >= config["limites_anos"]["junior"]:
            nivel = "junior"

        return {
            "nivel_identificado": nivel,
            "anos_experiencia": anos_experiencia,
            "explicacao": f"Nível {nivel} identificado com base em {anos_experiencia} anos de experiência"
        }

    def _obter_detalhes_diferenciais(self, curriculo: str, diferenciais: Optional[str]) -> Dict[str, Any]:
        """Retorna detalhes do cálculo de diferenciais"""
        if not diferenciais or not curriculo:
            return {"explicacao": "Nenhum diferencial especificado"}

        config = self.configuracao["criterios_personalizados"]["diferenciais"]
        curriculo_lower = curriculo.lower()
        diferenciais_lower = diferenciais.lower()

        certificacoes_encontradas = [cert for cert in config["certificacoes_personalizadas"] 
                                   if cert in curriculo_lower and cert in diferenciais_lower]
        idiomas_encontrados = [idioma for idioma in config["idiomas_personalizados"] 
                             if idioma in curriculo_lower and idioma in diferenciais_lower]

        return {
            "certificacoes_encontradas": certificacoes_encontradas,
            "idiomas_encontrados": idiomas_encontrados,
            "explicacao": f"Encontradas {len(certificacoes_encontradas)} certificações e {len(idiomas_encontrados)} idiomas"
        }

    def _obter_detalhes_localizacao(self, candidato_endereco: Optional[str], 
                                   vaga_endereco: Optional[str], tipo_vaga: str) -> Dict[str, Any]:
        """Retorna detalhes do cálculo de localização"""
        if tipo_vaga == 'Remota':
            return {"explicacao": "Vaga remota, score máximo aplicado"}

        if not candidato_endereco or not vaga_endereco:
            return {"explicacao": "Informação de endereço não disponível"}

        candidato_cidade = self._extrair_cidade(candidato_endereco.lower())
        vaga_cidade = self._extrair_cidade(vaga_endereco.lower())
        candidato_estado = self._extrair_estado(candidato_endereco.lower())
        vaga_estado = self._extrair_estado(vaga_endereco.lower())

        return {
            "candidato_cidade": candidato_cidade,
            "vaga_cidade": vaga_cidade,
            "candidato_estado": candidato_estado,
            "vaga_estado": vaga_estado,
            "tipo_vaga": tipo_vaga
        }

    def _obter_detalhes_formacao(self, curriculo: str, requisitos: str) -> Dict[str, Any]:
        """Retorna detalhes do cálculo de formação"""
        config = self.configuracao["criterios_personalizados"]["formacao"]
        curriculo_lower = curriculo.lower()
        requisitos_lower = requisitos.lower()

        pede_superior = any(form in requisitos_lower for form in config["formacoes_superiores"])
        pede_pos = any(pos in requisitos_lower for pos in config["pos_graduacao"])
        tem_superior = any(form in curriculo_lower for form in config["formacoes_superiores"])
        tem_pos = any(pos in curriculo_lower for pos in config["pos_graduacao"])

        return {
            "pede_superior": pede_superior,
            "pede_pos": pede_pos,
            "tem_superior": tem_superior,
            "tem_pos": tem_pos,
            "explicacao": f"Requisitos: Superior={pede_superior}, Pós={pede_pos}. Candidato: Superior={tem_superior}, Pós={tem_pos}"
        }

    # Métodos auxiliares (reutilizados do código original)
    def _extrair_anos_experiencia(self, texto: str) -> int:
        """Extrai anos de experiência requisitados"""
        patterns = [
            r'(\d+)\s*anos?\s*de\s*experiência',
            r'experiência\s*de\s*(\d+)\s*anos?',
            r'mínimo\s*(\d+)\s*anos?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto)
            if match:
                return int(match.group(1))
        return 0

    def _extrair_anos_experiencia_candidato(self, curriculo: str) -> int:
        """Estima anos de experiência do candidato"""
        # Procurar por datas no currículo
        dates_pattern = r'(20\d{2})'
        dates = re.findall(dates_pattern, curriculo)
        
        if dates:
            dates = [int(d) for d in dates]
            anos_min = min(dates)
            ano_atual = datetime.now().year
            return max(0, ano_atual - anos_min)
        
        # Se não encontrar datas, procurar por menções explícitas
        exp_patterns = [
            r'(\d+)\s*anos?\s*de\s*experiência',
            r'experiência\s*de\s*(\d+)\s*anos?'
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, curriculo)
            if match:
                return int(match.group(1))
        
        return 0

    def _extrair_cidade(self, endereco: str) -> Optional[str]:
        """Extrai cidade do endereço"""
        cidades_conhecidas = [
            'são paulo', 'rio de janeiro', 'belo horizonte', 'salvador', 
            'brasília', 'fortaleza', 'recife', 'porto alegre', 'curitiba'
        ]
        for cidade in cidades_conhecidas:
            if cidade in endereco:
                return cidade
        return None

    def _extrair_estado(self, endereco: str) -> Optional[str]:
        """Extrai estado do endereço"""
        estados = {
            'sp': 'são paulo', 'rj': 'rio de janeiro', 'mg': 'minas gerais',
            'ba': 'bahia', 'df': 'distrito federal', 'ce': 'ceará',
            'pe': 'pernambuco', 'rs': 'rio grande do sul', 'pr': 'paraná'
        }
        
        for sigla, nome in estados.items():
            if sigla in endereco or nome in endereco:
                return nome
        return None

    def _regioes_proximas(self, estado1: Optional[str], estado2: Optional[str]) -> bool:
        """Verifica se estados são de regiões próximas"""
        if not estado1 or not estado2:
            return False
            
        regioes = {
            'sudeste': ['são paulo', 'rio de janeiro', 'minas gerais', 'espírito santo'],
            'sul': ['rio grande do sul', 'paraná', 'santa catarina'],
            'nordeste': ['bahia', 'ceará', 'pernambuco', 'paraíba', 'rio grande do norte']
        }
        
        for regiao, estados in regioes.items():
            if estado1 in estados and estado2 in estados:
                return True
        return False

    def _extrair_palavras_chave(self, texto: str) -> List[str]:
        """Extrai palavras-chave relevantes do texto"""
        palavras = re.findall(r'\b\w+\b', texto.lower())
        stopwords = {'a', 'o', 'e', 'de', 'da', 'do', 'em', 'um', 'uma', 'para', 'com', 'por', 'que', 'na', 'no'}
        palavras_filtradas = [p for p in palavras if len(p) > 2 and p not in stopwords]
        return palavras_filtradas

    def gerar_relatorio_detalhado(self, curriculo: str, requisitos: str, pretensao_salarial: float,
                                 salario_oferecido: float, diferenciais: Optional[str] = None,
                                 candidato_endereco: Optional[str] = None, vaga_endereco: Optional[str] = None,
                                 tipo_vaga: str = 'Presencial', nome_candidato: str = "Candidato",
                                 titulo_vaga: str = "Vaga", empresa_nome: str = "Empresa") -> str:
        """
        Gera um relatório detalhado da avaliação do candidato
        """
        score_total, detalhes = self.calcular_score(
            curriculo, requisitos, pretensao_salarial, salario_oferecido,
            diferenciais, candidato_endereco, vaga_endereco, tipo_vaga
        )

        relatorio = f"""# Relatório de Avaliação de Candidato

## Informações da Vaga
- **Título da Vaga:** {titulo_vaga}
- **Empresa:** {empresa_nome}
- **Requisitos Principais:** {requisitos[:200]}{'...' if len(requisitos) > 200 else ''}
- **Salário Oferecido:** R$ {salario_oferecido:,.2f}
- **Tipo de Vaga:** {tipo_vaga}

## Informações do Candidato
- **Nome do Candidato:** {nome_candidato}
- **Pretensão Salarial:** R$ {pretensao_salarial:,.2f}
- **Endereço do Candidato:** {candidato_endereco or 'Não informado'}

## Score Total: {score_total}/100

## Detalhamento do Score por Categoria

"""

        for categoria, info in detalhes.items():
            relatorio += f"""### {categoria.title()}: {info['score']}/{info['peso_maximo']}
- **Explicação:** {info['detalhes'].get('explicacao', 'Cálculo baseado nos critérios configurados')}

"""

        relatorio += f"""
---
*Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*
*Configuração de score: {'Personalizada' if self.configuracao != self._carregar_configuracao_padrao() else 'Padrão'}*
"""

        return relatorio


# Função de compatibilidade com o sistema existente
def criar_avaliador(configuracao_empresa: Optional[Dict[str, Any]] = None):
    """
    Função de compatibilidade para criar um avaliador personalizado
    """
    return AvaliadorPersonalizavel(configuracao_empresa)


# Exemplo de uso
if __name__ == "__main__":
    # Configuração personalizada de exemplo
    config_exemplo = {
        "pesos_categorias": {
            "salarial": {"peso": 15, "ativo": True},
            "requisitos": {"peso": 50, "ativo": True},
            "experiencia": {"peso": 20, "ativo": True},
            "diferenciais": {"peso": 10, "ativo": True},
            "localizacao": {"peso": 5, "ativo": True},
            "formacao": {"peso": 0, "ativo": False}  # Desativada
        }
    }

    avaliador = AvaliadorPersonalizavel(config_exemplo)
    
    # Exemplo de cálculo
    curriculo_exemplo = """
    João Silva, desenvolvedor Python sênior com 8 anos de experiência.
    Especialista em Django, Flask, Docker, AWS. Graduado em Ciência da Computação.
    Certificação AWS Solutions Architect. Fluente em inglês.
    Experiência em liderança de equipes e projetos ágeis.
    """
    
    requisitos_exemplo = """
    Desenvolvedor Python sênior com mínimo 5 anos de experiência.
    Conhecimento em Django, Docker, AWS. Inglês intermediário.
    Experiência com metodologias ágeis e liderança de equipe.
    """
    
    score, detalhes = avaliador.calcular_score(
        curriculo_exemplo, requisitos_exemplo, 8000, 10000,
        "Inglês fluente, certificação AWS", "São Paulo, SP", "São Paulo, SP", "Presencial"
    )
    
    print(f"Score Total: {score}")
    print(f"Detalhes: {json.dumps(detalhes, indent=2, ensure_ascii=False)}")

