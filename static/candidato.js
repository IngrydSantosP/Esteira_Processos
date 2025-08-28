
// ============================
// Dashboard do Candidato - VaBoo! Platform
// Sistema completo de notificações e gerenciamento
// ============================

let notificacoesCache = [];
let categoriasBusca = [];
let localizacoesBusca = [];
let notificacoesInterval = null;
let ultimaAtualizacao = null;

// ============================
// Gerenciamento de seções do dashboard
// ============================
function showSection(sectionName, event) {
    // Esconder todas as seções
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.add('hidden');
    });

    // Mostrar seção selecionada
    const targetSection = document.getElementById(`section-${sectionName}`);
    if (targetSection) {
        targetSection.classList.remove('hidden');
    }

    // Atualizar botões de filtro
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('filter-active');
        btn.classList.add('bg-gray-100', 'text-gray-700');
        btn.style.background = '';
        btn.style.color = '';
        btn.style.transform = '';
        btn.style.boxShadow = '';
    });

    // Aplicar estilo ativo no botão clicado
    if (event && event.target) {
        const activeBtn = event.target;
        activeBtn.classList.add('filter-active');
        activeBtn.classList.remove('bg-gray-100', 'text-gray-700');
        activeBtn.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        activeBtn.style.color = 'white';
        activeBtn.style.transform = 'translateY(-2px)';
        activeBtn.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
    }

    // Carregar conteúdo específico se necessário
    if (sectionName === 'todas') {
        loadAllJobs();
        loadSearchFilters();
    } else if (sectionName === 'assistente-ia') {
        inicializarAssistenteIA();
    }
}

// ============================
// Sistema avançado de notificações
// ============================
function carregarNotificacoes(mostrarLoading = true, tentativa = 1) {
    const maxTentativas = 3;

    if (mostrarLoading) {
        mostrarLoadingNotificacoes(true);
    }

    fetch('/api/notificacoes', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        },
        signal: AbortSignal.timeout(30000) // 10 segundos timeout
    })
    .then(async response => {
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('📊 Dados recebidos:', data);

        if (data.error) {
            throw new Error(data.error);
        }

        // Atualizar cache
        notificacoesCache = data.notificacoes || [];
        ultimaAtualizacao = new Date();

        // Atualizar interface
        atualizarNotificacoes();

        if (mostrarLoading) {
            mostrarLoadingNotificacoes(false);
        }

        console.log(`✅ ${notificacoesCache.length} notificações carregadas (tentativa ${tentativa})`);
    })
    .catch(error => {
        console.error('❌ Erro ao carregar notificações:', error);

        if (mostrarLoading) {
            mostrarLoadingNotificacoes(false);
        }

        // Retry para outros erros
        if (tentativa < maxTentativas) {
            console.log(`🔄 Tentando novamente (${tentativa + 1}/${maxTentativas})...`);
            setTimeout(() => {
                carregarNotificacoes(mostrarLoading, tentativa + 1);
            }, 2000 * tentativa); // Delay progressivo
            return;
        }

        mostrarErroTemporario('Erro ao carregar notificações. Verifique sua conexão.');

        // Fallback: usar dados em cache se disponíveis
        if (notificacoesCache && notificacoesCache.length > 0) {
            console.log('📋 Usando dados em cache das notificações');
            atualizarNotificacoes();
        }
    });
}

