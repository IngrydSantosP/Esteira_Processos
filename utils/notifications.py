import sqlite3
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
from .email_templates import EmailTemplateManager

load_dotenv()


def obter_notificacoes(candidato_id, apenas_nao_lidas=False):
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    try:
        # Buscar notificações com dados completos de vaga e empresa
        query = '''
            SELECT n.id, n.candidato_id, COALESCE(n.tipo, 'geral') as tipo,
                   n.mensagem, COALESCE(n.lida, 0) as lida,
                   COALESCE(n.data_envio, datetime('now')) as data_envio,
                   n.vaga_id, n.empresa_id,
                   v.titulo as vaga_titulo, 
                   e.nome as empresa_nome,
                   v.tipo_vaga,
                   v.salario_oferecido,
                   DATE(COALESCE(n.data_envio, datetime('now'))) as data_formatada,
                   CASE 
                       WHEN n.tipo = 'contratacao' AND julianday('now') - julianday(COALESCE(n.data_envio, datetime('now'))) <= 30 THEN 1
                       ELSE 0
                   END as is_fixada
            FROM notificacoes n
            LEFT JOIN vagas v ON n.vaga_id = v.id
            LEFT JOIN empresas e ON n.empresa_id = e.id
            WHERE n.candidato_id = ?
        '''
        params = [candidato_id]

        if apenas_nao_lidas:
            query += ' AND n.lida = 0'

        # Ordenar: fixadas primeiro, depois não lidas, depois por data
        query += '''
            ORDER BY 
                CASE WHEN n.tipo = 'contratacao' AND julianday('now') - julianday(COALESCE(n.data_envio, datetime('now'))) <= 30 THEN 1 ELSE 0 END DESC,
                n.lida ASC, 
                COALESCE(n.data_envio, datetime('now')) DESC
            LIMIT 50
        '''

        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        conn.close()


def obter_estatisticas(candidato_id):
    """Retorna estatísticas das notificações de um candidato"""
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        # Total de notificações
        cursor.execute(
            'SELECT COUNT(*) FROM notificacoes WHERE candidato_id = ?',
            (candidato_id, ))
        total = cursor.fetchone()[0] or 0

        # Notificações não lidas
        cursor.execute(
            'SELECT COUNT(*) FROM notificacoes WHERE candidato_id = ? AND lida = 0',
            (candidato_id, ))
        nao_lidas = cursor.fetchone()[0] or 0

        # Notificações lidas
        lidas = total - nao_lidas

        # Quantidade por tipo
        cursor.execute(
            '''
            SELECT tipo, COUNT(*) 
            FROM notificacoes 
            WHERE candidato_id = ? 
            GROUP BY tipo
            ''', (candidato_id, ))
        por_tipo = {tipo: qtd for tipo, qtd in cursor.fetchall()}

        return {
            'total': total,
            'lidas': lidas,
            'nao_lidas': nao_lidas,
            'por_tipo': por_tipo
        }
    except Exception as e:
        print(f"Erro ao obter estatísticas de notificações: {e}")
        return {}
    finally:
        conn.close()


