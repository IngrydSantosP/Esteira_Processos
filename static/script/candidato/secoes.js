// ============================
// Gerenciamento de Seções do Dashboard
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

    // Carregar conteúdo específico
    if (sectionName === 'todas') {
        loadAllJobs();
        loadSearchFilters();
    } else if (sectionName === 'principais') {
        loadMainJobs(); // sempre recarregar
    } else if (sectionName === 'assistente-ia') {
        inicializarAssistenteIA();
    }
}






// ============================
// Navegação entre seções
// ============================


function showSection(sectionId) {
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(sec => sec.classList.add('hidden'));

    const activeSection = document.getElementById(`section-${sectionId}`);
    if (activeSection) activeSection.classList.remove('hidden');

    // Atualizar botões ativos
    const buttons = document.querySelectorAll('.filter-btn');
    buttons.forEach(btn => btn.classList.remove('filter-active'));

    const clickedBtn = Array.from(buttons).find(btn => btn.getAttribute('onclick')?.includes(sectionId));
    if (clickedBtn) clickedBtn.classList.add('filter-active');
}