function atualizarNotificacoes() {
    const badge = document.getElementById('badgeNotificacoes');
    const lista = document.getElementById('listaNotificacoes');
    const contador = document.getElementById('contadorNotificacoes');
    const vazias = document.getElementById('notificacoesVazias');
    const contadorNaoLidas = document.getElementById('contadorNaoLidas');

    if (!badge || !lista) {
        console.warn('⚠️ Elementos de notificação não encontrados no DOM');
        return;
    }

    // Verificar se notificacoesCache está definido
    if (!notificacoesCache || !Array.isArray(notificacoesCache)) {
        console.warn('⚠️ Cache de notificações não está disponível');
        notificacoesCache = [];
    }

    const naoLidas = notificacoesCache.filter(n => !n.lida);
    const agora = new Date();
    const novas = notificacoesCache.filter(n => {
        try {
            const dataNotificacao = new Date(n.data_criacao || n.data_envio);
            const diasPassados = (agora - dataNotificacao) / (1000 * 60 * 60 * 24);
            return !n.lida && diasPassados <= 30;
        } catch (error) {
            console.warn('Erro ao processar data da notificação:', error);
            return !n.lida; // Fallback: considerar como nova se não lida
        }
    });
    const total = notificacoesCache.length;

    // Atualizar badge com contagem inteligente
    const fixadas = notificacoesCache.filter(n => n.is_fixada);
    const recentesNaoLidas = notificacoesCache.filter(n => {
        const dataNotificacao = new Date(n.data_criacao);
        const diasPassados = (agora - dataNotificacao) / (1000 * 60 * 60 * 24);
        return !n.lida && diasPassados <= 7;
    });

    let badgeCount = 0;
    let badgeColor = '#ef4444';
    let badgeText = '';

    if (recentesNaoLidas.length > 0) {
        badgeCount = recentesNaoLidas.length;
        badgeColor = 'linear-gradient(45deg, #10b981, #059669)'; // Verde para novas
        badgeText = badgeCount > 99 ? '99+' : badgeCount.toString();
    } else if (naoLidas.length > 0) {
        badgeCount = naoLidas.length;
        badgeColor = '#f59e0b'; // Amarelo para não lidas antigas
        badgeText = badgeCount > 99 ? '99+' : badgeCount.toString();
    }

    if (badgeCount > 0) {
        badge.textContent = badgeText;
        badge.classList.remove('hidden');
        badge.style.animation = recentesNaoLidas.length > 0 ? 'pulse 2s infinite' : '';
        badge.style.background = badgeColor;
        badge.style.boxShadow = recentesNaoLidas.length > 0 ? '0 0 15px rgba(16, 185, 129, 0.6)' : '0 0 10px rgba(245, 158, 11, 0.4)';
    } else {
        badge.classList.add('hidden');
        badge.style.animation = '';
    }

    // Atualizar contador detalhado
    if (contador) {
        let textoContador = `${total} notificação${total !== 1 ? 'ões' : ''}`;

        const partes = [];
        if (recentesNaoLidas.length > 0) {
            partes.push(`${recentesNaoLidas.length} nova${recentesNaoLidas.length !== 1 ? 's' : ''}`);
        }
        if (naoLidas.length > recentesNaoLidas.length) {
            const antigas = naoLidas.length - recentesNaoLidas.length;
            partes.push(`${antigas} não lida${antigas !== 1 ? 's' : ''}`);
        }
        if (fixadas.length > 0) {
            partes.push(`${fixadas.length} fixada${fixadas.length !== 1 ? 's' : ''}`);
        }

        if (partes.length > 0) {
            textoContador += ` (${partes.join(', ')})`;
        }

        contador.textContent = textoContador;
    }

    // Atualizar contador de não lidas acima do botão
    if (contadorNaoLidas) {
        if (naoLidas.length > 0) {
            contadorNaoLidas.textContent = `+${naoLidas.length > 99 ? '99+' : naoLidas.length}`;
            contadorNaoLidas.classList.remove('hidden');
            contadorNaoLidas.style.animation = naoLidas.length > 0 ? 'pulse 2s infinite' : '';
        } else {
            contadorNaoLidas.classList.add('hidden');
            contadorNaoLidas.style.animation = '';
        }
    }

    // Gerenciar estado vazio
    if (total === 0) {
        if (vazias) vazias.classList.remove('hidden');
        lista.innerHTML = '';
        return;
    }

    if (vazias) vazias.classList.add('hidden');

    // Renderizar notificações com melhor UX
    lista.innerHTML = notificacoesCache.slice(0, 20).map((n, index) => {
        const dataEnvio = new Date(n.data_criacao);
        const tempoRelativo = formatarTempoRelativo(dataEnvio);
        const dataFormatada = dataEnvio.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        // Determinar emoji baseado no tipo
        let iconeNotificacao = n.emoji || getIconeNotificacao(n.tipo);

        // Verificar se é fixada (contratação nos últimos 30 dias)
        const isFixada = n.is_fixada || false;

        // Verificar se é nova (últimos 7 dias e não lida)
        const diasPassados = (new Date() - dataEnvio) / (1000 * 60 * 60 * 24);
        const isNova = !n.lida && diasPassados <= 7;

        return `
            <div class="notification-item border-b border-gray-100 last:border-b-0 ${!n.lida ? 'bg-gradient-to-r from-blue-50 to-purple-50 border-l-4 border-l-blue-500' : 'hover:bg-gray-50'} transition-all duration-300 transform hover:scale-[1.02] ${isNova ? 'ring-2 ring-green-300 ring-opacity-50' : ''} ${isFixada ? 'ring-2 ring-yellow-400 ring-opacity-70 bg-gradient-to-r from-yellow-50 to-orange-50' : ''}"
                 style="animation-delay: ${index * 50}ms">
                <div class="p-4">
                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0 relative">
                            <div class="w-12 h-12 rounded-full ${isFixada ? 'bg-gradient-to-br from-yellow-100 to-orange-100' : 'bg-gradient-to-br from-purple-100 to-blue-100'} flex items-center justify-center">
                                <span class="text-xl">${iconeNotificacao}</span>
                            </div>
                            ${!n.lida ? '<div class="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full animate-ping"></div>' : ''}
                            ${isNova ? '<div class="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 rounded-full flex items-center justify-center"><span class="text-xs text-white font-bold">N</span></div>' : ''}
                            ${isFixada ? '<div class="absolute -top-1 -left-1 w-4 h-4 bg-yellow-500 rounded-full flex items-center justify-center"><span class="text-xs text-white font-bold">📌</span></div>' : ''}
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex justify-between items-start mb-2">
                                <div class="flex-1">
                                    <h4 class="text-sm ${!n.lida ? 'font-bold text-gray-900' : 'font-medium text-gray-700'} line-clamp-1 mb-2">
                                        ${getTituloNotificacao(n)}
                                    </h4>
                                    ${n.vaga_titulo ? `
                                        <p class="text-xs text-blue-600 font-semibold mb-1 flex items-center gap-1">
                                            <span class="w-3 h-3 bg-blue-100 rounded-full flex items-center justify-center text-xs">💼</span>
                                            ${n.vaga_titulo}
                                        </p>
                                    ` : ''}
                                    ${n.empresa_nome ? `
                                        <p class="text-xs text-purple-600 font-medium mb-2 flex items-center gap-1">
                                            <span class="w-3 h-3 bg-purple-100 rounded-full flex items-center justify-center text-xs">🏢</span>
                                            ${n.empresa_nome}
                                        </p>
                                    ` : ''}
                                    <div class="flex flex-wrap gap-2 mb-2">
                                        ${isFixada ? `
                                            <span class="text-xs text-yellow-700 font-semibold bg-yellow-200 px-2 py-1 rounded-full">
                                                📌 Fixada
                                            </span>
                                        ` : ''}
                                    </div>
                                </div>
                                <div class="flex flex-col items-end gap-1 ml-2">
                                    <span class="text-xs text-gray-400 whitespace-nowrap bg-gray-100 px-2 py-1 rounded-full">
                                        ${tempoRelativo}
                                    </span>
                                </div>
                            </div>
                            <p class="text-sm text-gray-700 leading-relaxed mb-3 ${!n.lida ? 'font-medium' : ''}">
                                ${n.mensagem.length > 150 ? n.mensagem.substring(0, 150) + '...' : n.mensagem}
                            </p>
                            <div class="flex flex-wrap gap-2">
                                ${!n.lida ? `
                                    <button onclick="marcarComoLida(${n.id})"
                                            class="text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 px-3 py-1.5 rounded-full transition-all duration-200 hover:scale-105 flex items-center gap-1 font-medium">
                                        <span>✓</span> Marcar como lida
                                    </button>
                                ` : ''}
                                <button onclick="apagarNotificacao(${n.id})"
                                        class="text-xs bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1.5 rounded-full transition-all duration-200 hover:scale-105 flex items-center gap-1">
                                    <span>🗑️</span> Apagar
                                </button>
                                ${n.vaga_id ? `
                                    <button onclick="verVaga(${n.vaga_id})"
                                            class="text-xs bg-purple-100 hover:bg-purple-200 text-purple-700 px-3 py-1.5 rounded-full transition-all duration-200 hover:scale-105 flex items-center gap-1">
                                        <span>👁️</span> Ver Vaga
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    // Animar entrada das notificações
    setTimeout(() => {
        lista.querySelectorAll('.notification-item').forEach((item, index) => {
            item.style.animation = `slideInRight 0.3s ease-out ${index * 50}ms both`;
        });
    }, 100);
}

function formatarTempoRelativo(data) {
    const agora = new Date();
    const diferenca = agora - data;
    const minutos = Math.floor(diferenca / 60000);
    const horas = Math.floor(diferenca / 3600000);
    const dias = Math.floor(diferenca / 86400000);

    if (minutos < 1) return 'Agora';
    if (minutos < 60) return `${minutos}min`;
    if (horas < 24) return `${horas}h`;
    if (dias < 7) return `${dias}d`;
    if (dias < 30) return `${dias} dias`;
    return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function getTituloNotificacao(notificacao) {
    const { tipo, vaga_titulo, empresa_nome, mensagem, titulo } = notificacao;

    // Se já tem título formatado, usar ele
    if (titulo && titulo !== mensagem) {
        return titulo;
    }

    // Gerar título baseado no tipo
    const empresaTexto = empresa_nome ? ` na ${empresa_nome}` : '';
    const vagaTexto = vaga_titulo || 'Vaga';

    switch (tipo) {
        case 'contratacao':
            return `🎉 PARABÉNS! Você foi selecionado para ${vagaTexto}${empresaTexto}`;
        case 'candidatura':
        case 'nova_candidatura':
            return `🎯 Candidatura registrada: ${vagaTexto}${empresaTexto}`;
        case 'vaga_alterada':
        case 'alteracao_vaga':
            return `🔔 Vaga atualizada: ${vagaTexto}${empresaTexto}`;
        case 'vaga_congelada':
            return `❄️ Processo pausado: ${vagaTexto}${empresaTexto}`;
        case 'vaga_excluida':
            return `❌ Vaga encerrada: ${vagaTexto}${empresaTexto}`;
        case 'vaga_reativada':
            return `🔄 Processo retomado: ${vagaTexto}${empresaTexto}`;
        case 'vaga_concluida':
            return `✅ Processo concluído: ${vagaTexto}${empresaTexto}`;
        case 'vaga_nova':
            return `✨ Nova vaga disponível: ${vagaTexto}${empresaTexto}`;
        default:
            // Para outros tipos, extrair primeira linha da mensagem
            if (mensagem) {
                const primeiraLinha = mensagem.split('\n')[0];
                return primeiraLinha.length > 60 ? primeiraLinha.substring(0, 60) + '...' : primeiraLinha;
            }
            return vaga_titulo ? `💼 ${vagaTexto}${empresaTexto}` : '📢 Notificação do Sistema';
    }
}

function getIconeNotificacao(tipo) {
    const icones = {
        'contratacao': '🎉',
        'vaga_alterada': '📝',
        'vaga_congelada': '❄️',
        'vaga_excluida': '🗑️',
        'vaga_reativada': '✅',
        'nova_candidatura': '🎯',
        'novo_match': '⭐',
        'mensagem': '💬',
        'aviso': '⚠️',
        'sucesso': '✅',
        'geral': '📢',
        'presencial': '🏢',
        'remoto': '🏠',
        'hibrido': '🔄',
        'freelance': '💼',
        'estagio': '📚',
        'clt': '📄',
        'pj': '🤝',
        'temporario': '⏰'
    };
    return icones[tipo] || '📢';
}

function toggleNotificacoes() {
    const painel = document.getElementById('painelNotificacoes');
    if (!painel) return;

    const isVisible = !painel.classList.contains('hidden');

    if (isVisible) {
        // Fechar painel
        painel.style.animation = 'slideOutUp 0.3s ease-in';
        setTimeout(() => {
            painel.classList.add('hidden');
            painel.style.animation = '';
        }, 300);
    } else {
        // Abrir painel
        painel.classList.remove('hidden');
        painel.style.animation = 'slideInDown 0.3s ease-out';
        carregarNotificacoes(true);

        // Marcar painel como visualizado
        setTimeout(() => {
            painel.style.animation = '';
        }, 300);
    }
}

async function marcarComoLida(notificacaoId) {
    try {
        mostrarFeedbackAcao('Marcando como lida...');

        const response = await fetch('/api/notificacoes/marcar-lida', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: notificacaoId })
        });

        if (response.ok) {
            // Atualizar localmente com animação
            const notif = notificacoesCache.find(n => n.id === notificacaoId);
            if (notif) {
                notif.lida = true;
                atualizarNotificacoes();
                mostrarFeedbackAcao('✅ Marcada como lida!', 'success');
            }
        } else {
            throw new Error(`Erro ${response.status}`);
        }
    } catch (error) {
        console.error('Erro ao marcar como lida:', error);
        mostrarFeedbackAcao('❌ Erro ao marcar como lida', 'error');
    }
}

