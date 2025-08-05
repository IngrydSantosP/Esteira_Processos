
import sqlite3
from datetime import datetime
import re

class IAAssistant:
    """Assistente IA para análise de currículos e recomendações"""
    
    def __init__(self):
        pass
    
    def analisar_curriculo(self, candidato_id, curriculo_texto):
        """Analisa o currículo e fornece insights detalhados"""
        analise = {
            'pontos_fortes': [],
            'areas_melhoria': [],
            'tecnologias_identificadas': [],
            'nivel_senioridade': '',
            'score_geral': 0,
            'recomendacoes': []
        }
        
        if not curriculo_texto:
            return analise
            
        curriculo_lower = curriculo_texto.lower()
        
        # Identificar tecnologias
        tecnologias = self._identificar_tecnologias(curriculo_lower)
        analise['tecnologias_identificadas'] = tecnologias
        
        # Determinar nível de senioridade
        nivel = self._determinar_senioridade(curriculo_lower)
        analise['nivel_senioridade'] = nivel
        
        # Identificar pontos fortes
        pontos_fortes = self._identificar_pontos_fortes(curriculo_lower, tecnologias)
        analise['pontos_fortes'] = pontos_fortes
        
        # Identificar áreas de melhoria
        areas_melhoria = self._identificar_areas_melhoria(curriculo_lower)
        analise['areas_melhoria'] = areas_melhoria
        
        # Calcular score geral do perfil
        score = self._calcular_score_perfil(curriculo_lower, tecnologias, nivel)
        analise['score_geral'] = score
        
        # Gerar recomendações personalizadas
        recomendacoes = self._gerar_recomendacoes_personalizadas(analise)
        analise['recomendacoes'] = recomendacoes
        
        return analise
    
    def recomendar_vagas_personalizadas(self, candidato_id, curriculo_texto, limite=5):
        """Recomenda vagas específicas baseadas no perfil do candidato"""
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        try:
            # Buscar todas as vagas ativas
            cursor.execute('''
                SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido,
                       e.nome as empresa_nome, v.tipo_vaga, v.urgencia_contratacao
                FROM vagas v
                JOIN empresas e ON v.empresa_id = e.id
                WHERE v.status = 'Ativa'
                AND v.id NOT IN (
                    SELECT vaga_id FROM candidaturas WHERE candidato_id = ?
                )
            ''', (candidato_id,))
            
            vagas = cursor.fetchall()
            
            # Analisar compatibilidade de cada vaga
            recomendacoes = []
            analise_candidato = self.analisar_curriculo(candidato_id, curriculo_texto)
            
            for vaga in vagas:
                compatibilidade = self._analisar_compatibilidade_vaga(
                    analise_candidato, vaga
                )
                
                if compatibilidade['score'] >= 60:  # Só recomendar vagas com boa compatibilidade
                    recomendacoes.append({
                        'vaga_id': vaga[0],
                        'titulo': vaga[1],
                        'empresa': vaga[5],
                        'compatibilidade': compatibilidade,
                        'motivos': compatibilidade['motivos'],
                        'urgencia': vaga[7]
                    })
            
            # Ordenar por score de compatibilidade
            recomendacoes.sort(key=lambda x: x['compatibilidade']['score'], reverse=True)
            
            return recomendacoes[:limite]
            
        finally:
            conn.close()
    
    def gerar_dicas_melhoria_vaga(self, curriculo_texto, requisitos_vaga, salario_vaga):
        """Gera dicas específicas para uma vaga"""
        dicas = []
        
        curriculo_lower = curriculo_texto.lower()
        requisitos_lower = requisitos_vaga.lower()
        
        # Tecnologias faltantes
        tech_vaga = self._identificar_tecnologias(requisitos_lower)
        tech_candidato = self._identificar_tecnologias(curriculo_lower)
        tech_faltantes = [t for t in tech_vaga if t not in tech_candidato]
        
        if tech_faltantes:
            dicas.append({
                'categoria': 'Habilidades Técnicas',
                'titulo': 'Desenvolva novas tecnologias',
                'descricao': f"Aprenda: {', '.join(tech_faltantes[:3])}",
                'prioridade': 'alta',
                'icone': '💻'
            })
        
        # Experiência
        anos_necessarios = self._extrair_anos_experiencia(requisitos_lower)
        anos_candidato = self._estimar_anos_experiencia(curriculo_lower)
        
        if anos_necessarios > anos_candidato:
            dicas.append({
                'categoria': 'Experiência',
                'titulo': 'Ganhe mais experiência prática',
                'descricao': f"Busque projetos ou estágios na área ({anos_necessarios - anos_candidato} anos a mais)",
                'prioridade': 'media',
                'icone': '📈'
            })
        
        # Certificações
        if any(cert in requisitos_lower for cert in ['certificação', 'certificado']):
            if not any(cert in curriculo_lower for cert in ['certificação', 'certificado']):
                dicas.append({
                    'categoria': 'Qualificações',
                    'titulo': 'Obtenha certificações',
                    'descricao': 'Certificações podem aumentar muito suas chances',
                    'prioridade': 'media',
                    'icone': '🏆'
                })
        
        return dicas
    
    def _identificar_tecnologias(self, texto):
        """Identifica tecnologias no texto"""
        tecnologias_db = {
            'linguagens': ['python', 'java', 'javascript', 'typescript', 'php', 'c#', 'c++', 'go', 'rust'],
            'frameworks': ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'laravel', 'express'],
            'databases': ['mysql', 'postgresql', 'mongodb', 'oracle', 'sql server', 'sqlite'],
            'cloud': ['aws', 'azure', 'google cloud', 'gcp', 'docker', 'kubernetes'],
            'ferramentas': ['git', 'jenkins', 'jira', 'slack', 'figma', 'photoshop']
        }
        
        tecnologias_encontradas = []
        for categoria, techs in tecnologias_db.items():
            for tech in techs:
                if tech in texto:
                    tecnologias_encontradas.append({
                        'nome': tech,
                        'categoria': categoria
                    })
        
        return tecnologias_encontradas
    
    def _determinar_senioridade(self, curriculo):
        """Determina nível de senioridade"""
        palavras_senior = ['senior', 'sênior', 'líder', 'lead', 'coordenador', 'gerente', 'arquiteto']
        palavras_pleno = ['pleno', 'analista', 'desenvolvedor', 'especialista']
        palavras_junior = ['junior', 'júnior', 'estagiário', 'trainee', 'assistente']
        
        anos = self._estimar_anos_experiencia(curriculo)
        
        if any(p in curriculo for p in palavras_senior) or anos >= 8:
            return 'Senior'
        elif any(p in curriculo for p in palavras_pleno) or anos >= 4:
            return 'Pleno'
        elif any(p in curriculo for p in palavras_junior) or anos >= 1:
            return 'Junior'
        else:
            return 'Iniciante'
    
    def _identificar_pontos_fortes(self, curriculo, tecnologias):
        """Identifica pontos fortes do candidato"""
        pontos = []
        
        # Diversidade tecnológica
        if len(tecnologias) >= 8:
            pontos.append('Amplo conhecimento tecnológico')
        
        # Liderança
        if any(palavra in curriculo for palavra in ['líder', 'liderança', 'coordenador', 'gerente']):
            pontos.append('Experiência em liderança')
        
        # Formação
        if any(forma in curriculo for forma in ['mestrado', 'doutorado', 'pós-graduação']):
            pontos.append('Alta qualificação acadêmica')
        
        # Certificações
        if 'certificação' in curriculo or 'certificado' in curriculo:
            pontos.append('Certificações profissionais')
        
        # Idiomas
        if any(idioma in curriculo for idioma in ['inglês', 'english', 'fluente']):
            pontos.append('Conhecimento em idiomas')
        
        return pontos
    
    def _identificar_areas_melhoria(self, curriculo):
        """Identifica áreas que podem ser melhoradas"""
        areas = []
        
        # Pouca experiência internacional
        if not any(palavra in curriculo for palavra in ['internacional', 'exterior', 'english']):
            areas.append('Experiência internacional limitada')
        
        # Poucas certificações
        if curriculo.count('certificação') + curriculo.count('certificado') < 2:
            areas.append('Poucas certificações profissionais')
        
        # Falta de projetos próprios
        if not any(palavra in curriculo for palavra in ['projeto próprio', 'freelancer', 'empreendedor']):
            areas.append('Poucos projetos pessoais/próprios')
        
        return areas
    
    def _calcular_score_perfil(self, curriculo, tecnologias, nivel):
        """Calcula score geral do perfil"""
        score = 50  # Base
        
        # Tecnologias (+30)
        score += min(len(tecnologias) * 2, 30)
        
        # Senioridade (+20)
        nivel_scores = {'Iniciante': 5, 'Junior': 10, 'Pleno': 15, 'Senior': 20}
        score += nivel_scores.get(nivel, 5)
        
        # Extras
        if 'certificação' in curriculo:
            score += 10
        if any(idioma in curriculo for idioma in ['inglês', 'english']):
            score += 5
        if any(edu in curriculo for edu in ['mestrado', 'doutorado']):
            score += 10
        
        return min(score, 100)
    
    def _gerar_recomendacoes_personalizadas(self, analise):
        """Gera recomendações personalizadas"""
        recomendacoes = []
        
        nivel = analise['nivel_senioridade']
        tecnologias = len(analise['tecnologias_identificadas'])
        
        if nivel == 'Iniciante':
            recomendacoes.append({
                'titulo': 'Foque em projetos práticos',
                'descricao': 'Desenvolva projetos pessoais para demonstrar suas habilidades',
                'urgencia': 'alta'
            })
        
        if tecnologias < 5:
            recomendacoes.append({
                'titulo': 'Expanda seu toolkit tecnológico',
                'descricao': 'Aprenda novas tecnologias demandadas pelo mercado',
                'urgencia': 'media'
            })
        
        if 'Certificações profissionais' not in analise['pontos_fortes']:
            recomendacoes.append({
                'titulo': 'Obtenha certificações',
                'descricao': 'Certificações aumentam sua credibilidade no mercado',
                'urgencia': 'baixa'
            })
        
        return recomendacoes
    
    def _analisar_compatibilidade_vaga(self, analise_candidato, vaga):
        """Analisa compatibilidade entre candidato e vaga"""
        score = 0
        motivos = []
        
        vaga_id, titulo, descricao, requisitos, salario, empresa, tipo_vaga, urgencia = vaga
        
        # Tecnologias
        tech_vaga = self._identificar_tecnologias(requisitos.lower())
        tech_candidato = [t['nome'] for t in analise_candidato['tecnologias_identificadas']]
        
        tech_matches = len([t for t in tech_vaga if t['nome'] in tech_candidato])
        if tech_vaga:
            tech_score = (tech_matches / len(tech_vaga)) * 60
            score += tech_score
            
            if tech_score >= 40:
                motivos.append(f"Boa compatibilidade técnica ({tech_matches}/{len(tech_vaga)} tecnologias)")
        
        # Senioridade
        nivel = analise_candidato['nivel_senioridade']
        if nivel in requisitos:
            score += 20
            motivos.append(f"Nível de senioridade compatível ({nivel})")
        
        # Urgência
        if urgencia == 'Imediata':
            score += 10
            motivos.append("Vaga com contratação imediata")
        
        return {
            'score': min(score, 100),
            'motivos': motivos
        }
    
    def _extrair_anos_experiencia(self, texto):
        """Extrai anos de experiência mencionados"""
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
    
    def _estimar_anos_experiencia(self, curriculo):
        """Estima anos de experiência do candidato"""
        # Procurar por datas
        dates_pattern = r'(20\d{2})'
        dates = re.findall(dates_pattern, curriculo)
        
        if dates:
            dates = [int(d) for d in dates]
            anos_min = min(dates)
            ano_atual = datetime.now().year
            return max(0, ano_atual - anos_min)
        
        return 0
