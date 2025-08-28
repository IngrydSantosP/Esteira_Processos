
import sqlite3
import schedule
import time
from datetime import datetime, date
import threading
import os
import sys

# Adicionar o diretório atual ao sys.path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.notifications import notification_system

def verificar_vagas_para_congelar():
    """
    Verifica vagas que devem ser congeladas automaticamente hoje
    """
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Verificando vagas para congelamento...")
        
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        # Buscar vagas que devem ser congeladas hoje
        hoje = date.today().strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT id, titulo, empresa_id, data_congelamento_agendado
            FROM vagas 
            WHERE data_congelamento_agendado = ? 
            AND status = 'Ativa'
        ''', (hoje,))
        
        vagas_para_congelar = cursor.fetchall()
        
        if not vagas_para_congelar:
            print(f"Nenhuma vaga para congelar hoje ({hoje})")
            return
        
        vagas_congeladas = 0
        
        for vaga in vagas_para_congelar:
            vaga_id, titulo, empresa_id, data_congelamento = vaga
            
            try:
                # Atualizar status da vaga para congelada
                cursor.execute('''
                    UPDATE vagas 
                    SET status = 'Congelada' 
                    WHERE id = ?
                ''', (vaga_id,))
                
                # Notificar candidatos
                notification_system.notificar_vaga_congelada(vaga_id)
                
                vagas_congeladas += 1
                print(f"Vaga '{titulo}' (ID: {vaga_id}) congelada automaticamente")
                
            except Exception as e:
                print(f"Erro ao congelar vaga {vaga_id}: {e}")
        
        conn.commit()
        print(f"Total de vagas congeladas: {vagas_congeladas}")
        
    except Exception as e:
        print(f"Erro na verificação de congelamento: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def verificar_vagas_urgentes():
    """
    Verifica vagas com urgência 'Imediata' que ainda não foram preenchidas
    """
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Verificando vagas urgentes...")
        
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        # Buscar vagas urgentes ativas há mais de 7 dias
        cursor.execute('''
            SELECT v.id, v.titulo, v.empresa_id, v.data_criacao,
                   COUNT(ca.id) as total_candidatos
            FROM vagas v
            LEFT JOIN candidaturas ca ON v.id = ca.vaga_id
            WHERE v.urgencia_contratacao = 'Imediata' 
            AND v.status = 'Ativa'
            AND datetime(v.data_criacao) <= datetime('now', '-7 days')
            GROUP BY v.id
        ''')
        
        vagas_urgentes = cursor.fetchall()
        
        for vaga in vagas_urgentes:
            vaga_id, titulo, empresa_id, data_criacao, total_candidatos = vaga
            
            # Buscar email da empresa
            cursor.execute('SELECT email FROM empresas WHERE id = ?', (empresa_id,))
            empresa_email = cursor.fetchone()
            
            if empresa_email:
                assunto = f"⏰ Lembrete: Vaga Urgente - {titulo}"
                mensagem = f"""Sua vaga '{titulo}' está marcada como 'Contratação Imediata' e está ativa há mais de 7 dias.

Estatísticas:
• Total de candidatos: {total_candidatos}
• Data de criação: {data_criacao}

Acesse o sistema para revisar os candidatos ou atualizar o status da vaga."""
                
                notification_system.enviar_email(empresa_email[0], assunto, mensagem)
                print(f"Lembrete enviado para vaga urgente: {titulo}")
        
    except Exception as e:
        print(f"Erro na verificação de vagas urgentes: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def estatisticas_diarias():
    """
    Gera estatísticas diárias do sistema
    """
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Gerando estatísticas diárias...")
        
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        # Estatísticas básicas
        cursor.execute('SELECT COUNT(*) FROM vagas WHERE status = "Ativa"')
        vagas_ativas = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM candidaturas WHERE date(data_candidatura) = date("now")')
        candidaturas_hoje = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM vagas WHERE status = "Concluída" AND date(data_criacao) = date("now")')
        vagas_concluidas_hoje = cursor.fetchone()[0]
        
        print(f"Estatísticas do dia {date.today().strftime('%d/%m/%Y')}:")
        print(f"• Vagas ativas: {vagas_ativas}")
        print(f"• Candidaturas hoje: {candidaturas_hoje}")
        print(f"• Vagas concluídas hoje: {vagas_concluidas_hoje}")
        
    except Exception as e:
        print(f"Erro ao gerar estatísticas: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def iniciar_scheduler_background():
    """
    Inicia o scheduler em background thread
    """
    def run_scheduler():
        print("Sistema de agendamento iniciado em background...")
        
        # Agendar tarefas
        schedule.every().day.at("00:01").do(verificar_vagas_para_congelar)
        schedule.every().day.at("09:00").do(verificar_vagas_urgentes)
        schedule.every().day.at("23:59").do(estatisticas_diarias)
        
        # Executar verificação inicial
        verificar_vagas_para_congelar()
        
        # Loop principal
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto
    
    # Iniciar em thread separada
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    return scheduler_thread

def iniciar_scheduler():
    """
    Inicia o agendador para verificar vagas todos os dias às 00:01
    """
    print("Iniciando sistema de agendamento...")
    
    # Agendar verificação diária
    schedule.every().day.at("00:01").do(verificar_vagas_para_congelar)
    schedule.every().day.at("09:00").do(verificar_vagas_urgentes)
    schedule.every().day.at("23:59").do(estatisticas_diarias)
    
    # Executar uma verificação imediata ao iniciar
    verificar_vagas_para_congelar()
    
    # Loop principal do scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar a cada minuto

if __name__ == "__main__":
    iniciar_scheduler()
