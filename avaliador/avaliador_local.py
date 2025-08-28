
from .base_avaliador import BaseAvaliador
import re
from datetime import datetime

class AvaliadorLocal(BaseAvaliador):
    """Avaliador que usa método local avançado com múltiplos critérios"""

    def calcular_score(self, curriculo, requisitos, pretensao_salarial, salario_oferecido, 
                      diferenciais=None, candidato_endereco=None, vaga_endereco=None, tipo_vaga='Presencial'):
        """Calcula score avançado do candidato baseado em critérios abrangentes"""
        score = 0
        detalhes_score = {}

        # 1. Score baseado em compatibilidade salarial (20%)
        score_salarial = self._calcular_score_salarial(pretensao_salarial, salario_oferecido)
        score += score_salarial
        detalhes_score['salarial'] = score_salarial

        # 2. Score baseado em requisitos obrigatórios (40%)
        score_requisitos = self._calcular_score_requisitos_avancado(curriculo, requisitos)
        score += score_requisitos
        detalhes_score['requisitos'] = score_requisitos

        # 3. Score baseado em experiência e senioridade (15%)
        score_experiencia = self._calcular_score_experiencia(curriculo)
        score += score_experiencia
        detalhes_score['experiencia'] = score_experiencia

        # 4. Score baseado em diferenciais (10%)
        score_diferenciais = self._calcular_score_diferenciais(curriculo, diferenciais)
        score += score_diferenciais
        detalhes_score['diferenciais'] = score_diferenciais

        # 5. Score baseado em proximidade geográfica (10%)
        score_localizacao = self._calcular_score_localizacao(candidato_endereco, vaga_endereco, tipo_vaga)
        score += score_localizacao
        detalhes_score['localizacao'] = score_localizacao

        # 6. Score baseado em formação acadêmica (5%)
        score_formacao = self._calcular_score_formacao(curriculo, requisitos)
        score += score_formacao
        detalhes_score['formacao'] = score_formacao

        return min(score, 100)

    def _calcular_score_salarial(self, pretensao_salarial, salario_oferecido):
        """Calcula score salarial com lógica mais sofisticada"""
        if not pretensao_salarial or not salario_oferecido:
            return 10  # Score neutro
        
        if salario_oferecido >= pretensao_salarial:
            # Bônus se salário oferecido for muito superior
            ratio = salario_oferecido / pretensao_salarial
            if ratio >= 1.5:  # 50% acima
                return 20
            elif ratio >= 1.2:  # 20% acima
                return 18
            else:
                return 15
        else:
            # Penalização gradual se pretensão for acima
            diferenca_percentual = (pretensao_salarial - salario_oferecido) / salario_oferecido
            if diferenca_percentual <= 0.1:  # até 10% acima
                return 12
            elif diferenca_percentual <= 0.2:  # até 20% acima
                return 8
            elif diferenca_percentual <= 0.3:  # até 30% acima
                return 5
            else:
                return 2

    def _calcular_score_requisitos_avancado(self, curriculo, requisitos):
        """Calcula score de requisitos com análise semântica básica"""
        if not curriculo or not requisitos:
            return 0

        curriculo_lower = curriculo.lower()
        requisitos_lower = requisitos.lower()

        # Extrair tecnologias e habilidades
        tecnologias = self._extrair_tecnologias(requisitos_lower)
        habilidades_soft = self._extrair_habilidades_soft(requisitos_lower)
        experiencia_anos = self._extrair_anos_experiencia(requisitos_lower)

        score = 0
        matches_tecnologias = 0
        matches_soft = 0

        # Verificar tecnologias (peso maior)
        for tech in tecnologias:
            if tech in curriculo_lower:
                matches_tecnologias += 1

        if tecnologias:
            score += (matches_tecnologias / len(tecnologias)) * 25

        # Verificar habilidades soft
        for skill in habilidades_soft:
            if skill in curriculo_lower:
                matches_soft += 1

        if habilidades_soft:
            score += (matches_soft / len(habilidades_soft)) * 10

        # Verificar experiência em anos
        if experiencia_anos:
            anos_candidato = self._extrair_anos_experiencia_candidato(curriculo_lower)
            if anos_candidato >= experiencia_anos:
                score += 5
            elif anos_candidato >= experiencia_anos * 0.7:  # 70% da experiência pedida
                score += 3

        return min(score, 40)

    def _calcular_score_experiencia(self, curriculo):
        """Analisa o nível de senioridade baseado no currículo"""
        curriculo_lower = curriculo.lower()
        score = 0

        # Palavras que indicam senioridade
        palavras_senior = ['senior', 'sênior', 'líder', 'lead', 'coordenador', 'gerente', 'diretor', 'arquiteto']
        palavras_pleno = ['pleno', 'analista', 'desenvolvedor', 'especialista']
        palavras_junior = ['junior', 'júnior', 'estagiário', 'trainee', 'assistente']

        # Contar anos de experiência aproximados
        anos_experiencia = self._extrair_anos_experiencia_candidato(curriculo_lower)

        if any(palavra in curriculo_lower for palavra in palavras_senior) or anos_experiencia >= 8:
            score = 15  # Senior
        elif any(palavra in curriculo_lower for palavra in palavras_pleno) or anos_experiencia >= 4:
            score = 12  # Pleno
        elif any(palavra in curriculo_lower for palavra in palavras_junior) or anos_experiencia >= 1:
            score = 8   # Junior
        else:
            score = 5   # Iniciante

        return score

    def _calcular_score_diferenciais(self, curriculo, diferenciais):
        """Calcula score baseado em diferenciais"""
        if not diferenciais or not curriculo:
            return 0

        curriculo_lower = curriculo.lower()
        diferenciais_lower = diferenciais.lower()

        # Certificações e cursos
        certificacoes = ['certificação', 'certificado', 'aws', 'azure', 'google cloud', 'pmp', 'scrum master']
        idiomas = ['inglês', 'english', 'espanhol', 'francês', 'alemão']
        outros_diferenciais = self._extrair_palavras_chave(diferenciais_lower)

        score = 0
        matches = 0

        # Verificar certificações
        for cert in certificacoes:
            if cert in curriculo_lower and cert in diferenciais_lower:
                score += 2
                matches += 1

        # Verificar idiomas
        for idioma in idiomas:
            if idioma in curriculo_lower and idioma in diferenciais_lower:
                score += 1.5
                matches += 1

        # Verificar outros diferenciais
        for diferencial in outros_diferenciais:
            if diferencial in curriculo_lower:
                score += 0.5
                matches += 1

        return min(score, 10)

    def _calcular_score_localizacao(self, candidato_endereco, vaga_endereco, tipo_vaga):
        """Calcula score de localização com análise geográfica avançada"""
        if not candidato_endereco or not vaga_endereco:
            return 3 if tipo_vaga == 'Remota' else 0

        candidato_lower = candidato_endereco.lower()
        vaga_lower = vaga_endereco.lower()

        # Se for remota, dar score máximo
        if tipo_vaga == 'Remota':
            return 10

        # Extrair cidade e estado
        candidato_cidade = self._extrair_cidade(candidato_lower)
        vaga_cidade = self._extrair_cidade(vaga_lower)
        candidato_estado = self._extrair_estado(candidato_lower)
        vaga_estado = self._extrair_estado(vaga_lower)

        score = 0

        # Mesma cidade
        if candidato_cidade and vaga_cidade and candidato_cidade == vaga_cidade:
            score = 10 if tipo_vaga == 'Presencial' else 8
        # Mesmo estado
        elif candidato_estado and vaga_estado and candidato_estado == vaga_estado:
            score = 6 if tipo_vaga == 'Presencial' else 5
        # Regiões próximas (simplificado)
        elif self._regioes_proximas(candidato_estado, vaga_estado):
            score = 3 if tipo_vaga == 'Presencial' else 2
        else:
            score = 1 if tipo_vaga == 'Híbrida' else 0

        return score

    def _calcular_score_formacao(self, curriculo, requisitos):
        """Analisa formação acadêmica"""
        curriculo_lower = curriculo.lower()
        requisitos_lower = requisitos.lower()

        formacoes_superiores = ['bacharelado', 'licenciatura', 'graduação', 'superior completo']
        pos_graduacao = ['especialização', 'pós-graduação', 'mba', 'mestrado', 'doutorado']
        areas_tech = ['computação', 'informática', 'sistemas', 'engenharia', 'tecnologia']

        score = 0

        # Verificar se requisitos pedem formação específica
        pede_superior = any(form in requisitos_lower for form in formacoes_superiores)
        pede_pos = any(pos in requisitos_lower for pos in pos_graduacao)

        # Verificar formação do candidato
        tem_superior = any(form in curriculo_lower for form in formacoes_superiores)
        tem_pos = any(pos in curriculo_lower for pos in pos_graduacao)
        area_relacionada = any(area in curriculo_lower for area in areas_tech)

        if pede_pos and tem_pos:
            score = 5
        elif pede_superior and tem_superior:
            score = 4
        elif tem_pos:
            score = 4
        elif tem_superior:
            score = 3
        elif area_relacionada:
            score = 2
        else:
            score = 1

        return score

    def _extrair_tecnologias(self, texto):
        """Extrai tecnologias mencionadas no texto"""
        tecnologias_comuns = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node',
            'php', 'laravel', 'django', 'flask', 'spring', 'docker', 'kubernetes',
            'aws', 'azure', 'git', 'sql', 'mysql', 'postgresql', 'mongodb',
            'html', 'css', 'bootstrap', 'tailwind', 'typescript'
        ]
        return [tech for tech in tecnologias_comuns if tech in texto]

    def _extrair_habilidades_soft(self, texto):
        """Extrai habilidades soft mencionadas"""
        soft_skills = [
            'liderança', 'comunicação', 'trabalho em equipe', 'proatividade',
            'criatividade', 'organização', 'responsabilidade', 'autonomia'
        ]
        return [skill for skill in soft_skills if skill in texto]

    def _extrair_anos_experiencia(self, texto):
        """Extrai anos de experiência requisitados"""
        import re
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

    def _extrair_anos_experiencia_candidato(self, curriculo):
        """Estima anos de experiência do candidato"""
        import re
        
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

    def _extrair_cidade(self, endereco):
        """Extrai cidade do endereço"""
        # Simplificado - na prática seria mais robusto
        cidades_conhecidas = [
            'são paulo', 'rio de janeiro', 'belo horizonte', 'salvador', 
            'brasília', 'fortaleza', 'recife', 'porto alegre', 'curitiba'
        ]
        for cidade in cidades_conhecidas:
            if cidade in endereco:
                return cidade
        return None

    def _extrair_estado(self, endereco):
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

    def _regioes_proximas(self, estado1, estado2):
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

    def _extrair_palavras_chave(self, texto):
        """Extrai palavras-chave relevantes do texto"""
        import re
        palavras = re.findall(r'\b\w+\b', texto.lower())
        stopwords = {'a', 'o', 'e', 'de', 'da', 'do', 'em', 'um', 'uma', 'para', 'com', 'por', 'que', 'na', 'no'}
        palavras_filtradas = [p for p in palavras if len(p) > 2 and p not in stopwords]
        return palavras_filtradas

    def calcular_score_requisitos(self, resumo_profissional, requisitos_vaga):
        """Método de compatibilidade - usa o novo método avançado"""
        return self._calcular_score_requisitos_avancado(resumo_profissional, requisitos_vaga)

    def gerar_dicas_melhoria(self, curriculo, requisitos, score_detalhes=None):
        """Gera dicas personalizadas para melhoria do currículo"""
        dicas = []
        curriculo_lower = curriculo.lower()
        requisitos_lower = requisitos.lower()

        # Verificar tecnologias faltantes
        tecnologias_vaga = self._extrair_tecnologias(requisitos_lower)
        tecnologias_candidato = self._extrair_tecnologias(curriculo_lower)
        tecnologias_faltantes = [tech for tech in tecnologias_vaga if tech not in tecnologias_candidato]

        if tecnologias_faltantes:
            dicas.append({
                'tipo': 'tecnologia',
                'titulo': 'Desenvolva suas habilidades técnicas',
                'descricao': f"Considere estudar: {', '.join(tecnologias_faltantes[:3])}",
                'prioridade': 'alta'
            })

        # Verificar experiência
        anos_necessarios = self._extrair_anos_experiencia(requisitos_lower)
        anos_candidato = self._extrair_anos_experiencia_candidato(curriculo_lower)

        if anos_necessarios > anos_candidato:
            dicas.append({
                'tipo': 'experiencia',
                'titulo': 'Ganhe mais experiência',
                'descricao': f"Esta vaga pede {anos_necessarios} anos de experiência. Considere projetos ou estágios.",
                'prioridade': 'media'
            })

        # Verificar certificações
        if 'certificação' in requisitos_lower and 'certificação' not in curriculo_lower:
            dicas.append({
                'tipo': 'certificacao',
                'titulo': 'Obtenha certificações',
                'descricao': "Certificações podem aumentar significativamente suas chances.",
                'prioridade': 'media'
            })

        return dicas
