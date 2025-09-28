// ============================
// Sistema de Notificações (Modal)
// ============================
function toggleNotificacoes() {
    if (document.getElementById('modalNotificacoes')) {
        fecharModalNotificacoes();
        return;
    }

    const modal = document.createElement('div');
    modal.id = 'modalNotificacoes';
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
    modal.innerHTML = `
        <div class="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto shadow-2xl">
            <div class="p-6 flex justify-between items-center border-b">
                <h3 class="text-xl font-bold">🔔 Notificações</h3>
                <button onclick="fecharModalNotificacoes()">✕</button>
            </div>
            <div class="p-6" id="listaNotificacoes"></div>
        </div>`;
    document.body.appendChild(modal);

    carregarNotificacoes();
}

function fecharModalNotificacoes() {
    const modal = document.getElementById('modalNotificacoes');
    if (modal) modal.remove();
}

function atualizarNotificacoes() {
    const lista = document.getElementById('listaNotificacoes');
    if (!lista) return;
    lista.innerHTML = notificacoesCache.map(n => `
        <div class="p-4 border-b">
            <p><strong>${n.titulo || 'Notificação'}</strong></p>
            <p>${n.mensagem}</p>
        </div>`).join('');
}






// ============================
// Sistema avançado de notificações
// ============================

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