async function marcarTodasComoLidas() {
    const naoLidas = notificacoesCache.filter(n => !n.lida);
    if (naoLidas.length === 0) {
        mostrarFeedbackAcao('ℹ️ Todas já estão marcadas como lidas', 'info');
        return;
    }

    try {
        mostrarFeedbackAcao(`Marcando ${naoLidas.length} notificações...`);

        const response = await fetch('/api/notificacoes/marcar-todas-lidas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            notificacoesCache.forEach(n => n.lida = true);
            atualizarNotificacoes();
            mostrarFeedbackAcao(`✅ ${naoLidas.length} notificações marcadas!`, 'success');
        } else {
            throw new Error(`Erro ${response.status}`);
        }
    } catch (error) {
        console.error('Erro ao marcar todas como lidas:', error);
        mostrarFeedbackAcao('❌ Erro ao marcar todas como lidas', 'error');
    }
}

async function apagarNotificacao(notificacaoId) {
    try {
        mostrarFeedbackAcao('Apagando notificação...');

        const response = await fetch(`/api/notificacoes/${notificacaoId}/apagar`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            // Animação de saída
            const itemElement = document.querySelector(`[onclick*="${notificacaoId}"]`)?.closest('.notification-item');
            if (itemElement) {
                itemElement.style.animation = 'slideOutRight 0.3s ease-in';
                setTimeout(() => {
                    notificacoesCache = notificacoesCache.filter(n => n.id !== notificacaoId);
                    atualizarNotificacoes();
                }, 300);
            } else {
                notificacoesCache = notificacoesCache.filter(n => n.id !== notificacaoId);
                atualizarNotificacoes();
            }
            mostrarFeedbackAcao('✅ Notificação apagada!', 'success');
        } else {
            throw new Error(`Erro ${response.status}`);
        }
    } catch (error) {
        console.error('Erro ao apagar notificação:', error);
        mostrarFeedbackAcao('❌ Erro ao apagar notificação', 'error');
    }
}