class NotificationSystem:
    """Sistema completo de notificações"""

    def __init__(self):
        self.email_remetente = os.getenv('EMAIL_REMETENTE', 'sistema@vaboo.com')
        self.email_senha = os.getenv('EMAIL_SENHA', '')
        self.template_manager = EmailTemplateManager()
        
        # Log das configurações (sem expor a senha)
        if not self.email_remetente or not self.email_senha:
            print("⚠️  Configurações de email não encontradas no .env")
            print("📧 Sistema funcionará sem envio de emails")

    def enviar_email(self,
                     destinatario,
                     assunto,
                     corpo,
                     template_data=None,
                     template_type=None):
        """Envia email de notificação com template personalizado"""
        if not self.email_remetente or not self.email_senha:
            print("⚠️  Configurações de email não encontradas - email não será enviado")
            print(f"📧 Email que seria enviado para {destinatario}: {assunto}")
            # Retorna True para não quebrar o fluxo das notificações
            return True

        try:
            msg = EmailMessage()
            msg['Subject'] = assunto
            msg['From'] = self.email_remetente
            msg['To'] = destinatario
            msg.set_content(corpo, subtype='plain')

            # Usar template personalizado se fornecido
            if template_data and template_type:
                html_content = self._gerar_html_template(
                    template_type, template_data)
            else:
                # Usar template básico
                html_content = f"""
                <html>
                  <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee;">
                      <div style="text-align: center; margin-bottom: 20px;">
                        <h1 style="color: #6366f1;">Vaboo!</h1>
                      </div>
                      <p style="font-size: 16px; line-height: 1.6;">{corpo}</p>
                      <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;">
                      <p style="font-size: 12px; color: gray; text-align: center;">Vaboo! — Simplicidade, agilidade e inteligência</p>
                    </div>
                  </body>
                </html>
                """

            msg.add_alternative(html_content, subtype='html')

            smtp = smtplib.SMTP('smtp.gmail.com', 587)
            smtp.starttls()
            smtp.login(self.email_remetente, self.email_senha)
            smtp.send_message(msg)
            smtp.quit()
            print(f"✅ E-mail enviado com sucesso para {destinatario}")
            return True
        except Exception as e:
            print(f"❌ Erro ao enviar e-mail para {destinatario}: {e}")
            print(f"📧 Assunto: {assunto}")
            # Retorna True para não quebrar o fluxo, mas loga o erro
            return True

    def _gerar_html_template(self, template_type, dados):
        """Gera HTML usando template personalizado"""
        try:
            if template_type == 'contratacao':
                return self.template_manager.template_contratacao(dados)
            elif template_type == 'vaga_alterada':
                return self.template_manager.template_vaga_alterada(dados)
            elif template_type == 'vaga_congelada':
                return self.template_manager.template_vaga_congelada(dados)
            elif template_type == 'recomendacao_ia':
                return self.template_manager.template_recomendacao_ia(dados)
            else:
                return None
        except Exception as e:
            print(f"Erro ao gerar template: {e}")
            return None

    def criar_notificacao(self,
                          candidato_id,
                          mensagem,
                          vaga_id=None,
                          empresa_id=None,
                          tipo='geral',
                          titulo=None):
        """Criar notificação no banco de dados"""
        max_tentativas = 3
        tentativa = 0
        
        # Validar candidato_id com mais rigor
        if not candidato_id or candidato_id == 0:
            print("❌ Erro: candidato_id não pode ser nulo ou zero")
            return False
            
        # Converter para int se necessário
        try:
            candidato_id = int(candidato_id)
        except (ValueError, TypeError):
            print(f"❌ Erro: candidato_id inválido: {candidato_id}")
            return False
            
        print(f"🔔 Criando notificação para candidato {candidato_id}, tipo: {tipo}")
        
        while tentativa < max_tentativas:
            try:
                # Usar timeout maior e WAL mode para evitar locks
                conn = sqlite3.connect('recrutamento.db', timeout=60.0)
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA busy_timeout=60000')
                conn.execute('PRAGMA synchronous=NORMAL')
                cursor = conn.cursor()

                # Verificar se o candidato existe com validação mais robusta
                cursor.execute('SELECT id, nome FROM candidatos WHERE id = ?', (candidato_id,))
                candidato_existe = cursor.fetchone()
                if not candidato_existe:
                    print(f"❌ Candidato {candidato_id} não encontrado no banco")
                    conn.close()
                    return False
                
                print(f"✅ Candidato encontrado: {candidato_existe[1]} (ID: {candidato_id})")

                # Verificar se as colunas existem
                cursor.execute("PRAGMA table_info(notificacoes)")
                columns = [column[1] for column in cursor.fetchall()]

                if 'tipo' not in columns:
                    cursor.execute(
                        'ALTER TABLE notificacoes ADD COLUMN tipo TEXT DEFAULT "geral"'
                    )
                    conn.commit()

                if 'titulo' not in columns:
                    cursor.execute(
                        'ALTER TABLE notificacoes ADD COLUMN titulo TEXT DEFAULT ""'
                    )
                    conn.commit()

                # Se empresa_id não foi fornecido, buscar pela vaga_id
                if not empresa_id and vaga_id:
                    cursor.execute('SELECT empresa_id FROM vagas WHERE id = ?',
                                   (vaga_id, ))
                    result = cursor.fetchone()
                    if result:
                        empresa_id = result[0]

                # Se ainda não temos empresa_id, buscar uma empresa válida
                if not empresa_id:
                    cursor.execute('SELECT id FROM empresas LIMIT 1')
                    result = cursor.fetchone()
                    empresa_id = result[0] if result else None

                # Usar título personalizado ou extrair da mensagem
                if not titulo:
                    titulo = mensagem.split(
                        '\n')[0][:100] if mensagem else 'Notificação'

                cursor.execute(
                    '''
                    INSERT INTO notificacoes (candidato_id, mensagem, vaga_id, empresa_id, tipo, titulo, data_envio, lida)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 0)
                ''', (candidato_id, mensagem, vaga_id, empresa_id, tipo, titulo))

                conn.commit()
                print(f"✅ Notificação criada com sucesso para candidato {candidato_id}")
                return True

            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e) and tentativa < max_tentativas - 1:
                    tentativa += 1
                    print(f"⏳ Database locked, tentativa {tentativa}/{max_tentativas}")
                    import time
                    time.sleep(2 ** tentativa)  # Backoff exponencial
                    continue
                print(f"❌ Erro de banco ao criar notificação para candidato {candidato_id}: {e}")
                return False
            except Exception as e:
                print(f"❌ Erro ao criar notificação para candidato {candidato_id}: {e}")
                return False
            finally:
                try:
                    if 'conn' in locals():
                        conn.close()
                except:
                    pass
        
        return False

    def notificar_contratacao(self,
                              candidato_id,
                              vaga_id,
                              empresa_id,
                              mensagem_personalizada=""):
        """Notifica candidato sobre contratação com template personalizado"""
        
        # Validar parâmetros de entrada
        if not candidato_id or not vaga_id:
            print(f"❌ Parâmetros inválidos: candidato_id={candidato_id}, vaga_id={vaga_id}")
            return False
            
        try:
            candidato_id = int(candidato_id)
            vaga_id = int(vaga_id)
        except (ValueError, TypeError):
            print(f"❌ IDs inválidos: candidato_id={candidato_id}, vaga_id={vaga_id}")
            return False
            
        print(f"🎯 Iniciando notificação de contratação para candidato {candidato_id}")
        
        conn = sqlite3.connect('recrutamento.db', timeout=60.0)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()

        try:
            # Verificar se o candidato existe com mais detalhes
            cursor.execute('SELECT id, nome, email FROM candidatos WHERE id = ?', (candidato_id,))
            candidato_info = cursor.fetchone()
            if not candidato_info:
                print(f"❌ Candidato {candidato_id} não encontrado no banco")
                conn.close()
                return False
            
            print(f"✅ Candidato encontrado: {candidato_info[1]} (ID: {candidato_id})")

            # Buscar dados completos do candidato, vaga e empresa
            cursor.execute(
                '''
                SELECT c.nome, c.email, v.titulo, e.nome, ca.posicao, ca.score,
                       v.salario_oferecido, v.tipo_vaga, v.descricao,
                       (SELECT COUNT(*) FROM candidaturas WHERE vaga_id = ?) as total_candidatos
                FROM candidatos c
                JOIN candidaturas ca ON c.id = ca.candidato_id
                JOIN vagas v ON ca.vaga_id = v.id
                JOIN empresas e ON v.empresa_id = e.id
                WHERE c.id = ? AND v.id = ? AND e.id = ?
            ''', (vaga_id, candidato_id, vaga_id, empresa_id))

            resultado = cursor.fetchone()
            if not resultado:
                print(f"❌ Dados da contratação não encontrados para candidato {candidato_id}")
                return False

            candidato_nome, candidato_email, vaga_titulo, empresa_nome, posicao, score, salario, tipo_vaga, descricao, total_candidatos = resultado

            # Dados para o template
            template_data = {
                'candidato_nome': candidato_nome,
                'vaga_titulo': vaga_titulo,
                'empresa_nome': empresa_nome,
                'posicao': posicao,
                'score': round(score, 1) if score else 'N/A',
                'total_candidatos': total_candidatos,
                'mensagem_personalizada': mensagem_personalizada,
                'vaga_id': vaga_id,
                'salario_oferecido': salario,
                'tipo_vaga': tipo_vaga,
                'data_selecao': datetime.now().strftime('%d/%m/%Y às %H:%M')
            }

            # Criar mensagem para notificação interna mais detalhada
            mensagem_completa = f"""🎉 PARABÉNS! Você foi selecionado(a)!

🏆 Vaga: {vaga_titulo}
🏢 Empresa: {empresa_nome}
📊 Sua posição: {posicao}º lugar (de {total_candidatos} candidatos)
⭐ Score de compatibilidade: {round(score, 1) if score else 'N/A'}%
💰 Salário: R$ {salario:,.2f}
📋 Modalidade: {tipo_vaga}
📅 Data da seleção: {datetime.now().strftime('%d/%m/%Y às %H:%M')}

{mensagem_personalizada if mensagem_personalizada else 'A empresa entrará em contato em breve para os próximos passos. Prepare-se para uma nova jornada! 🚀'}

🎊 Desejamos muito sucesso!"""

            # Criar notificação no sistema
            sucesso_notif = self.criar_notificacao(candidato_id, mensagem_completa, vaga_id,
                                                   empresa_id, 'contratacao')

            if not sucesso_notif:
                print(f"❌ Falha ao criar notificação para candidato {candidato_id}")

            # Enviar email com template personalizado
            assunto = f"🎉 PARABÉNS! Você foi selecionado(a) para {vaga_titulo} - {empresa_nome}"
            self.enviar_email(
                candidato_email, assunto,
                f"Parabéns! Você foi selecionado(a) para a vaga '{vaga_titulo}' na empresa {empresa_nome}!",
                template_data, 'contratacao')

            print(f"✅ Notificação de contratação processada para candidato {candidato_id}")
            return True

        except Exception as e:
            print(f"❌ Erro ao notificar contratação para candidato {candidato_id}: {e}")
            return False
        finally:
            conn.close()

    def notificar_alteracao_vaga(self, vaga_id, tipo_alteracao='atualizada'):
        """Notifica candidatos sobre alterações na vaga"""
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        try:
            # Buscar candidatos da vaga com mais detalhes
            cursor.execute(
                '''
                SELECT DISTINCT c.id, c.nome, c.email, v.titulo, e.nome, ca.posicao, ca.score,
                       v.salario_oferecido, v.tipo_vaga, v.descricao, v.requisitos
                FROM candidaturas ca
                JOIN candidatos c ON ca.candidato_id = c.id
                JOIN vagas v ON ca.vaga_id = v.id
                JOIN empresas e ON v.empresa_id = e.id
                WHERE ca.vaga_id = ? AND v.status = 'Ativa'
            ''', (vaga_id, ))

            candidatos = cursor.fetchall()

            for candidato in candidatos:
                candidato_id, nome, email, vaga_titulo, empresa_nome, posicao, score, salario, tipo_vaga, descricao, requisitos = candidato

                mensagem = f"""📝 VAGA ATUALIZADA - AÇÃO NECESSÁRIA

🏢 Empresa: {empresa_nome}
💼 Vaga: {vaga_titulo}
📊 Sua posição atual: {posicao}º lugar
⭐ Seu score: {round(score, 1) if score else 'N/A'}%

🔄 MUDANÇAS REALIZADAS:
A vaga foi {tipo_alteracao} e pode incluir:
• Novos requisitos ou qualificações
• Alterações no salário ou benefícios
• Mudanças na descrição da função
• Ajustes no tipo de contratação

✅ O QUE FAZER AGORA:
1. Acesse seu dashboard para ver as mudanças
2. Verifique se ainda atende aos novos requisitos
3. Seu score pode ter sido recalculado
4. Considere atualizar seu perfil se necessário

🎯 IMPACTO NA SUA CANDIDATURA:
• Sua candidatura permanece ativa
• Posição pode ser ajustada conforme novos critérios
• Recomendamos revisar a vaga completa

Data da atualização: {datetime.now().strftime('%d/%m/%Y às %H:%M')}

💡 Mantenha-se competitivo atualizando seu perfil!"""

                # Criar notificação
                self.criar_notificacao(candidato_id, mensagem, vaga_id, None,
                                       'vaga_alterada')

                # Enviar email
                assunto = f"📝 Vaga Atualizada - {vaga_titulo} na {empresa_nome}"
                self.enviar_email(email, assunto, mensagem)

            return True

        except Exception as e:
            print(f"Erro ao notificar alteração de vaga: {e}")
            return False
        finally:
            conn.close()

    def notificar_vaga_congelada(self, vaga_id):
        """Notifica candidatos sobre congelamento de vaga"""
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                SELECT DISTINCT c.id, c.nome, c.email, v.titulo, e.nome, ca.posicao, ca.score,
                       v.salario_oferecido, v.tipo_vaga
                FROM candidaturas ca
                JOIN candidatos c ON ca.candidato_id = c.id
                JOIN vagas v ON ca.vaga_id = v.id
                JOIN empresas e ON v.empresa_id = e.id
                WHERE ca.vaga_id = ?
            ''', (vaga_id, ))

            candidatos = cursor.fetchall()

            for candidato in candidatos:
                candidato_id, nome, email, vaga_titulo, empresa_nome, posicao, score, salario, tipo_vaga = candidato

                mensagem = f"""❄️ PROCESSO SELETIVO PAUSADO TEMPORARIAMENTE

🏢 Empresa: {empresa_nome}
💼 Vaga: {vaga_titulo}
📊 Sua posição atual: {posicao}º lugar
⭐ Seu score: {round(score, 1) if score else 'N/A'}%
💰 Salário: R$ {salario:,.2f} ({tipo_vaga})

📋 O QUE SIGNIFICA:
• O processo seletivo foi pausado temporariamente
• Sua candidatura permanece ATIVA e válida
• Você manterá sua posição no ranking
• Será notificado quando o processo for retomado

🔔 PRÓXIMOS PASSOS:
• Mantenha seu perfil atualizado
• Continue explorando outras oportunidades
• Aguarde nossa comunicação sobre a reativação

Data da pausa: {datetime.now().strftime('%d/%m/%Y às %H:%M')}

💡 Dica: Use este tempo para aprimorar suas habilidades relacionadas à vaga!"""

                self.criar_notificacao(candidato_id, mensagem, vaga_id, None,
                                       'vaga_congelada')

                assunto = f"❄️ Processo Pausado - {vaga_titulo} na {empresa_nome}"
                self.enviar_email(email, assunto, mensagem)

            return True

        except Exception as e:
            print(f"Erro ao notificar congelamento: {e}")
            return False
        finally:
            conn.close()

    def notificar_nova_candidatura(self, candidato_id, vaga_id, posicao,
                                   score):
        """Notifica candidato sobre nova candidatura com informações úteis"""
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                SELECT c.nome, c.email, v.titulo, e.nome, v.salario_oferecido, v.tipo_vaga,
                       (SELECT COUNT(*) FROM candidaturas WHERE vaga_id = ?) as total_candidatos,
                       v.urgencia_contratacao, v.data_criacao
                FROM candidatos c, vagas v, empresas e
                WHERE c.id = ? AND v.id = ? AND e.id = v.empresa_id
            ''', (vaga_id, candidato_id, vaga_id))

            resultado = cursor.fetchone()
            if not resultado:
                return False

            nome, email, vaga_titulo, empresa_nome, salario, tipo_vaga, total_candidatos, urgencia, data_criacao = resultado

            # Calcular quantos dias a vaga está ativa
            if data_criacao:
                data_vaga = datetime.strptime(data_criacao,
                                              '%Y-%m-%d %H:%M:%S')
                dias_ativa = (datetime.now() - data_vaga).days
            else:
                dias_ativa = 0

            mensagem = f"""🎯 CANDIDATURA REALIZADA COM SUCESSO!

🏢 Empresa: {empresa_nome}
💼 Vaga: {vaga_titulo}
📊 Sua posição: {posicao}º lugar (de {total_candidatos} candidatos)
⭐ Score de compatibilidade: {round(score, 1) if score else 'N/A'}%
💰 Salário: R$ {salario:,.2f} ({tipo_vaga})

📈 ESTATÍSTICAS DA VAGA:
• Total de candidatos: {total_candidatos}
• Vaga ativa há: {dias_ativa} dias
• Urgência: {urgencia or 'Normal'}

🔔 PRÓXIMOS PASSOS:
1. Acompanhe sua posição no ranking
2. Mantenha seu perfil atualizado
3. Prepare-se para possível contato da empresa
4. Continue explorando outras oportunidades

💡 DICAS PARA SE DESTACAR:
• Complete seu perfil se ainda não fez
• Adicione certificações relevantes
• Mantenha suas experiências atualizadas

Data da candidatura: {datetime.now().strftime('%d/%m/%Y às %H:%M')}

Boa sorte! 🍀"""

            self.criar_notificacao(candidato_id, mensagem, vaga_id, None,
                                   'nova_candidatura')

            assunto = f"🎯 Candidatura Confirmada - {vaga_titulo} na {empresa_nome}"
            self.enviar_email(email, assunto, mensagem)

            return True

        except Exception as e:
            print(f"Erro ao notificar nova candidatura: {e}")
            return False
        finally:
            conn.close()

    def notificar_vaga_excluida(self, vaga_id):
        """Notifica candidatos sobre exclusão de vaga"""
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                SELECT DISTINCT c.id, c.nome, c.email, v.titulo, e.nome
                FROM candidaturas ca
                JOIN candidatos c ON ca.candidato_id = c.id
                JOIN vagas v ON ca.vaga_id = v.id
                JOIN empresas e ON v.empresa_id = e.id
                WHERE ca.vaga_id = ?
            ''', (vaga_id, ))

            candidatos = cursor.fetchall()

            for candidato in candidatos:
                candidato_id, nome, email, vaga_titulo, empresa_nome = candidato

                mensagem = f"""❌ A vaga '{vaga_titulo}' da empresa {empresa_nome} foi excluída.

Infelizmente, o processo seletivo para esta vaga foi encerrado. Continue explorando outras oportunidades em nosso sistema!"""

                self.criar_notificacao(candidato_id, mensagem, vaga_id, None,
                                       'vaga_excluida')

                assunto = f"❌ Vaga Excluída - {vaga_titulo}"
                self.enviar_email(email, assunto, mensagem)

            return True

        except Exception as e:
            print(f"Erro ao notificar exclusão: {e}")
            return False
        finally:
            conn.close()


# Funções de conveniência para manter compatibilidade
notification_system = NotificationSystem()


def criar_notificacao(candidato_id,
                      mensagem,
                      vaga_id=None,
                      empresa_id=None,
                      tipo='geral'):
    return notification_system.criar_notificacao(candidato_id, mensagem,
                                                 vaga_id, empresa_id, tipo)


def notificar_alteracao_vaga(vaga_id, tipo_alteracao='atualizada'):
    return notification_system.notificar_alteracao_vaga(
        vaga_id, tipo_alteracao)


def buscar_notificacoes_candidato(candidato_id, apenas_nao_lidas=False):
    """Busca notificações de um candidato"""
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        query = '''
            SELECT n.id, n.mensagem, n.data_envio, n.lida, n.tipo,
                   v.titulo as vaga_titulo, e.nome as empresa_nome
            FROM notificacoes n
            LEFT JOIN vagas v ON n.vaga_id = v.id
            LEFT JOIN empresas e ON n.empresa_id = e.id
            WHERE n.candidato_id = ?
        '''

        if apenas_nao_lidas:
            query += ' AND n.lida = 0'

        query += ' ORDER BY n.data_envio DESC'

        cursor.execute(query, (candidato_id, ))
        return cursor.fetchall()
    except Exception as e:
        print(f"Erro ao buscar notificações: {e}")
        return []
    finally:
        conn.close()


def marcar_notificacao_como_lida(notificacao_id, candidato_id):
    """Marca uma notificação como lida"""
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            UPDATE notificacoes 
            SET lida = 1 
            WHERE id = ? AND candidato_id = ?
        ''', (notificacao_id, candidato_id))

        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Erro ao marcar notificação como lida: {e}")
        return False
    finally:
        conn.close()


