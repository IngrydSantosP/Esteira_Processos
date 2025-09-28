
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from db import get_db_connection
import json

score_bp = Blueprint("score", __name__)

class GerenciadorScore:
    """Gerencia configurações personalizadas de score por empresa"""
    
    @staticmethod
    def obter_configuracao_empresa(empresa_id, nome_config="Padrão"):
        """Obtém configuração de score da empresa"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT peso_salarial, peso_requisitos, peso_experiencia, 
                   peso_diferenciais, peso_localizacao, peso_formacao
            FROM configuracoes_score_empresa 
            WHERE empresa_id = %s AND nome_configuracao = %s AND ativo = TRUE
        """, (empresa_id, nome_config))
        
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            return {
                'salarial': float(resultado[0]),
                'requisitos': float(resultado[1]),
                'experiencia': float(resultado[2]),
                'diferenciais': float(resultado[3]),
                'localizacao': float(resultado[4]),
                'formacao': float(resultado[5])
            }
        
        # Retorna configuração padrão se não encontrar
        return {
            'salarial': 20.0,
            'requisitos': 40.0,
            'experiencia': 15.0,
            'diferenciais': 10.0,
            'localizacao': 10.0,
            'formacao': 5.0
        }
    
    @staticmethod
    def salvar_configuracao(empresa_id, pesos, nome_config="Padrão"):
        """Salva configuração personalizada de score"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO configuracoes_score_empresa 
                (empresa_id, nome_configuracao, peso_salarial, peso_requisitos, 
                 peso_experiencia, peso_diferenciais, peso_localizacao, peso_formacao)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                peso_salarial = VALUES(peso_salarial),
                peso_requisitos = VALUES(peso_requisitos),
                peso_experiencia = VALUES(peso_experiencia),
                peso_diferenciais = VALUES(peso_diferenciais),
                peso_localizacao = VALUES(peso_localizacao),
                peso_formacao = VALUES(peso_formacao),
                data_atualizacao = CURRENT_TIMESTAMP
            """, (empresa_id, nome_config, pesos['salarial'], pesos['requisitos'],
                  pesos['experiencia'], pesos['diferenciais'], 
                  pesos['localizacao'], pesos['formacao']))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Erro ao salvar configuração: {e}")
            return False
        finally:
            conn.close()

@score_bp.route("/configurar-score")
def configurar_score():
    """Página para configurar pesos do score"""
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))
    
    # Obter configuração atual
    pesos_atuais = GerenciadorScore.obter_configuracao_empresa(session["empresa_id"])
    
    # Obter templates disponíveis
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates_score ORDER BY categoria, nome_template")
    templates = cursor.fetchall()
    conn.close()
    
    return render_template("empresa/configurar_score.html", 
                         pesos=pesos_atuais, 
                         templates=templates)

@score_bp.route("/salvar-configuracao-score", methods=["POST"])
def salvar_configuracao_score():
    """Salva configuração personalizada de score"""
    if "empresa_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    try:
        data = request.get_json()
        pesos = data.get("pesos", {})
        
        # Validar se a soma dos pesos é 100
        soma_pesos = sum(float(peso) for peso in pesos.values())
        if abs(soma_pesos - 100) > 0.1:
            return jsonify({"error": f"A soma dos pesos deve ser 100%. Atual: {soma_pesos}%"}), 400
        
        # Salvar configuração
        sucesso = GerenciadorScore.salvar_configuracao(session["empresa_id"], pesos)
        
        if sucesso:
            return jsonify({"success": True, "message": "Configuração salva com sucesso!"})
        else:
            return jsonify({"error": "Erro ao salvar configuração"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@score_bp.route("/aplicar-template-score", methods=["POST"])
def aplicar_template_score():
    """Aplica template de score pré-definido"""
    if "empresa_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    try:
        data = request.get_json()
        template_id = data.get("template_id")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar template
        cursor.execute("""
            SELECT peso_salarial, peso_requisitos, peso_experiencia, 
                   peso_diferenciais, peso_localizacao, peso_formacao
            FROM templates_score WHERE id = %s
        """, (template_id,))
        
        template = cursor.fetchone()
        conn.close()
        
        if not template:
            return jsonify({"error": "Template não encontrado"}), 404
        
        pesos = {
            'salarial': float(template[0]),
            'requisitos': float(template[1]),
            'experiencia': float(template[2]),
            'diferenciais': float(template[3]),
            'localizacao': float(template[4]),
            'formacao': float(template[5])
        }
        
        # Salvar configuração
        sucesso = GerenciadorScore.salvar_configuracao(session["empresa_id"], pesos)
        
        if sucesso:
            return jsonify({"success": True, "pesos": pesos})
        else:
            return jsonify({"error": "Erro ao aplicar template"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@score_bp.route("/visualizar-metodologia/<int:candidato_id>/<int:vaga_id>")
def visualizar_metodologia(candidato_id, vaga_id):
    """Visualiza detalhes da metodologia de cálculo do score"""
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se a empresa tem acesso
    cursor.execute("""
        SELECT v.id FROM vagas v 
        WHERE v.id = %s AND v.empresa_id = %s
    """, (vaga_id, session["empresa_id"]))
    
    if not cursor.fetchone():
        flash("Acesso negado", "error")
        return redirect(url_for("vagas.dashboard_empresa"))
    
    # Buscar dados detalhados do score
    cursor.execute("""
        SELECT score_salarial, score_requisitos, score_experiencia,
               score_diferenciais, score_localizacao, score_formacao,
               score_final, metodologia_utilizada
        FROM historico_scores_detalhados hsd
        JOIN candidaturas c ON hsd.candidatura_id = c.id
        WHERE c.candidato_id = %s AND c.vaga_id = %s
        ORDER BY hsd.data_calculo DESC LIMIT 1
    """, (candidato_id, vaga_id))
    
    score_detalhado = cursor.fetchone()
    
    # Buscar dados do candidato e vaga
    cursor.execute("""
        SELECT cand.nome, cand.resumo_profissional, v.titulo, v.requisitos
        FROM candidatos cand, vagas v
        WHERE cand.id = %s AND v.id = %s
    """, (candidato_id, vaga_id))
    
    dados_gerais = cursor.fetchone()
    conn.close()
    
    return render_template("empresa/metodologia_score.html",
                         score_detalhado=score_detalhado,
                         dados_gerais=dados_gerais,
                         candidato_id=candidato_id,
                         vaga_id=vaga_id)
