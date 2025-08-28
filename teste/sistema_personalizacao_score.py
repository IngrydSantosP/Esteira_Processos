"""
Sistema de Gerenciamento de Personalização de Score
Permite que empresas configurem e gerenciem suas preferências de avaliação
"""

import json
import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime


class GerenciadorPersonalizacaoScore:
    """Gerencia as configurações personalizadas de score por empresa"""

    def __init__(self, db_path: str = "esteira.db"):
        """
        Inicializa o gerenciador com conexão ao banco de dados
        
        Args:
            db_path: Caminho para o banco de dados SQLite
        """
        self.db_path = db_path
        self._criar_tabelas()

    def _criar_tabelas(self):
        """Cria as tabelas necessárias para armazenar configurações"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabela para configurações de score por empresa
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes_score (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome_configuracao TEXT NOT NULL DEFAULT 'Configuração Padrão',
                configuracao_json TEXT NOT NULL,
                ativa BOOLEAN DEFAULT TRUE,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas (id),
                UNIQUE(empresa_id, nome_configuracao)
            )
        """)

        # Tabela para templates de configuração pré-definidos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates_score (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_template TEXT NOT NULL UNIQUE,
                descricao TEXT,
                configuracao_json TEXT NOT NULL,
                categoria TEXT DEFAULT 'geral',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela para histórico de configurações
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_configuracoes_score (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                configuracao_anterior TEXT,
                configuracao_nova TEXT,
                usuario_alteracao TEXT,
                data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                motivo_alteracao TEXT,
                FOREIGN KEY (empresa_id) REFERENCES empresas (id)
            )
        """)

        conn.commit()
        conn.close()

        # Inserir templates padrão se não existirem
        self._inserir_templates_padrao()

    def _inserir_templates_padrao(self):
        """Insere templates de configuração pré-definidos"""
        templates_padrao = [
            {
                "nome": "Padrão Equilibrado",
                "descricao": "Configuração equilibrada para a maioria das vagas",
                "categoria": "geral",
                "configuracao": {
                    "pesos_categorias": {
                        "salarial": {"peso": 20, "ativo": True},
                        "requisitos": {"peso": 40, "ativo": True},
                        "experiencia": {"peso": 15, "ativo": True},
                        "diferenciais": {"peso": 10, "ativo": True},
                        "localizacao": {"peso": 10, "ativo": True},
                        "formacao": {"peso": 5, "ativo": True}
                    }
                }
            },
            {
                "nome": "Foco em Habilidades Técnicas",
                "descricao": "Prioriza requisitos técnicos e experiência",
                "categoria": "tecnologia",
                "configuracao": {
                    "pesos_categorias": {
                        "salarial": {"peso": 10, "ativo": True},
                        "requisitos": {"peso": 50, "ativo": True},
                        "experiencia": {"peso": 25, "ativo": True},
                        "diferenciais": {"peso": 10, "ativo": True},
                        "localizacao": {"peso": 5, "ativo": True},
                        "formacao": {"peso": 0, "ativo": False}
                    }
                }
            },
            {
                "nome": "Startup Flexível",
                "descricao": "Para startups que valorizam flexibilidade e potencial",
                "categoria": "startup",
                "configuracao": {
                    "pesos_categorias": {
                        "salarial": {"peso": 30, "ativo": True},
                        "requisitos": {"peso": 30, "ativo": True},
                        "experiencia": {"peso": 10, "ativo": True},
                        "diferenciais": {"peso": 20, "ativo": True},
                        "localizacao": {"peso": 10, "ativo": True},
                        "formacao": {"peso": 0, "ativo": False}
                    }
                }
            },
            {
                "nome": "Empresa Tradicional",
                "descricao": "Para empresas que valorizam formação e localização",
                "categoria": "tradicional",
                "configuracao": {
                    "pesos_categorias": {
                        "salarial": {"peso": 15, "ativo": True},
                        "requisitos": {"peso": 35, "ativo": True},
                        "experiencia": {"peso": 20, "ativo": True},
                        "diferenciais": {"peso": 5, "ativo": True},
                        "localizacao": {"peso": 15, "ativo": True},
                        "formacao": {"peso": 10, "ativo": True}
                    }
                }
            },
            {
                "nome": "Remoto First",
                "descricao": "Para empresas 100% remotas",
                "categoria": "remoto",
                "configuracao": {
                    "pesos_categorias": {
                        "salarial": {"peso": 25, "ativo": True},
                        "requisitos": {"peso": 45, "ativo": True},
                        "experiencia": {"peso": 20, "ativo": True},
                        "diferenciais": {"peso": 10, "ativo": True},
                        "localizacao": {"peso": 0, "ativo": False},
                        "formacao": {"peso": 0, "ativo": False}
                    }
                }
            }
        ]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for template in templates_padrao:
            cursor.execute("""
                INSERT OR IGNORE INTO templates_score 
                (nome_template, descricao, categoria, configuracao_json)
                VALUES (?, ?, ?, ?)
            """, (
                template["nome"],
                template["descricao"],
                template["categoria"],
                json.dumps(template["configuracao"], ensure_ascii=False)
            ))

        conn.commit()
        conn.close()

    def salvar_configuracao_empresa(self, empresa_id: int, configuracao: Dict[str, Any],
                                   nome_configuracao: str = "Configuração Padrão",
                                   usuario_alteracao: str = None,
                                   motivo_alteracao: str = None) -> bool:
        """
        Salva ou atualiza a configuração de score de uma empresa
        
        Args:
            empresa_id: ID da empresa
            configuracao: Dicionário com a configuração
            nome_configuracao: Nome da configuração
            usuario_alteracao: Usuário que fez a alteração
            motivo_alteracao: Motivo da alteração
            
        Returns:
            bool: True se salvou com sucesso
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Buscar configuração anterior para histórico
            cursor.execute("""
                SELECT configuracao_json FROM configuracoes_score 
                WHERE empresa_id = ? AND nome_configuracao = ?
            """, (empresa_id, nome_configuracao))
            
            resultado = cursor.fetchone()
            configuracao_anterior = resultado[0] if resultado else None

            # Inserir ou atualizar configuração
            cursor.execute("""
                INSERT OR REPLACE INTO configuracoes_score 
                (empresa_id, nome_configuracao, configuracao_json, ativa, data_atualizacao)
                VALUES (?, ?, ?, TRUE, CURRENT_TIMESTAMP)
            """, (
                empresa_id,
                nome_configuracao,
                json.dumps(configuracao, ensure_ascii=False)
            ))

            # Registrar no histórico se houve alteração
            if configuracao_anterior:
                cursor.execute("""
                    INSERT INTO historico_configuracoes_score 
                    (empresa_id, configuracao_anterior, configuracao_nova, usuario_alteracao, motivo_alteracao)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    empresa_id,
                    configuracao_anterior,
                    json.dumps(configuracao, ensure_ascii=False),
                    usuario_alteracao,
                    motivo_alteracao
                ))

            conn.commit()
            return True

        except Exception as e:
            print(f"Erro ao salvar configuração: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def obter_configuracao_empresa(self, empresa_id: int, 
                                  nome_configuracao: str = "Configuração Padrão") -> Optional[Dict[str, Any]]:
        """
        Obtém a configuração de score de uma empresa
        
        Args:
            empresa_id: ID da empresa
            nome_configuracao: Nome da configuração
            
        Returns:
            Dict com a configuração ou None se não encontrar
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT configuracao_json FROM configuracoes_score 
            WHERE empresa_id = ? AND nome_configuracao = ? AND ativa = TRUE
        """, (empresa_id, nome_configuracao))

        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            return json.loads(resultado[0])
        return None

    def listar_configuracoes_empresa(self, empresa_id: int) -> List[Dict[str, Any]]:
        """
        Lista todas as configurações de uma empresa
        
        Args:
            empresa_id: ID da empresa
            
        Returns:
            Lista de configurações
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT nome_configuracao, configuracao_json, ativa, data_criacao, data_atualizacao
            FROM configuracoes_score 
            WHERE empresa_id = ?
            ORDER BY data_atualizacao DESC
        """, (empresa_id,))

        resultados = cursor.fetchall()
        conn.close()

        configuracoes = []
        for resultado in resultados:
            configuracoes.append({
                "nome": resultado[0],
                "configuracao": json.loads(resultado[1]),
                "ativa": bool(resultado[2]),
                "data_criacao": resultado[3],
                "data_atualizacao": resultado[4]
            })

        return configuracoes

    def obter_templates_disponiveis(self, categoria: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtém templates de configuração disponíveis
        
        Args:
            categoria: Filtrar por categoria (opcional)
            
        Returns:
            Lista de templates
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if categoria:
            cursor.execute("""
                SELECT nome_template, descricao, categoria, configuracao_json
                FROM templates_score 
                WHERE categoria = ?
                ORDER BY nome_template
            """, (categoria,))
        else:
            cursor.execute("""
                SELECT nome_template, descricao, categoria, configuracao_json
                FROM templates_score 
                ORDER BY categoria, nome_template
            """)

        resultados = cursor.fetchall()
        conn.close()

        templates = []
        for resultado in resultados:
            templates.append({
                "nome": resultado[0],
                "descricao": resultado[1],
                "categoria": resultado[2],
                "configuracao": json.loads(resultado[3])
            })

        return templates

    def aplicar_template_empresa(self, empresa_id: int, nome_template: str,
                                nome_configuracao: str = "Configuração Padrão",
                                usuario_alteracao: str = None) -> bool:
        """
        Aplica um template de configuração a uma empresa
        
        Args:
            empresa_id: ID da empresa
            nome_template: Nome do template a aplicar
            nome_configuracao: Nome da configuração na empresa
            usuario_alteracao: Usuário que aplicou o template
            
        Returns:
            bool: True se aplicou com sucesso
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Buscar template
        cursor.execute("""
            SELECT configuracao_json FROM templates_score 
            WHERE nome_template = ?
        """, (nome_template,))

        resultado = cursor.fetchone()
        conn.close()

        if not resultado:
            return False

        configuracao_template = json.loads(resultado[0])
        
        return self.salvar_configuracao_empresa(
            empresa_id, configuracao_template, nome_configuracao,
            usuario_alteracao, f"Template '{nome_template}' aplicado"
        )

    def validar_configuracao(self, configuracao: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Valida uma configuração de score
        
        Args:
            configuracao: Configuração a validar
            
        Returns:
            Tuple[bool, List[str]]: (é_válida, lista_de_erros)
        """
        erros = []

        # Verificar estrutura básica
        if "pesos_categorias" not in configuracao:
            erros.append("Configuração deve conter 'pesos_categorias'")
            return False, erros

        pesos_categorias = configuracao["pesos_categorias"]
        categorias_obrigatorias = ["salarial", "requisitos", "experiencia", "diferenciais", "localizacao", "formacao"]

        # Verificar se todas as categorias estão presentes
        for categoria in categorias_obrigatorias:
            if categoria not in pesos_categorias:
                erros.append(f"Categoria '{categoria}' não encontrada")

        # Verificar pesos
        soma_pesos = 0
        for categoria, config in pesos_categorias.items():
            if "peso" not in config:
                erros.append(f"Categoria '{categoria}' deve ter 'peso'")
                continue
            
            if "ativo" not in config:
                erros.append(f"Categoria '{categoria}' deve ter 'ativo'")
                continue

            peso = config["peso"]
            ativo = config["ativo"]

            if not isinstance(peso, (int, float)) or peso < 0:
                erros.append(f"Peso da categoria '{categoria}' deve ser um número não negativo")

            if not isinstance(ativo, bool):
                erros.append(f"Campo 'ativo' da categoria '{categoria}' deve ser boolean")

            if ativo:
                soma_pesos += peso

        # Verificar se soma dos pesos ativos é 100
        if abs(soma_pesos - 100) > 0.1:  # Tolerância para problemas de ponto flutuante
            erros.append(f"Soma dos pesos das categorias ativas deve ser 100, atual: {soma_pesos}")

        return len(erros) == 0, erros

    def obter_historico_alteracoes(self, empresa_id: int, limite: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém histórico de alterações de configuração de uma empresa
        
        Args:
            empresa_id: ID da empresa
            limite: Número máximo de registros a retornar
            
        Returns:
            Lista com histórico de alterações
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT configuracao_anterior, configuracao_nova, usuario_alteracao, 
                   data_alteracao, motivo_alteracao
            FROM historico_configuracoes_score 
            WHERE empresa_id = ?
            ORDER BY data_alteracao DESC
            LIMIT ?
        """, (empresa_id, limite))

        resultados = cursor.fetchall()
        conn.close()

        historico = []
        for resultado in resultados:
            historico.append({
                "configuracao_anterior": json.loads(resultado[0]) if resultado[0] else None,
                "configuracao_nova": json.loads(resultado[1]),
                "usuario_alteracao": resultado[2],
                "data_alteracao": resultado[3],
                "motivo_alteracao": resultado[4]
            })

        return historico

    def exportar_configuracao(self, empresa_id: int, 
                             nome_configuracao: str = "Configuração Padrão") -> Optional[str]:
        """
        Exporta configuração de empresa para JSON
        
        Args:
            empresa_id: ID da empresa
            nome_configuracao: Nome da configuração
            
        Returns:
            String JSON da configuração ou None se não encontrar
        """
        configuracao = self.obter_configuracao_empresa(empresa_id, nome_configuracao)
        if configuracao:
            return json.dumps(configuracao, indent=2, ensure_ascii=False)
        return None

    def importar_configuracao(self, empresa_id: int, configuracao_json: str,
                             nome_configuracao: str = "Configuração Padrão",
                             usuario_alteracao: str = None) -> tuple[bool, List[str]]:
        """
        Importa configuração de JSON
        
        Args:
            empresa_id: ID da empresa
            configuracao_json: String JSON com configuração
            nome_configuracao: Nome da configuração
            usuario_alteracao: Usuário que importou
            
        Returns:
            Tuple[bool, List[str]]: (sucesso, lista_de_erros)
        """
        try:
            configuracao = json.loads(configuracao_json)
        except json.JSONDecodeError as e:
            return False, [f"JSON inválido: {e}"]

        # Validar configuração
        valida, erros = self.validar_configuracao(configuracao)
        if not valida:
            return False, erros

        # Salvar configuração
        sucesso = self.salvar_configuracao_empresa(
            empresa_id, configuracao, nome_configuracao,
            usuario_alteracao, "Configuração importada"
        )

        return sucesso, [] if sucesso else ["Erro ao salvar configuração"]


# Exemplo de uso
if __name__ == "__main__":
    gerenciador = GerenciadorPersonalizacaoScore()

    # Exemplo: aplicar template a uma empresa
    sucesso = gerenciador.aplicar_template_empresa(
        empresa_id=1,
        nome_template="Foco em Habilidades Técnicas",
        usuario_alteracao="admin"
    )
    print(f"Template aplicado: {sucesso}")

    # Exemplo: obter configuração da empresa
    config = gerenciador.obter_configuracao_empresa(1)
    print(f"Configuração da empresa: {json.dumps(config, indent=2, ensure_ascii=False)}")

    # Exemplo: listar templates disponíveis
    templates = gerenciador.obter_templates_disponiveis()
    print(f"Templates disponíveis: {len(templates)}")
    for template in templates:
        print(f"- {template['nome']} ({template['categoria']}): {template['descricao']}")