def marcar_todas_notificacoes_como_lidas(candidato_id):
    """Marca todas as notificações do candidato como lidas"""
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            UPDATE notificacoes 
            SET lida = 1 
            WHERE candidato_id = ? AND lida = 0
        ''', (candidato_id, ))

        conn.commit()
        return cursor.rowcount
    except Exception as e:
        print(f"Erro ao marcar todas notificações como lidas: {e}")
        return 0
    finally:
        conn.close()


def contar_notificacoes_nao_lidas(candidato_id):
    """Conta quantas notificações não lidas o candidato tem"""
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            SELECT COUNT(*) FROM notificacoes 
            WHERE candidato_id = ? AND lida = 0
        ''', (candidato_id, ))

        resultado = cursor.fetchone()
        return resultado[0] if resultado else 0
    except Exception as e:
        print(f"Erro ao contar notificações: {e}")
        return 0
    finally:
        conn.close()


def obter_historico_notificacoes(candidato_id, limite=50):
    """Obtém o histórico completo de notificações do candidato"""
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            SELECT n.id, n.mensagem, n.data_envio, n.lida, n.tipo,
                   v.titulo as vaga_titulo, e.nome as empresa_nome,
                   strftime('%d/%m/%Y %H:%M', n.data_envio) as data_formatada
            FROM notificacoes n
            LEFT JOIN vagas v ON n.vaga_id = v.id
            LEFT JOIN empresas e ON n.empresa_id = e.id
            WHERE n.candidato_id = ?
            ORDER BY n.data_envio DESC
            LIMIT ?
        ''', (candidato_id, limite))

        return cursor.fetchall()
    except Exception as e:
        print(f"Erro ao obter histórico de notificações: {e}")
        return []
    finally:
        conn.close()


def debug_notificacoes_sistema():
    """Função de debug para verificar o sistema de notificações"""
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    try:
        print("\n=== DEBUG DO SISTEMA DE NOTIFICAÇÕES ===")
        
        # Listar todos os candidatos
        cursor.execute('SELECT id, nome, email FROM candidatos ORDER BY id')
        candidatos = cursor.fetchall()
        print(f"\n📋 Total de candidatos: {len(candidatos)}")
        for candidato in candidatos:
            print(f"  • ID: {candidato[0]} - Nome: {candidato[1]} - Email: {candidato[2]}")
        
        # Contar notificações por candidato
        print(f"\n🔔 Notificações por candidato:")
        cursor.execute('''
            SELECT n.candidato_id, COUNT(*) as total, 
                   SUM(CASE WHEN n.lida = 0 THEN 1 ELSE 0 END) as nao_lidas,
                   c.nome
            FROM notificacoes n
            JOIN candidatos c ON n.candidato_id = c.id
            GROUP BY n.candidato_id, c.nome
            ORDER BY n.candidato_id
        ''')
        
        stats = cursor.fetchall()
        for stat in stats:
            print(f"  • Candidato {stat[0]} ({stat[3]}): {stat[1]} total, {stat[2]} não lidas")
            
        if not stats:
            print("  • Nenhuma notificação encontrada")
            
        # Verificar estrutura da tabela
        cursor.execute("PRAGMA table_info(notificacoes)")
        colunas = cursor.fetchall()
        print(f"\n📊 Estrutura da tabela notificacoes:")
        for coluna in colunas:
            print(f"  • {coluna[1]} ({coluna[2]})")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no debug: {e}")
        return False
    finally:
        conn.close()


def testar_notificacao_para_todos():
    """Testa criação de notificação para todos os candidatos"""
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, nome FROM candidatos ORDER BY id')
        candidatos = cursor.fetchall()
        
        print(f"\n🧪 Testando notificações para {len(candidatos)} candidatos...")
        
        sucessos = 0
        falhas = 0
        
        for candidato in candidatos:
            candidato_id, nome = candidato
            mensagem = f"🧪 Teste de notificação para {nome} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            
            sucesso = notification_system.criar_notificacao(
                candidato_id, mensagem, None, None, 'teste')
            
            if sucesso:
                sucessos += 1
                print(f"  ✅ Candidato {candidato_id} ({nome}): OK")
            else:
                falhas += 1
                print(f"  ❌ Candidato {candidato_id} ({nome}): FALHOU")
        
        print(f"\n📊 Resultado: {sucessos} sucessos, {falhas} falhas")
        return sucessos > 0
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False
    finally:
        conn.close()
