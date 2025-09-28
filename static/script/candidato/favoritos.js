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