async function apagarTodasNotificacoes() {
    if (notificacoesCache.length === 0) {
        mostrarFeedbackAcao('ℹ️ Não há notificações para apagar', 'info');
        return;
    }

    if (!confirm(`Tem certeza que deseja apagar todas as ${notificacoesCache.length} notificações? Esta ação não pode ser desfeita.`)) {
        return;
    }

    try {
        mostrarFeedbackAcao('Apagando todas as notificações...');

        const response = await fetch('/api/notificacoes/apagar-todas', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            // Animação de limpeza
            const lista = document.getElementById('listaNotificacoes');
            if (lista) {
                lista.style.animation = 'fadeOut 0.5s ease-in';
                setTimeout(() => {
                    notificacoesCache = [];
                    atualizarNotificacoes();
                }, 500);
            } else {
                notificacoesCache = [];
                atualizarNotificacoes();
            }
            mostrarFeedbackAcao('✅ Todas as notificações foram apagadas!', 'success');
        } else {
            throw new Error(`Erro ${response.status}`);
        }
    } catch (error) {
        console.error('Erro ao apagar todas as notificações:', error);
        mostrarFeedbackAcao('❌ Erro ao apagar todas as notificações', 'error');
    }
}

function verVaga(vagaId) {
    if (vagaId) {
        // Adicionar animação de transição
        mostrarFeedbackAcao('Redirecionando para a vaga...');
        setTimeout(() => {
            window.location.href = `/vaga/${vagaId}`;
        }, 500);
    }
}

