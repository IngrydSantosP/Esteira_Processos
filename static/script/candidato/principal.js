// ============================
// Estado Global
// ============================
let notificacoesCache = [];
let ultimaAtualizacao = null;

// ============================
// Gerenciamento de Seções
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

    // Resetar botões
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('filter-active');
        btn.classList.add('bg-gray-100', 'text-gray-700');
        btn.style.background = '';
        btn.style.color = '';
        btn.style.transform = '';
        btn.style.boxShadow = '';
    });

    // Destacar botão ativo
    if (event && event.target) {
        const activeBtn = event.target;
        activeBtn.classList.add('filter-active');
        activeBtn.classList.remove('bg-gray-100', 'text-gray-700');
        activeBtn.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        activeBtn.style.color = 'white';
        activeBtn.style.transform = 'translateY(-2px)';
        activeBtn.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
    }

    // Carregar conteúdo
    if (sectionName === 'todas') {
        loadAllJobs();
        loadSearchFilters();
    } else if (sectionName === 'principais') {
        loadMainJobs(); // sempre recarregar
    } else if (sectionName === 'assistente-ia') {
        inicializarAssistenteIA();
    } else if (sectionName === 'favoritos') {
        loadFavoriteJobs();
    }
}

// ============================
// Sistema de Vagas
// ============================
async function loadAllJobs() {
    const container = document.getElementById('todasVagasContainer');
    try {
        const response = await fetch('/api/todas-vagas');
        const vagas = await response.json();
        if (vagas.length === 0) {
            container.innerHTML = `<p>🔍 Nenhuma vaga disponível</p>`;
            return;
        }
        renderVagas(vagas, container);
    } catch (error) {
        console.error('Erro ao carregar vagas:', error);
        container.innerHTML = `<p>❌ Erro ao carregar vagas</p>`;
    }
}

async function loadMainJobs() {
    const container = document.getElementById('principaisVagasContainer');
    try {
        const response = await fetch('/api/principais-vagas');
        const vagas = await response.json();
        if (vagas.length === 0) {
            container.innerHTML = `<p>😔 Nenhuma vaga em destaque</p>`;
            return;
        }
        renderVagas(vagas, container);
    } catch (error) {
        console.error('Erro ao carregar principais vagas:', error);
        container.innerHTML = `<p>❌ Erro ao carregar principais vagas</p>`;
    }
}

function renderVagas(vagas, container, titulo = null) {
    let html = '';
    if (titulo) {
        html += `<h3 class="text-xl font-bold mb-4">${titulo}</h3>`;
    }
    html += '<div class="grid gap-6">';
    vagas.forEach(vaga => {
        html += `
            <div class="bg-white rounded-2xl p-6 shadow-sm border hover:shadow-lg transition">
                <h3 class="text-lg font-bold mb-2">${vaga.titulo}</h3>
                <p class="text-sm text-gray-600">${vaga.empresa_nome || ''}</p>
                <p class="text-sm text-green-600 font-semibold">💰 ${vaga.salario_oferecido ? 'R$ ' + vaga.salario_oferecido.toLocaleString('pt-BR') : '-'}</p>
                <p class="text-sm text-gray-600 line-clamp-2 mb-3">${vaga.descricao || ''}</p>
                <div class="flex gap-3">
                    <button onclick="toggleFavorite(${vaga.id}, this)" 
                            data-favorited="${vaga.is_favorita}" 
                            class="favorite-btn text-xl ${vaga.is_favorita ? 'text-red-500' : 'text-gray-300'}">
                        ${vaga.is_favorita ? '❤️' : '🤍'}
                    </button>
                    <a href="/vaga/${vaga.id}" class="text-blue-600 hover:underline">👁️ Ver Detalhes</a>
                </div>
            </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

// ============================
// Sistema de Favoritos
// ============================
async function toggleFavorite(vagaId, buttonElement) {
    try {
        const response = await fetch('/api/favoritar-vaga', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ vaga_id: vagaId })
        });
        const data = await response.json();
        if (data.success) {
            buttonElement.innerHTML = data.favorited ? '❤️' : '🤍';
            buttonElement.setAttribute('data-favorited', data.favorited);
            buttonElement.classList.toggle('text-red-500', data.favorited);
            buttonElement.classList.toggle('text-gray-300', !data.favorited);
            // Atualizar seção favoritos se visível
            if (document.getElementById('favoritosVagasContainer')) {
                loadFavoriteJobs();
            }
        }
    } catch (error) {
        console.error('Erro ao atualizar favoritos:', error);
    }
}

async function loadFavoriteJobs() {
    const container = document.getElementById('favoritosVagasContainer');
    try {
        const response = await fetch('/api/favoritos-vagas');
        const vagas = await response.json();
        if (vagas.length === 0) {
            container.innerHTML = `<p>🤍 Nenhuma vaga favoritada ainda</p>`;
            return;
        }
        renderVagas(vagas, container, "Vagas Favoritas");
    } catch (error) {
        console.error('Erro ao carregar favoritos:', error);
    }
}

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

function carregarNotificacoes() {
    fetch('/api/notificacoes')
        .then(r => r.json())
        .then(data => {
            notificacoesCache = data.notificacoes || [];
            atualizarNotificacoes();
        })
        .catch(err => console.error('Erro ao carregar notificações:', err));
}

function atualizarNotificacoes() {
    const lista = document.getElementById('listaNotificacoes');
    if (!lista) return;

    if (notificacoesCache.length === 0) {
        lista.innerHTML = `<p class="text-gray-500">Nenhuma notificação encontrada</p>`;
        return;
    }

    lista.innerHTML = notificacoesCache.map(n => `
        <div class="p-4 border-b hover:bg-gray-50">
            <h4 class="font-semibold">${n.titulo || 'Notificação'}</h4>
            <p class="text-sm text-gray-600">${n.mensagem}</p>
        </div>
    `).join('');
}

// ============================
// Inicialização
// ============================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Dashboard iniciado');
    showSection('todas');
});
