
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
function inicializarAssistenteIA() {
    const conteudoDiv = document.getElementById('conteudoIA');
    conteudoDiv.innerHTML = `
        <div class="text-center py-8">
            <h3 class="text-xl font-bold mb-4 text-gray-800">🤖 Assistente de IA para Candidatos</h3>
            <p class="text-gray-600 mb-6">Utilize as ferramentas abaixo para melhorar seu perfil e encontrar vagas ideais.</p>
            <div class="space-y-4 max-w-md mx-auto">
                <button onclick="analisarCurriculo()" class="w-full bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 transition-colors">
                    📄 Analisar meu Currículo
                </button>
                <button onclick="obterRecomendacoesIA()" class="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors">       
                    🎯 Obter Vagas Recomendadas
                </button>
                <button onclick="obterDicasFavoritas()" class="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors">
                    💡 Dicas para Minhas Vagas Favoritas
                </button>
            </div>
        </div>
    `;
    document.getElementById('resultadosIA').classList.add('hidden');
}

// Função para fechar o modal de dicas
function fecharModalDicas() {
    const modal = document.getElementById('modalDicas');
    if (modal) {
        modal.classList.add('hidden');
    }
}

// Função para salvar as dicas (simulação)
function salvarDicas() {
    alert('Dicas salvas com sucesso!');
    fecharModalDicas();
}

// Função para obter o ícone baseado na categoria da dica
function getIconeDica(categoria) {
    const icones = {
        'perfil': '👤',
        'curriculo': '📄',
        'habilidades': '🛠️',
        'entrevista': '🎤',
        'outros': '💡'
    };
    return icones[categoria] || '💡';
}       