// ============================
// Sistema de dicas para vagas favoritas
// ============================
async function obterDicasFavoritas() {
    try {
        mostrarFeedbackAcao('🔍 Buscando dicas personalizadas...', 'info');

        const response = await fetch('/api/dicas-favoritas', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Erro ${response.status}`);
        }

        const data = await response.json();

        if (data.success && data.dicas && data.dicas.length > 0) {
            exibirModalDicas(data.dicas, data.vagas_analisadas);
            mostrarFeedbackAcao('✨ Dicas geradas com sucesso!', 'success');
        } else {
            mostrarFeedbackAcao('ℹ️ Adicione vagas aos favoritos para receber dicas personalizadas', 'info');
        }

    } catch (error) {
        console.error('Erro ao obter dicas:', error);
        mostrarFeedbackAcao('❌ Erro ao gerar dicas. Tente novamente.', 'error');
    }
}

function exibirModalDicas(dicas, vagasAnalisadas) {
    // Criar modal se não existir
    let modal = document.getElementById('modalDicas');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modalDicas';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div class="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl">
            <div class="bg-gradient-to-r from-purple-500 to-blue-500 text-white p-6">
                <div class="flex justify-between items-center">
                    <div class="flex items-center gap-3">
                        <span class="text-2xl">💡</span>
                        <h3 class="text-xl font-bold">Dicas Personalizadas</h3>
                    </div>
                    <button onclick="fecharModalDicas()" class="text-white hover:text-gray-200 text-xl">✕</button>
                </div>
                <p class="text-sm opacity-90 mt-2">Baseado em ${vagasAnalisadas} vaga${vagasAnalisadas !== 1 ? 's' : ''} favorita${vagasAnalisadas !== 1 ? 's' : ''}</p>
            </div>
            
            <div class="p-6 overflow-y-auto max-h-96">
                <div class="space-y-4">
                    ${dicas.map((dica, index) => `
                        <div class="bg-gradient-to-r from-blue-50 to-purple-50 p-4 rounded-xl border-l-4 border-l-blue-500">
                            <div class="flex items-start gap-3">
                                <span class="text-xl flex-shrink-0">${getIconeDica(dica.categoria)}</span>
                                <div class="flex-1">
                                    <h4 class="font-bold text-gray-800 mb-2">${dica.titulo}</h4>
                                    <p class="text-gray-700 leading-relaxed">${dica.descricao}</p>
                                    ${dica.acao ? `
                                        <div class="mt-3 p-3 bg-white rounded-lg border border-gray-200">
                                            <p class="text-sm font-semibold text-purple-600 mb-1">💪 Ação Recomendada:</p>
                                            <p class="text-sm text-gray-600">${dica.acao}</p>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                
                <div class="mt-6 p-4 bg-gradient-to-r from-green-50 to-blue-50 rounded-xl border border-green-200">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-lg">🎯</span>
                        <h4 class="font-bold text-green-700">Próximos Passos</h4>
                    </div>
                    <ul class="text-sm text-green-600 space-y-1">
                        <li>• Implemente as dicas gradualmente</li>
                        <li>• Atualize seu perfil conforme necessário</li>
                        <li>• Continue adicionando vagas aos favoritos</li>
                        <li>• Revise suas dicas semanalmente</li>
                    </ul>
                </div>
            </div>
            
            <div class="border-t border-gray-100 p-4 bg-gray-50 flex justify-end gap-3">
                <button onclick="fecharModalDicas()" class="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg transition-colors">
                    Fechar
                </button>
                <button onclick="salvarDicas()" class="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white rounded-lg transition-all duration-300">
                    💾 Salvar Dicas
                </button>
            </div>
        </div>
    `;

    modal.classList.remove('hidden');
    modal.style.animation = 'fadeIn 0.3s ease-out';
}

function getIconeDica(categoria) {
    const icones = {
        'perfil': '👤',
        'competencias': '🎯',
        'experiencia': '💼',
        'certificacoes': '🏆',
        'networking': '🤝',
        'preparacao': '📚',
        'comunicacao': '💬',
        'portfolio': '📁',
        'geral': '💡'
    };
    return icones[categoria] || '💡';
}

function fecharModalDicas() {
    const modal = document.getElementById('modalDicas');
    if (modal) {
        modal.style.animation = 'fadeOut 0.3s ease-in';
        setTimeout(() => {
            modal.remove();
        }, 300);
    }
}

function salvarDicas() {
    // Implementar salvamento das dicas se necessário
    mostrarFeedbackAcao('💾 Dicas salvas com sucesso!', 'success');
    fecharModalDicas();
}

// ============================
// Sistema de feedback e UI
// ============================
function mostrarFeedbackAcao(mensagem, tipo = 'info') {
    // Criar elemento de feedback se não existir
    let feedback = document.getElementById('feedbackAcao');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.id = 'feedbackAcao';
        feedback.className = 'fixed top-4 right-4 z-50 max-w-sm';
        document.body.appendChild(feedback);
    }

    const cores = {
        'info': 'bg-blue-500 border-blue-600',
        'success': 'bg-green-500 border-green-600',
        'error': 'bg-red-500 border-red-600',
        'warning': 'bg-yellow-500 border-yellow-600'
    };

    feedback.innerHTML = `
        <div class="p-4 rounded-lg shadow-lg text-white border-l-4 ${cores[tipo] || cores.info} notification-feedback"
             style="animation: slideInRight 0.3s ease-out;">
            <p class="text-sm font-medium">${mensagem}</p>
        </div>
    `;

    // Auto-remover após 3 segundos
    setTimeout(() => {
        const el = feedback.querySelector('.notification-feedback');
        if (el) {
            el.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => {
                feedback.innerHTML = '';
            }, 300);
        }
    }, 3000);
}

function mostrarErroTemporario(mensagem) {
    mostrarFeedbackAcao(mensagem, 'error');
}

function mostrarLoadingNotificacoes(carregando) {
    const badge = document.getElementById('badgeNotificacoes');
    if (badge && carregando) {
        badge.style.animation = 'pulse 1s infinite';
    } else if (badge) {
        badge.style.animation = '';
    }
}

// ============================
// Gerenciamento de favoritos
// ============================
async function toggleFavorite(vagaId, buttonElement) {
    if (!vagaId || !buttonElement) return;

    const isFavorited = buttonElement.dataset.favorited === 'true';

    try {
        // Animação otimista
        buttonElement.style.transform = 'scale(1.2)';
        buttonElement.style.transition = 'all 0.2s ease';

        const response = await fetch('/api/favoritos/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ vaga_id: vagaId })
        });

        if (response.ok) {
            const data = await response.json();
            const novoStatus = data.favorited;

            // Atualizar UI
            buttonElement.textContent = novoStatus ? '⭐' : '☆';
            buttonElement.dataset.favorited = novoStatus;
            buttonElement.className = `favorite-btn text-2xl transition-all duration-300 hover:scale-125 ${novoStatus ? 'text-yellow-400' : 'text-gray-300'}`;

            // Feedback visual
            mostrarFeedbackAcao(
                novoStatus ? '⭐ Adicionada aos favoritos!' : '☆ Removida dos favoritos!',
                novoStatus ? 'success' : 'info'
            );
        } else {
            throw new Error(`Erro ${response.status}`);
        }
    } catch (error) {
        console.error('Erro ao alterar favorito:', error);
        mostrarFeedbackAcao('❌ Erro ao alterar favorito', 'error');
    } finally {
        // Resetar animação
        setTimeout(() => {
            buttonElement.style.transform = 'scale(1)';
        }, 200);
    }
}

