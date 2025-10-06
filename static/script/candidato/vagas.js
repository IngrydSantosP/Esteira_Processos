// ============================
// Sistema de Vagas
// ============================

async function loadAllJobs() {
    const container = document.getElementById('todasVagasContainer');

    try {
        const response = await fetch('/api/todas-vagas');
        const vagas = await response.json();
        if (vagas.length === 0) {
            container.innerHTML = '<p>Nenhuma vaga disponível</p>';
            return;
        }
        renderVagas(vagas, container);
    } catch (error) {
        console.error('Erro ao carregar vagas:', error);
        container.innerHTML = '<p>Erro ao carregar vagas</p>';
    }
}

async function loadMainJobs() {
    const container = document.getElementById('principaisVagasContainer');
    try {
        const response = await fetch('/api/principais-vagas');
        const vagas = await response.json();
        if (vagas.length === 0) {
            container.innerHTML = '<p>Nenhuma vaga em destaque</p>';
            return;
        }
        renderVagas(vagas, container);
    } catch (error) {
        console.error('Erro ao carregar principais vagas:', error);
        container.innerHTML = '<p>Erro ao carregar principais vagas</p>';
    }
}

function renderVagas(vagas, container) {
    let html = '<div class="grid gap-6">';
    vagas.forEach(vaga => {
        html += `
            <div class="bg-white rounded-2xl p-6 shadow-sm">
                <h3>${vaga.titulo}</h3>
                <button onclick="toggleFavorite(${vaga.id}, this)" 
                        data-favorited="${vaga.is_favorita}">
                    ${vaga.is_favorita ? '❤️' : '🤍'}
                </button>
            </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}
