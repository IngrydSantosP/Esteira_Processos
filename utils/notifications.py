
import sqlite3
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
from .email_templates import EmailTemplateManager

load_dotenv()

class NotificationSystem:
    """Sistema completo de notificações"""
    
    def __init__(self):
        self.email_remetente = os.getenv('EMAIL_REMETENTE')
        self.email_senha = os.getenv('EMAIL_SENHA')
        self.template_manager = EmailTemplateManager()
    
    def enviar_email(self, destinatario, assunto, corpo, template_data=None, template_type=None):
        """Envia email de notificação com template personalizado"""
        if not self.email_remetente or not self.email_senha:
            print("Configurações de email não encontradas")
            return False
            
        try:
            msg = EmailMessage()
            msg['Subject'] = assunto
            msg['From'] = self.email_remetente
            msg['To'] = destinatario
            msg.set_content(corpo, subtype='plain')

            # Usar template personalizado se fornecido
            if template_data and template_type:
                html_content = self._gerar_html_template(template_type, template_data)
            else:
                # Usar template básico
                html_content = f"""
                <html>
                  <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee;">
                      <img src="" alt="Vaboo!" style="height: 40px; margin-bottom: 20px;">
                      <p style="font-size: 16px;">{corpo}</p>
                      <hr style="margin: 20px 0;">
                      <p style="font-size: 12px; color: gray;">Vaboo! — Simplicidade, agilidade e inteligência</p>
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
            print(f"E-mail enviado para {destinatario}")
            return True
        except Exception as e:
            print(f"Erro ao enviar e-mail: {e}")
            return False

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

    def criar_notificacao(self, candidato_id, mensagem, vaga_id=None, empresa_id=None, tipo='geral'):
        """Cria uma nova notificação para o candidato"""
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO notificacoes (candidato_id, mensagem, vaga_id, empresa_id, tipo, data_envio, lida)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (candidato_id, mensagem, vaga_id, empresa_id, tipo, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), False))

            conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao criar notificação: {e}")
            return False
        finally:
            conn.close()

    def notificar_contratacao(self, candidato_id, vaga_id, empresa_id, mensagem_personalizada=""):
        """Notifica candidato sobre contratação com template personalizado"""
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        try:
            # Buscar dados completos do candidato, vaga e empresa
            cursor.execute('''
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
            self.criar_notificacao(candidato_id, mensagem_completa, vaga_id, empresa_id, 'contratacao')
            
            # Enviar email com template personalizado
            assunto = f"🎉 PARABÉNS! Você foi selecionado(a) para {vaga_titulo} - {empresa_nome}"
            self.enviar_email(
                candidato_email, 
                assunto, 
                f"Parabéns! Você foi selecionado(a) para a vaga '{vaga_titulo}' na empresa {empresa_nome}!",
                template_data,
                'contratacao'
            )
            
            return True
            
        except Exception as e:
            print(f"Erro ao notificar contratação: {e}")
            return False
        finally:
            conn.close()

    def notificar_alteracao_vaga(self, vaga_id, tipo_alteracao='atualizada'):
        """Notifica candidatos sobre alterações na vaga"""
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        try:
            # Buscar candidatos da vaga
            cursor.execute('''
                SELECT DISTINCT c.id, c.nome, c.email, v.titulo, e.nome
                FROM candidaturas ca
                JOIN candidatos c ON ca.candidato_id = c.id
                JOIN vagas v ON ca.vaga_id = v.id
                JOIN empresas e ON v.empresa_id = e.id
                WHERE ca.vaga_id = ? AND v.status = 'Ativa'
            ''', (vaga_id,))
            
            candidatos = cursor.fetchall()
            
            for candidato in candidatos:
                candidato_id, nome, email, vaga_titulo, empresa_nome = candidato
                
                mensagem = f"""📝 A vaga '{vaga_titulo}' da empresa {empresa_nome} foi {tipo_alteracao}.

Acesse seu dashboard para verificar as atualizações e manter sua candidatura em dia.

Data da alteração: {datetime.now().strftime('%d/%m/%Y às %H:%M')}"""
                
                # Criar notificação
                self.criar_notificacao(candidato_id, mensagem, vaga_id, None, 'alteracao_vaga')
                
                # Enviar email
                assunto = f"📝 Vaga {tipo_alteracao} - {vaga_titulo}"
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
            cursor.execute('''
                SELECT DISTINCT c.id, c.nome, c.email, v.titulo, e.nome
                FROM candidaturas ca
                JOIN candidatos c ON ca.candidato_id = c.id
                JOIN vagas v ON ca.vaga_id = v.id
                JOIN empresas e ON v.empresa_id = e.id
                WHERE ca.vaga_id = ?
            ''', (vaga_id,))
            
            candidatos = cursor.fetchall()
            
            for candidato in candidatos:
                candidato_id, nome, email, vaga_titulo, empresa_nome = candidato
                
                mensagem = f"""❄️ A vaga '{vaga_titulo}' da empresa {empresa_nome} foi temporariamente congelada.

Isso significa que o processo seletivo foi pausado. Você será notificado caso a vaga seja reativada.

Sua candidatura permanece válida e será considerada quando o processo for retomado."""
                
                self.criar_notificacao(candidato_id, mensagem, vaga_id, None, 'vaga_congelada')
                
                assunto = f"❄️ Vaga Congelada - {vaga_titulo}"
                self.enviar_email(email, assunto, mensagem)
            
            return True
            
        except Exception as e:
            print(f"Erro ao notificar congelamento: {e}")
            return False
        finally:
            conn.close()

    def notificar_vaga_excluida(self, vaga_id):
        """Notifica candidatos sobre exclusão de vaga"""
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT DISTINCT c.id, c.nome, c.email, v.titulo, e.nome
                FROM candidaturas ca
                JOIN candidatos c ON ca.candidato_id = c.id
                JOIN vagas v ON ca.vaga_id = v.id
                JOIN empresas e ON v.empresa_id = e.id
                WHERE ca.vaga_id = ?
            ''', (vaga_id,))
            
            candidatos = cursor.fetchall()
            
            for candidato in candidatos:
                candidato_id, nome, email, vaga_titulo, empresa_nome = candidato
                
                mensagem = f"""❌ A vaga '{vaga_titulo}' da empresa {empresa_nome} foi excluída.

Infelizmente, o processo seletivo para esta vaga foi encerrado. Continue explorando outras oportunidades em nosso sistema!"""
                
                self.criar_notificacao(candidato_id, mensagem, vaga_id, None, 'vaga_excluida')
                
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

def criar_notificacao(candidato_id, mensagem, vaga_id=None, empresa_id=None, tipo='geral'):
    return notification_system.criar_notificacao(candidato_id, mensagem, vaga_id, empresa_id, tipo)

def notificar_alteracao_vaga(vaga_id, tipo_alteracao='atualizada'):
    return notification_system.notificar_alteracao_vaga(vaga_id, tipo_alteracao)

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

        cursor.execute(query, (candidato_id,))
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
        cursor.execute('''
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
        cursor.execute('''
            UPDATE notificacoes 
            SET lida = 1 
            WHERE candidato_id = ? AND lida = 0
        ''', (candidato_id,))

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
        cursor.execute('''
            SELECT COUNT(*) FROM notificacoes 
            WHERE candidato_id = ? AND lida = 0
        ''', (candidato_id,))

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
        cursor.execute('''
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