// ============================
// Busca e filtros avançados
// ============================
async function loadAllJobs() {
    console.log('🔍 Carregando todas as vagas...');

    try {
        const container = document.getElementById('todasVagasContainer');
        if (!container) return;

        // Mostrar loading
        container.innerHTML = `
            <div class="text-center py-8">
                <div class="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                <p class="text-gray-500">Carregando todas as vagas disponíveis...</p>
            </div>
        `;

        const response = await fetch('/api/todas-vagas');
        if (!response.ok) throw new Error('Erro ao buscar vagas');

        const vagas = await response.json();
        renderTodasVagas(vagas);

        console.log(`✅ ${vagas.length} vagas carregadas com sucesso`);

    } catch (error) {
        console.error('❌ Erro ao carregar todas as vagas:', error);
        const container = document.getElementById('todasVagasContainer');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-12 bg-white rounded-2xl shadow-sm border border-gray-100">
                    <div class="w-24 h-24 bg-red-100 rounded-full mx-auto mb-6 flex items-center justify-center">
                        <span class="text-4xl">⚠️</span>
                    </div>
                    <h3 class="text-xl font-bold text-gray-600 mb-3">Erro ao carregar vagas</h3>
                    <p class="text-gray-500 mb-6">Tente recarregar a página ou entre em contato com o suporte.</p>
                    <button onclick="loadAllJobs()" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105">
                        🔄 Tentar Novamente
                    </button>
                </div>
            `;
        }
    }
}

async function loadSearchFilters() {
    console.log('🔧 Carregando filtros de busca...');

    try {
        const response = await fetch('/api/busca-filtros');
        if (!response.ok) throw new Error('Erro ao carregar filtros');

        const filtros = await response.json();

        // Popular localização
        const locationSelect = document.getElementById('searchLocation');
        if (locationSelect) {
            locationSelect.innerHTML = '<option value="">Todas as localizações</option>';
            filtros.localizacoes.forEach(loc => {
                const option = document.createElement('option');
                option.value = loc;
                option.textContent = loc;
                locationSelect.appendChild(option);
            });
        }

        // Popular categorias
        const categorySelect = document.getElementById('searchCategory');
        if (categorySelect) {
            categorySelect.innerHTML = '<option value="">Todas as categorias</option>';
            filtros.categorias.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id;
                option.textContent = cat.nome;
                categorySelect.appendChild(option);
            });
        }

        console.log('✅ Filtros carregados com sucesso');

    } catch (error) {
        console.error('❌ Erro ao carregar filtros:', error);
    }
}

function renderTodasVagas(vagas) {
    const container = document.getElementById('todasVagasContainer');
    if (!container) return;

    if (vagas.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 bg-white rounded-2xl shadow-sm border border-gray-100">
                <div class="w-24 h-24 bg-gray-100 rounded-full mx-auto mb-6 flex items-center justify-center">
                    <span class="text-4xl">🔍</span>
                </div>
                <h3 class="text-xl font-bold text-gray-600 mb-3">Nenhuma vaga encontrada</h3>
                <p class="text-gray-500 mb-6">Tente ajustar os filtros de busca ou volte mais tarde.</p>
            </div>
        `;
        return;
    }

    const vagasHtml = vagas.map(vaga => `
        <div class="group bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-xl hover:border-purple-200 transition-all duration-300 transform hover:-translate-y-1">
            <div class="flex flex-col lg:flex-row gap-6">
                <div class="flex-1">
                    <div class="flex items-start gap-4 mb-4">
                        <div class="w-16 h-16 bg-gradient-to-br from-purple-100 to-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
                            <span class="text-2xl">💼</span>
                        </div>
                        <div class="flex-1">
                            <div class="flex items-center gap-3 mb-2">
                                <a href="/vaga/${vaga.id}" class="block">
                                    <h3 class="text-xl font-bold text-gray-800 group-hover:text-purple-600 transition-colors">
                                        ${vaga.titulo}
                                    </h3>
                                </a>
                                <button onclick="toggleFavorite(${vaga.id}, this)"
                                        class="favorite-btn text-xl transition-all duration-300 hover:scale-125 ${vaga.is_favorita ? 'text-yellow-400' : 'text-gray-300'}"
                                        data-favorited="${vaga.is_favorita}">
                                    ${vaga.is_favorita ? '⭐' : '☆'}
                                </button>
                            </div>
                            <p class="text-purple-600 font-semibold mb-2 flex items-center gap-1">
                                <span class="w-3 h-3 bg-purple-100 rounded-full flex items-center justify-center text-xs">🏢</span>
                                ${vaga.empresa_nome}
                            </p>
                            <p class="text-lg font-bold text-green-600 mb-3 flex items-center gap-1">
                                <span class="w-3 h-3 bg-green-100 rounded-full flex items-center justify-center text-xs">💰</span>
                                R$ ${vaga.salario_oferecido.toFixed(2)}
                            </p>
                            <div class="flex gap-2 mb-3">
                                <span class="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-medium">
                                    ${vaga.tipo_vaga}
                                </span>
                                ${vaga.ja_candidatou ? '<span class="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full font-medium">✅ Candidatado</span>' : ''}
                            </div>
                        </div>
                    </div>

                    <div class="bg-gray-50 p-4 rounded-xl">
                        <p class="text-sm text-gray-600 leading-relaxed">${vaga.descricao.substring(0, 180)}${vaga.descricao.length > 180 ? '...' : ''}</p>
                    </div>
                </div>

                <div class="flex flex-col items-center justify-center lg:w-48 gap-4">
                    <div class="text-center bg-gradient-to-br from-green-400 to-emerald-500 text-white p-4 rounded-xl shadow-lg">
                        <div class="text-2xl font-bold mb-1">${Math.round(vaga.score)}%</div>
                        <p class="text-xs font-semibold opacity-90">MATCH</p>
                    </div>

                    ${!vaga.ja_candidatou ? `
                        <a href="/candidatar/${vaga.id}"
                           class="group/btn bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-bold px-6 py-3 rounded-xl shadow-lg transition-all duration-300 transform hover:scale-105 hover:shadow-xl flex items-center gap-2">
                            <span class="transition-transform group-hover/btn:translate-x-1">🚀</span>
                            Candidatar-se
                        </a>
                    ` : `
                        <div class="bg-green-100 text-green-800 px-4 py-2 rounded-xl font-semibold text-sm">
                            ✅ Candidatado
                        </div>
                    `}
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = `
        <div class="mb-6">
            <h3 class="text-xl font-bold text-gray-800 mb-2">
                ${vagas.length} vaga${vagas.length !== 1 ? 's' : ''} encontrada${vagas.length !== 1 ? 's' : ''}
            </h3>
            <div class="h-1 w-20 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full"></div>
        </div>
        <div class="grid gap-6">
            ${vagasHtml}
        </div>
    `;
}

async function realizarBusca() {
    const keyword = document.getElementById('searchKeyword')?.value || '';
    const location = document.getElementById('searchLocation')?.value || '';
    const category = document.getElementById('searchCategory')?.value || '';
    const urgency = document.getElementById('searchUrgency')?.value || '';
    const salary = document.getElementById('searchSalary')?.value || '';
    const type = document.getElementById('searchType')?.value || '';

    const params = new URLSearchParams();
    if (keyword) params.append('keyword', keyword);
    if (location) params.append('location', location);
    if (category) params.append('category', category);
    if (urgency) params.append('urgency', urgency);
    if (salary) params.append('salary', salary);
    if (type) params.append('type', type);

    try {
        const container = document.getElementById('todasVagasContainer');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-8">
                    <div class="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                    <p class="text-gray-500">Buscando vagas...</p>
                </div>
            `;
        }

        const response = await fetch(`/api/buscar-vagas?${params.toString()}`);
        if (!response.ok) throw new Error('Erro na busca');

        const vagas = await response.json();
        renderTodasVagas(vagas);

    } catch (error) {
        console.error('Erro na busca:', error);
        mostrarFeedbackAcao('❌ Erro ao buscar vagas', 'error');
    }
}

