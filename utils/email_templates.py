from datetime import datetime
import os


class EmailTemplateManager:
    """Gerenciador de templates de email personalizados"""

    def __init__(self):
        self.base_style = """
        <style>
            .email-container {
                max-width: 600px;
                margin: 0 auto;
                font-family: 'Arial', sans-serif;
                background-color: #f8f9fa;
                padding: 20px;
            }
            .email-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }
            .email-body {
                background: white;
                padding: 30px;
                border-radius: 0 0 10px 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .highlight {
                background-color: #e3f2fd;
                padding: 15px;
                border-left: 4px solid #2196f3;
                margin: 15px 0;
            }
            .stats-table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            .stats-table th, .stats-table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            .stats-table th {
                background-color: #f5f5f5;
                font-weight: bold;
            }
            .action-button {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 25px;
                margin: 20px 0;
                font-weight: bold;
            }
            .footer {
                text-align: center;
                color: #666;
                font-size: 12px;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }
            .badge {
                display: inline-block;
                background-color: #4caf50;
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: bold;
            }
            .badge.urgent {
                background-color: #f44336;
            }
            .badge.medium {
                background-color: #ff9800;
            }
        </style>
        """

    def template_contratacao(self, dados):
        """Template para notificação de contratação"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>🎉 Parabéns! Você foi selecionado(a)!</title>
            {self.base_style}
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <div style="font-size: 48px; margin-bottom: 10px;">🎉</div>
                        <h1 style="margin: 0; font-size: 28px; font-weight: bold;">PARABÉNS!</h1>
                        <h2 style="margin: 5px 0 0 0; font-size: 18px; opacity: 0.9;">Você foi selecionado(a)!</h2>
                    </div>
                </div>
                <div class="email-body">
                    <p style="font-size: 16px; margin-bottom: 20px;">Olá, <strong>{dados['candidato_nome']}</strong>! 👋</p>

                    <div class="highlight" style="text-align: center; padding: 20px; margin: 20px 0;">
                        <h3 style="margin: 0 0 10px 0; color: #2563eb;">🏆 EXCELENTE NOTÍCIA!</h3>
                        <p style="margin: 0; font-size: 18px;"><strong>Você foi selecionado(a) para a vaga:</strong></p>
                        <h2 style="margin: 10px 0; color: #1f2937; font-size: 22px;">"{dados['vaga_titulo']}"</h2>
                        <p style="margin: 0; font-size: 16px;">na empresa <strong style="color: #7c3aed;">{dados['empresa_nome']}</strong></p>
                    </div>

                    <div style="background: #f8fafc; padding: 20px; border-radius: 10px; margin: 20px 0;">
                        <h3 style="margin: 0 0 15px 0; color: #374151; display: flex; align-items: center;">
                            📊 Detalhes da sua candidatura
                        </h3>
                        <table class="stats-table" style="width: 100%; background: white; border-radius: 8px; overflow: hidden;">
                            <tr>
                                <th style="background: #e5e7eb; padding: 12px; text-align: left;">🏅 Posição no ranking</th>
                                <td style="padding: 12px;"><span class="badge" style="background: #10b981; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold;">{dados['posicao']}º lugar</span></td>
                            </tr>
                            <tr>
                                <th style="background: #e5e7eb; padding: 12px; text-align: left;">⭐ Score de compatibilidade</th>
                                <td style="padding: 12px;"><strong style="color: #059669; font-size: 18px;">{dados.get('score', 'N/A')}%</strong></td>
                            </tr>
                            <tr>
                                <th style="background: #e5e7eb; padding: 12px; text-align: left;">👥 Total de candidatos</th>
                                <td style="padding: 12px;"><strong>{dados.get('total_candidatos', 'N/A')}</strong></td>
                            </tr>
                            <tr>
                                <th style="background: #e5e7eb; padding: 12px; text-align: left;">📅 Data da seleção</th>
                                <td style="padding: 12px;"><strong>{datetime.now().strftime('%d/%m/%Y às %H:%M')}</strong></td>
                            </tr>
                        </table>
                    </div>

                    {self._gerar_mensagem_personalizada(dados)}

                    <div style="background: #dbeafe; border-left: 4px solid #3b82f6; padding: 20px; margin: 25px 0; border-radius: 0 8px 8px 0;">
                        <h3 style="margin: 0 0 15px 0; color: #1e40af; display: flex; align-items: center;">
                            🚀 Próximos passos
                        </h3>
                        <ul style="margin: 0; padding-left: 20px; color: #1f2937;">
                            <li style="margin-bottom: 8px;">💼 A empresa <strong>{dados['empresa_nome']}</strong> entrará em contato em breve</li>
                            <li style="margin-bottom: 8px;">🎯 Prepare-se para possíveis entrevistas finais ou alinhamentos</li>
                            <li style="margin-bottom: 8px;">📋 Tenha seus documentos pessoais organizados e atualizados</li>
                            <li style="margin-bottom: 8px;">💡 Revise informações sobre a empresa e a vaga</li>
                        </ul>
                    </div>

                    {dados.get('mensagem_personalizada', '') and f'<div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;"><h4 style="margin: 0 0 10px 0; color: #92400e;">💬 Mensagem da empresa:</h4><p style="margin: 0; font-style: italic; color: #78350f;">"{dados["mensagem_personalizada"]}"</p></div>' or ''}

                    <div style="text-align: center; margin: 30px 0;">
                        <p style="font-size: 20px; margin: 0; color: #059669;">
                            <strong>Mais uma vez, parabéns pela conquista! 🎊✨</strong>
                        </p>
                        <p style="margin: 10px 0 0 0; color: #6b7280;">
                            Desejamos muito sucesso nesta nova jornada! 🌟
                        </p>
                    </div>
                </div>
                {self._gerar_footer()}
            </div>
        </body>
        </html>
        """

    def template_vaga_alterada(self, dados):
        """Template para alteração de vaga"""
        corpo = f"""
                    <p>A vaga <strong>"{dados['vaga_titulo']}"</strong> da empresa <strong>{dados['empresa_nome']}</strong> foi <strong>{dados['tipo_alteracao']}</strong>.</p>
                    <h3>ℹ️ O que isso significa:</h3>
                    <ul>
                        <li>Sua candidatura continua válida</li>
                        <li>Podem ter havido mudanças nos requisitos ou benefícios</li>
                        <li>Recomendamos revisar a vaga atualizada</li>
                    </ul>
                    <a href="#{dados['vaga_id']}" class="action-button">Ver Vaga Atualizada</a>
                    <p><small>Data da alteração: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</small></p>
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>📝 Vaga Atualizada - {dados['vaga_titulo']}</title>
            {self.base_style}
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h1>📝 VAGA ATUALIZADA</h1>
                    <h2>{dados['vaga_titulo']}</h2>
                </div>
                <div class="email-body">
                    <p>Olá, <strong>{dados['candidato_nome']}</strong>!</p>
                    <div style="text-align: center; margin-bottom: 20px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
                        <h2 style="margin: 0 0 10px 0; font-size: 24px; font-weight: bold;">Vaboo!</h2>
                        <p style="margin: 0; font-size: 14px; opacity: 0.9;">Simplicidade, agilidade e inteligência</p>
                    </div>
                    <div style="padding: 20px;">
                        <p style="font-size: 16px; line-height: 1.6; color: #333;">{corpo}</p>
                    </div>
                </div>
                {self._gerar_footer()}
            </div>
        </body>
        </html>
        """

    def template_vaga_congelada(self, dados):
        """Template para vaga congelada"""
        corpo = f"""
                    <p>A vaga <strong>"{dados['vaga_titulo']}"</strong> da empresa <strong>{dados['empresa_nome']}</strong> foi temporariamente <strong>congelada</strong>.</p>
                    <h3>🔍 O que isso significa:</h3>
                    <ul>
                        <li><strong>Sua candidatura permanece válida</strong></li>
                        <li>O processo seletivo foi pausado temporariamente</li>
                        <li>Você será notificado quando a vaga for reativada</li>
                        <li>Não há ação necessária de sua parte</li>
                    </ul>
                    <div class="highlight">
                        <p><strong>💡 Sugestão:</strong> Continue explorando outras oportunidades enquanto aguarda!</p>
                    </div>
                    <a href="#/dashboard" class="action-button">Ver Outras Vagas</a>
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>❄️ Vaga Temporariamente Congelada</title>
            {self.base_style}
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h1>❄️ VAGA CONGELADA</h1>
                    <h2>Processo Temporariamente Pausado</h2>
                </div>
                <div class="email-body">
                    <p>Olá, <strong>{dados['candidato_nome']}</strong>!</p>
                    <div style="text-align: center; margin-bottom: 20px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
                        <h2 style="margin: 0 0 10px 0; font-size: 24px; font-weight: bold;">Vaboo!</h2>
                        <p style="margin: 0; font-size: 14px; opacity: 0.9;">Simplicidade, agilidade e inteligência</p>
                    </div>
                    <div style="padding: 20px;">
                        <p style="font-size: 16px; line-height: 1.6; color: #333;">{corpo}</p>
                    </div>
                </div>
                {self._gerar_footer()}
            </div>
        </body>
        </html>
        """

    def template_relatorio_empresa(self, dados):
        """Template para relatório da empresa"""
        corpo = f"""
                    <p>Olá, <strong>{dados['empresa_nome']}</strong>!</p>
                    <h3>📈 Resumo da Semana:</h3>
                    <table class="stats-table">
                        <tr>
                            <th>Vagas Ativas</th>
                            <td><strong>{dados['vagas_ativas']}</strong></td>
                        </tr>
                        <tr>
                            <th>Novas Candidaturas</th>
                            <td><span class="badge">{dados['novas_candidaturas']}</span></td>
                        </tr>
                        <tr>
                            <th>Candidatos com Score 80+</th>
                            <td><span class="badge">{dados['candidatos_alta_compatibilidade']}</span></td>
                        </tr>
                        <tr>
                            <th>Vagas Urgentes</th>
                            <td><span class="badge urgent">{dados['vagas_urgentes']}</span></td>
                        </tr>
                    </table>
                    <h3>🎯 Top Vagas por Performance:</h3>
                    {self._gerar_lista_top_vagas(dados.get('top_vagas', []))}
                    <div class="highlight">
                        <p><strong>💡 Dica da Semana:</strong> Vagas com descrições detalhadas e requisitos claros atraem 40% mais candidatos qualificados!</p>
                    </div>
                    <a href="#/dashboard" class="action-button">Ver Dashboard Completo</a>
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>📊 Relatório de Vagas - {dados['empresa_nome']}</title>
            {self.base_style}
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h1>📊 RELATÓRIO SEMANAL</h1>
                    <h2>Suas Vagas em Números</h2>
                </div>
                <div class="email-body">
                    <div style="text-align: center; margin-bottom: 20px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
                        <h2 style="margin: 0 0 10px 0; font-size: 24px; font-weight: bold;">Vaboo!</h2>
                        <p style="margin: 0; font-size: 14px; opacity: 0.9;">Simplicidade, agilidade e inteligência</p>
                    </div>
                    <div style="padding: 20px;">
                        <p style="font-size: 16px; line-height: 1.6; color: #333;">{corpo}</p>
                    </div>
                </div>
                {self._gerar_footer()}
            </div>
        </body>
        </html>
        """

    def template_recomendacao_ia(self, dados):
        """Template para recomendações da IA"""
        corpo = f"""
                    <p>Olá, <strong>{dados['candidato_nome']}</strong>!</p>
                    <div class="highlight">
                        <p>Baseado na análise do seu perfil, nossa IA identificou <strong>{len(dados['recomendacoes'])} oportunidades</strong> perfeitas para você!</p>
                    </div>
                    <h3>📊 Análise do seu Perfil:</h3>
                    <table class="stats-table">
                        <tr>
                            <th>Nível de Senioridade</th>
                            <td><span class="badge">{dados['analise']['nivel_senioridade']}</span></td>
                        </tr>
                        <tr>
                            <th>Tecnologias Dominadas</th>
                            <td><strong>{len(dados['analise']['tecnologias_identificadas'])}</strong></td>
                        </tr>
                        <tr>
                            <th>Score do Perfil</th>
                            <td><span class="badge">{dados['analise']['score_geral']}/100</span></td>
                        </tr>
                    </table>
                    <h3>🎯 Vagas Recomendadas:</h3>
                    {self._gerar_lista_recomendacoes(dados['recomendacoes'])}
                    <h3>💡 Dicas de Melhoria:</h3>
                    {self._gerar_lista_dicas(dados.get('dicas', []))}
                    <a href="#/dashboard" class="action-button">Ver Recomendações Completas</a>
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>🤖 Recomendações Personalizadas da IA</title>
            {self.base_style}
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h1>🤖 IA ASSISTANT</h1>
                    <h2>Recomendações Personalizadas</h2>
                </div>
                <div class="email-body">
                    <div style="text-align: center; margin-bottom: 20px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
                        <h2 style="margin: 0 0 10px 0; font-size: 24px; font-weight: bold;">Vaboo!</h2>
                        <p style="margin: 0; font-size: 14px; opacity: 0.9;">Simplicidade, agilidade e inteligência</p>
                    </div>
                    <div style="padding: 20px;">
                        <p style="font-size: 16px; line-height: 1.6; color: #333;">{corpo}</p>
                    </div>
                </div>
                {self._gerar_footer()}
            </div>
        </body>
        </html>
        """

    def _gerar_mensagem_personalizada(self, dados):
        """Gera mensagem personalizada baseada no score"""
        score = dados.get('score', 0)
        if score >= 90:
            return '<div class="highlight"><p><strong>🌟 Excepcional!</strong> Seu perfil teve compatibilidade quase perfeita com esta vaga!</p></div>'
        elif score >= 80:
            return '<div class="highlight"><p><strong>⭐ Excelente!</strong> Você demonstrou alta compatibilidade com os requisitos!</p></div>'
        elif score >= 70:
            return '<div class="highlight"><p><strong>👍 Muito Bom!</strong> Seu perfil se destacou entre os candidatos!</p></div>'
        else:
            return '<div class="highlight"><p><strong>✨ Parabéns!</strong> Você foi a melhor escolha para esta posição!</p></div>'

    def _gerar_lista_top_vagas(self, vagas):
        """Gera lista HTML das top vagas"""
        if not vagas:
            return '<p>Nenhuma vaga para exibir.</p>'

        html = '<ul>'
        for vaga in vagas[:3]:
            html += f'''
            <li>
                <strong>{vaga['titulo']}</strong> - 
                {vaga['candidatos']} candidatos 
                <span class="badge">{vaga['score_medio']:.1f} score médio</span>
            </li>
            '''
        html += '</ul>'
        return html

    def _gerar_lista_recomendacoes(self, recomendacoes):
        """Gera lista HTML das recomendações"""
        if not recomendacoes:
            return '<p>Nenhuma recomendação disponível no momento.</p>'

        html = '<ul>'
        for rec in recomendacoes[:3]:
            urgencia_badge = 'urgent' if rec.get(
                'urgencia') == 'Imediata' else 'medium'
            html += f'''
            <li>
                <strong>{rec['titulo']}</strong> - {rec['empresa']}<br>
                <small>Compatibilidade: <span class="badge">{rec['compatibilidade']['score']:.0f}%</span></small>
                {f'<span class="badge {urgencia_badge}">Urgente</span>' if rec.get('urgencia') == 'Imediata' else ''}
                <br><small>{', '.join(rec['motivos'][:2])}</small>
            </li>
            '''
        html += '</ul>'
        return html

    def _gerar_lista_dicas(self, dicas):
        """Gera lista HTML das dicas"""
        if not dicas:
            return '<p>Seu perfil está muito bem otimizado! 🎉</p>'

        html = '<ul>'
        for dica in dicas[:3]:
            prioridade_class = 'urgent' if dica.get(
                'prioridade') == 'alta' else 'medium' if dica.get(
                    'prioridade') == 'media' else ''
            html += f'''
            <li>
                <strong>{dica.get('icone', '💡')} {dica['titulo']}</strong>
                {f'<span class="badge {prioridade_class}">{dica["prioridade"]}</span>' if dica.get('prioridade') else ''}
                <br><small>{dica['descricao']}</small>
            </li>
            '''
        html += '</ul>'
        return html

    def _gerar_footer(self):
        """Gera footer padrão dos emails"""
        return f'''
        <div class="footer">
            <p><strong>Vaboo! Sistema de Gestão de Vagas</strong></p>
            <p>Simplicidade, agilidade e inteligência na busca por talentos</p>
            <p>© {datetime.now().year} - Todos os direitos reservados</p>
            <p><small>Este é um email automático, não responda.</small></p>
        </div>
        '''