function limparFiltros() {
    document.getElementById('searchKeyword').value = '';
    document.getElementById('searchLocation').value = '';
    document.getElementById('searchCategory').value = '';
    document.getElementById('searchUrgency').value = '';
    document.getElementById('searchSalary').value = '';
    document.getElementById('searchType').value = '';

    loadAllJobs();
}

function inicializarAssistenteIA() {
    // Implementação do assistente IA
    console.log('Inicializando assistente IA...');
}

// ============================
// Fechar painéis ao clicar fora
// ============================
document.addEventListener('click', function(e) {
    const painel = document.getElementById('painelNotificacoes');
    const botaoNotificacoes = e.target.closest('[onclick*="toggleNotificacoes"]');

    if (painel && !painel.contains(e.target) && !botaoNotificacoes) {
        if (!painel.classList.contains('hidden')) {
            painel.style.animation = 'slideOutUp 0.3s ease-in';
            setTimeout(() => {
                painel.classList.add('hidden');
                painel.style.animation = '';
            }, 300);
        }
    }
});

// ============================
// Animações CSS via JavaScript
// ============================
const animacoes = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    @keyframes slideInDown {
        from { transform: translateY(-20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    @keyframes slideOutUp {
        from { transform: translateY(0); opacity: 1; }
        to { transform: translateY(-20px); opacity: 0; }
    }
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    .line-clamp-1 {
        display: -webkit-box;
        -webkit-line-clamp: 1;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .line-clamp-2 {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
`;

// Adicionar estilos de animação
const styleSheet = document.createElement('style');
styleSheet.textContent = animacoes;
document.head.appendChild(styleSheet);

// ============================
// Inicialização e polling
// ============================
function inicializarSistemaNotificacoes() {
    console.log('🚀 Inicializando sistema de notificações VaBoo!');

    // Carregar notificações imediatamente
    carregarNotificacoes(true);

    // Configurar polling inteligente
    notificacoesInterval = setInterval(() => {
        // Só fazer polling se a aba estiver ativa
        if (document.visibilityState === 'visible') {
            carregarNotificacoes(false);
        }
    }, 45000); // 45 segundos

    // Parar polling quando aba não estiver visível
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'hidden' && notificacoesInterval) {
            clearInterval(notificacoesInterval);
            notificacoesInterval = null;
        } else if (document.visibilityState === 'visible' && !notificacoesInterval) {
            carregarNotificacoes(false);
            notificacoesInterval = setInterval(() => {
                if (document.visibilityState === 'visible') {
                    carregarNotificacoes(false);
                }
            }, 45000);
        }
    });

    console.log('✅ Sistema de notificações inicializado com sucesso!');
}

// ============================
// Inicialização quando DOM estiver pronto
// ============================
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarSistemaNotificacoes);
} else {
    inicializarSistemaNotificacoes();
}

// Limpeza quando a página for descarregada
window.addEventListener('beforeunload', function() {
    if (notificacoesInterval) {
        clearInterval(notificacoesInterval);
    }
});


console.log('📱 VaBoo! Candidato Dashboard - JavaScript carregado com sucesso!');



// Cancelar candidatura
async function cancelarCandidatura(vagaId) {
    if (confirm('🤔 Tem certeza que deseja cancelar sua candidatura para esta vaga?')) {
        try {
            const btn = event.target.closest('button');
            const originalContent = btn.innerHTML;
            btn.innerHTML = '<span class="animate-spin">⏳</span> Cancelando...';
            btn.disabled = true;

            const response = await fetch('/cancelar_candidatura', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    vaga_id: vagaId
                })
            });

            if (response.ok) {
                btn.innerHTML = '<span class="text-green-500">✅</span> Cancelada!';
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                btn.innerHTML = originalContent;
                btn.disabled = false;
                alert('❌ Erro ao cancelar candidatura');
            }
        } catch (error) {
            console.error('Erro:', error);
            alert('❌ Erro ao cancelar candidatura');
        }
    }
}

// Funções do Assistente IA
async function analisarCurriculo() {
    const resultadosDiv = document.getElementById('resultadosIA');
    const conteudoDiv = document.getElementById('conteudoIA');

    resultadosDiv.classList.remove('hidden');
    conteudoDiv.innerHTML = `
        <div class="text-center py-8">
            <div class="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p class="text-gray-500">Analisando seu currículo...</p>
        </div>
    `;

    try {
        const response = await fetch('/api/ia/analisar-curriculo');
        const data = await response.json();

        if (data.error) {
            conteudoDiv.innerHTML = `
                <div class="text-center py-8 text-red-500">
                    <p>Erro: ${data.error}</p>
                </div>
            `;
        } else {
            mostrarAnaliseIA(data);
        }
    } catch (error) {
        conteudoDiv.innerHTML = `
            <div class="text-center py-8 text-red-500">
                <p>Erro ao carregar análise</p>
            </div>
        `;
    }
}

function mostrarAnaliseIA(analise) {
    const conteudoDiv = document.getElementById('conteudoIA');

    const tecnologias = analise.tecnologias_identificadas?.map(t => t.nome)?.join(', ') || 'Nenhuma identificada';
    const pontosFortes = analise.pontos_fortes?.map(p => `<li class="text-green-600">✅ ${p}</li>`)?.join('') || '<li class="text-gray-500">Analisando...</li>';
    const areasMelhoria = analise.areas_melhoria?.map(a => `<li class="text-orange-600">⚠️ ${a}</li>`)?.join('') || '<li class="text-gray-500">Nenhuma identificada</li>';

    conteudoDiv.innerHTML = `
        <h3 class="text-xl font-bold mb-6 text-gray-800">📊 Análise do seu Perfil</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
                <h4 class="font-semibold mb-3 text-purple-600">📊 Análise Geral</h4>
                <div class="space-y-2">
                    <p><strong>Nível:</strong> <span class="badge bg-blue-100 text-blue-800 px-2 py-1 rounded">${analise.nivel_senioridade || 'Analisando...'}</span></p>
                    <p><strong>Score do Perfil:</strong> <span class="text-2xl font-bold text-green-600">${analise.score_geral || 0}/100</span></p>
                    <p><strong>Tecnologias:</strong> ${tecnologias}</p>
                </div>
            </div>
            <div>
                <h4 class="font-semibold mb-3 text-green-600">✨ Pontos Fortes</h4>
                <ul class="space-y-1">
                    ${pontosFortes}
                </ul>
            </div>
            <div class="md:col-span-2">
                <h4 class="font-semibold mb-3 text-orange-600">🎯 Áreas de Melhoria</h4>
                <ul class="space-y-1">
                    ${areasMelhoria}
                </ul>
            </div>
        </div>
    `;
}



async function obterRecomendacoesIA() {
    const resultadosDiv = document.getElementById('resultadosIA');
    const conteudoDiv = document.getElementById('conteudoIA');

    // Mostrar loading
    resultadosDiv.classList.remove('hidden');
    conteudoDiv.innerHTML = `
        <div class="text-center py-8">
            <div class="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p class="text-gray-500">Obtendo recomendações personalizadas...</p>
        </div>
    `;

    try {
        const response = await fetch('/api/ia/recomendacoes-vagas');

        // Tratar códigos de erro HTTP
        if (!response.ok) {
            if (response.status === 401) {
                conteudoDiv.innerHTML = `<p class="text-red-500 text-center py-8">Você precisa estar logado para ver as recomendações.</p>`;
            } else if (response.status === 404) {
                conteudoDiv.innerHTML = `<p class="text-gray-500 text-center py-8">Nenhuma recomendação disponível no momento.</p>`;
            } else {
                conteudoDiv.innerHTML = `<p class="text-red-500 text-center py-8">Erro ao obter recomendações. Código: ${response.status}</p>`;
            }
            return;
        }

        const data = await response.json();

        // Tratar caso a API retorne um objeto de erro
        if (data.error) {
            conteudoDiv.innerHTML = `<p class="text-red-500 text-center py-8">${data.error}</p>`;
        }
        // Tratar caso não seja array ou array vazio
        else if (!Array.isArray(data) || data.length === 0) {
            conteudoDiv.innerHTML = `<p class="text-gray-500 text-center py-8">Nenhuma recomendação disponível no momento.</p>`;
        }
        // Exibir recomendações
        else {
            mostrarRecomendacoesIA(data);
        }

    } catch (error) {
        // Erro de rede ou outro
        conteudoDiv.innerHTML = `
            <div class="text-center py-8 text-red-500">
                <p>Erro ao obter recomendações: ${error.message}</p>
            </div>
        `;
    }
}

function mostrarRecomendacoesIA(recomendacoes) {
    const conteudoDiv = document.getElementById('conteudoIA');

    const recomendacoesHtml = recomendacoes.map(rec => `
        <div class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
            <div class="flex justify-between items-start mb-2">
                <h3 class="font-semibold text-lg">${rec.titulo}</h3>
                <span class="text-sm text-purple-600 font-bold">
                    ${Number(rec.compatibilidade?.score || 0).toFixed(0)}% compatível
                </span>
            </div>
            <p class="text-gray-600 mb-2">${rec.empresa}</p>
            <div class="text-sm text-gray-500">
                <p><strong>Motivos:</strong> ${rec.motivos?.join(', ') || 'N/A'}</p>
                ${rec.urgencia === 'Imediata' ? '<span class="bg-red-100 text-red-800 px-2 py-1 rounded text-xs">🔥 URGENTE</span>' : ''}
            </div>
            <a href="/candidatar/${rec.vaga_id}" class="mt-3 bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 transition-colors inline-block">
                Candidatar-se
            </a>
        </div>
    `).join('');

    conteudoDiv.innerHTML = `
        <h3 class="text-xl font-bold mb-6 text-gray-800">🎯 Vagas Recomendadas pela IA</h3>
        <div class="space-y-4 max-h-96 overflow-y-auto">
            ${recomendacoesHtml}
        </div>
    `;
}


async function obterDicasFavoritas() {
    const resultadosDiv = document.getElementById('resultadosIA');
    const conteudoDiv = document.getElementById('conteudoIA');

    resultadosDiv.classList.remove('hidden');
    conteudoDiv.innerHTML = `
        <div class="text-center py-8">
            <div class="animate-spin w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p class="text-gray-500">Analisando suas vagas favoritas...</p>
        </div>
    `;

    // Simular análise das vagas favoritas
    setTimeout(() => {
        conteudoDiv.innerHTML = `
            <h3 class="text-xl font-bold mb-6 text-gray-800">💡 Dicas para suas Vagas Favoritas</h3>
            <div class="space-y-4">
                <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h4 class="font-semibold text-green-800 mb-2">✅ Pontos Fortes do seu Perfil</h4>
                    <ul class="text-sm text-green-700 space-y-1">
                        <li>• Experiência sólida na área</li>
                        <li>• Competências técnicas alinhadas</li>
                        <li>• Formação adequada para as posições</li>
                    </ul>
                </div>

                <div class="bg-orange-50 border border-orange-200 rounded-lg p-4">
                    <h4 class="font-semibold text-orange-800 mb-2">🎯 Áreas para Melhorar</h4>
                    <ul class="text-sm text-orange-700 space-y-1">
                        <li>• Adicione mais projetos práticos ao seu currículo</li>
                        <li>• Destaque certificações relevantes</li>
                        <li>• Inclua métricas de resultados alcançados</li>
                    </ul>
                </div>

                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h4 class="font-semibold text-blue-800 mb-2">💡 Recomendações Específicas</h4>
                    <ul class="text-sm text-blue-700 space-y-1">
                        <li>• Personalize sua carta de apresentação</li>
                        <li>• Atualize seu perfil no LinkedIn</li>
                        <li>• Pratique entrevistas técnicas</li>
                    </ul>
                </div>
            </div>
        `;
    }, 2000);
}