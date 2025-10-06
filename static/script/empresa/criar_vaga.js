// Variáveis globais
let currentStep = 1;
const totalSteps = 3;

// Campos obrigatórios ocultos com valores padrão
const camposOcultos = {
    'turno_trabalho': 'Comercial',
    'idiomas_exigidos': '',
    'disponibilidade_viagens': false,
    'data_limite_candidatura': null,
    'data_congelamento_agendado': null
};

// ---------------------- FUNÇÕES ----------------------

// Navegação entre seções
function mostrarSecao(step) {
    if (step < 1 || step > totalSteps) return;

    for (let i = 1; i <= totalSteps; i++) {
        const secao = document.getElementById(`secao-${i}`);
        if (secao) secao.style.display = i === step ? 'block' : 'none';
    }

    atualizarProgresso(step);
    atualizarNavegacao(step);
    currentStep = step;

    window.scrollTo({top: 200, behavior: 'smooth'});
}

function atualizarProgresso(activeStep) {
    for (let i = 1; i <= totalSteps; i++) {
        const stepEl = document.getElementById(`step-${i}`);
        if (!stepEl) continue;

        const circle = stepEl.querySelector('div');
        const label = stepEl.querySelector('span');

        if (i <= activeStep) {
            const colors = [
                'from-green-500 to-emerald-500 text-green-600',
                'from-blue-500 to-blue-600 text-blue-600',
                'from-purple-500 to-indigo-600 text-purple-600'
            ];
            circle.className = `w-10 h-10 bg-gradient-to-r ${colors[i-1].split(' ')[0]} text-white rounded-full flex items-center justify-center font-bold text-sm shadow-lg`;
            label.className = `ml-3 text-sm font-medium ${colors[i-1].split(' ')[2]}`;
        } else {
            circle.className = 'w-10 h-10 bg-gray-300 text-gray-500 rounded-full flex items-center justify-center font-bold text-sm';
            label.className = 'ml-3 text-sm font-medium text-gray-500';
        }
    }
}

function atualizarNavegacao(step) {
    const btnAnterior = document.getElementById('btnAnterior');
    const btnProximo = document.getElementById('btnProximo');
    const actionButtons = document.getElementById('actionButtons');

    if (btnAnterior) btnAnterior.style.display = step > 1 ? 'flex' : 'none';
    if (btnProximo && actionButtons) {
        if (step < totalSteps) {
            btnProximo.style.display = 'flex';
            actionButtons.style.display = 'none';
        } else {
            btnProximo.style.display = 'none';
            actionButtons.style.display = 'flex';
        }
    }
}

function proximaSecao() {
    if (currentStep < totalSteps && validarSecaoAtual()) {
        mostrarSecao(currentStep + 1);
    }
}

function secaoAnterior() {
    if (currentStep > 1) {
        mostrarSecao(currentStep - 1);
    }
}

// Validação das seções
function validarSecaoAtual() {
    const secaoAtual = document.getElementById(`secao-${currentStep}`);
    if (!secaoAtual) return true;

    const camposObrigatorios = secaoAtual.querySelectorAll('input[required], select[required], textarea[required]');

    for (let campo of camposObrigatorios) {
        if (!campo.value.trim()) {
            campo.focus();
            campo.classList.add('border-red-500');
            setTimeout(() => campo.classList.remove('border-red-500'), 3000);
            showToast('Por favor, preencha todos os campos obrigatórios.', 'error');
            return false;
        }
    }

    // Validação de endereço
    if (currentStep === 1) {
        const tipoVaga = document.getElementById('tipo_vaga').value;
        if (tipoVaga === 'Presencial' || tipoVaga === 'Híbrida') {
            const endereco = document.getElementById('localizacao_endereco').value;
            const cidade = document.getElementById('localizacao_cidade').value;
            const estado = document.getElementById('localizacao_estado').value;

            if (!endereco || !cidade || !estado) {
                showToast('Endereço é obrigatório para vagas presenciais/híbridas.', 'error');
                return false;
            }
        }
    }

    // Validação de pesos
    if (currentStep === 3) {
        const total = parseInt(document.getElementById('total-peso').textContent);
        if (total !== 100) {
            showToast('Os pesos devem somar exatamente 100%.', 'error');
            return false;
        }
    }

    return true;
}

// Toast
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const bgColor = type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-500' : 'bg-blue-500';

    toast.className = `fixed bottom-4 right-4 z-50 px-6 py-4 rounded-xl shadow-lg text-white ${bgColor} transform translate-y-full transition-all duration-300`;
    toast.textContent = message;

    document.body.appendChild(toast);
    setTimeout(() => toast.classList.remove('translate-y-full'), 100);

    setTimeout(() => {
        toast.classList.add('translate-y-full');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Toggle endereço
function toggleEnderecoField() {
    const tipoVaga = document.getElementById('tipo_vaga')?.value;
    const enderecoContainer = document.getElementById('endereco_container');
    const camposEndereco = document.querySelectorAll('#campos_endereco_vaga input, #campos_endereco_vaga select');

    if (!tipoVaga || !enderecoContainer) return;

    if (tipoVaga === 'Presencial' || tipoVaga === 'Híbrida') {
        enderecoContainer.classList.remove('hidden');
        camposEndereco.forEach(c => c.required = true);
    } else {
        enderecoContainer.classList.add('hidden');
        camposEndereco.forEach(c => { c.required = false; c.value = ''; });
    }
}

// Toggle nova categoria
function toggleNovaCategoria() {
    const categoriaSelect = document.getElementById('categoria_id');
    const novaContainer = document.getElementById('nova_categoria_container');
    const novaInput = document.getElementById('nova_categoria');

    if (!categoriaSelect || !novaContainer || !novaInput) return;

    if (categoriaSelect.value === 'nova') {
        novaContainer.classList.remove('hidden');
        novaInput.required = true;
        novaInput.focus();
    } else {
        novaContainer.classList.add('hidden');
        novaInput.required = false;
        novaInput.value = '';
    }
}

// Toggle endereço da empresa
function toggleEnderecoEmpresa() {
    const checkbox = document.getElementById('usar_endereco_empresa');
    const camposEndereco = document.getElementById('campos_endereco_vaga');

    if (!checkbox || !camposEndereco) return;

    if (checkbox.checked) {
        fetch('/empresa/endereco')
            .then(res => res.json())
            .then(data => {
                document.getElementById('localizacao_endereco').value = data.endereco || '';
                document.getElementById('localizacao_cidade').value = data.cidade || '';
                document.getElementById('localizacao_estado').value = data.estado || '';
            })
            .catch(console.error);

        camposEndereco.style.opacity = '0.6';
        camposEndereco.style.pointerEvents = 'none';
    } else {
        camposEndereco.style.opacity = '1';
        camposEndereco.style.pointerEvents = 'auto';
        document.getElementById('localizacao_endereco').value = '';
        document.getElementById('localizacao_cidade').value = '';
        document.getElementById('localizacao_estado').value = '';
    }
}

// Score
function atualizarPeso(tipo, valor) {
    document.getElementById(`valor_${tipo}`).textContent = valor;
    calcularTotalPesos();
}

function calcularTotalPesos() {
    const pesos = ['salarial', 'requisitos', 'experiencia', 'diferenciais', 'localizacao', 'formacao'];
    let total = 0;
    pesos.forEach(p => total += parseInt(document.getElementById(`peso_${p}`).value));
    document.getElementById('total-peso').textContent = total;

    const statusPeso = document.getElementById('status-peso');
    const barraProgresso = document.getElementById('barra-progresso');

    if (!statusPeso || !barraProgresso) return;

    if (total === 100) {
        statusPeso.textContent = '✅ Válido (100%)';
        statusPeso.className = 'text-sm font-bold text-green-600';
        barraProgresso.style.width = '100%';
        barraProgresso.className = 'bg-gradient-to-r from-green-500 to-emerald-500 h-3 rounded-full transition-all duration-300';
    } else if (total < 100) {
        statusPeso.textContent = `⚠️ Incompleto (${total}%)`;
        statusPeso.className = 'text-sm font-bold text-yellow-600';
        barraProgresso.style.width = `${total}%`;
        barraProgresso.className = 'bg-gradient-to-r from-yellow-500 to-orange-500 h-3 rounded-full transition-all duration-300';
    } else {
        statusPeso.textContent = `❌ Excesso (${total}%)`;
        statusPeso.className = 'text-sm font-bold text-red-600';
        barraProgresso.style.width = '100%';
        barraProgresso.className = 'bg-gradient-to-r from-red-500 to-red-600 h-3 rounded-full transition-all duration-300';
    }
}

// Template score
function aplicarTemplateScore() {
    const template = document.getElementById('template_score')?.value;
    const templates = {
        'equilibrado': {salarial: 20, requisitos: 40, experiencia: 15, diferenciais: 10, localizacao: 10, formacao: 5},
        'tecnico': {salarial: 10, requisitos: 50, experiencia: 25, diferenciais: 10, localizacao: 5, formacao: 0},
        'startup': {salarial: 30, requisitos: 30, experiencia: 10, diferenciais: 20, localizacao: 10, formacao: 0},
        'tradicional': {salarial: 15, requisitos: 35, experiencia: 20, diferenciais: 5, localizacao: 15, formacao: 10},
        'remoto': {salarial: 25, requisitos: 45, experiencia: 20, diferenciais: 10, localizacao: 0, formacao: 0},
        'vendas': {salarial: 25, requisitos: 25, experiencia: 20, diferenciais: 20, localizacao: 10, formacao: 0},
        'gestao': {salarial: 15, requisitos: 30, experiencia: 30, diferenciais: 15, localizacao: 5, formacao: 5}
    };

    const valores = templates[template];
    if (!valores) return;

    for (let key in valores) {
        document.getElementById(`peso_${key}`).value = valores[key];
        document.getElementById(`valor_${key}`).textContent = valores[key];
    }

    calcularTotalPesos();
}

function resetarPesos() {
    const pesos = ['salarial', 'requisitos', 'experiencia', 'diferenciais', 'localizacao', 'formacao'];
    pesos.forEach(p => {
        document.getElementById(`peso_${p}`).value = 0;
        document.getElementById(`valor_${p}`).textContent = 0;
    });
    calcularTotalPesos();
}

// ---------------------- INICIALIZAÇÃO ----------------------
document.addEventListener('DOMContentLoaded', () => {
    toggleEnderecoField();
    toggleNovaCategoria();
    calcularTotalPesos();
    mostrarSecao(currentStep);

    const form = document.querySelector('form');
    if (!form) return;

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        // Adiciona campos ocultos
        Object.keys(camposOcultos).forEach(campo => {
            if (!this.querySelector(`[name="${campo}"]`)) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = campo;
                input.value = camposOcultos[campo];
                this.appendChild(input);
            }
        });

        if (!validarSecaoAtual()) return;

        const formData = new FormData(this);

        fetch(this.action || window.location.href, {
            method: this.method || 'POST',
            body: formData
        })
        .then(res => {
            if (res.ok) window.location.href = '/dashboard_empresa'; // 🔥 corrigido
            else showToast('Erro ao criar vaga. Tente novamente.', 'error');
        })
        .catch(err => {
            console.error(err);
            showToast('Erro de rede. Tente novamente.', 'error');
        });
    });
});

// Tornar funções globais para botões
window.proximaSecao = proximaSecao;
window.secaoAnterior = secaoAnterior;
window.mostrarSecao = mostrarSecao;
window.toggleEnderecoField = toggleEnderecoField;
window.toggleNovaCategoria = toggleNovaCategoria;
window.toggleEnderecoEmpresa = toggleEnderecoEmpresa;
window.atualizarPeso = atualizarPeso;
window.aplicarTemplateScore = aplicarTemplateScore;
window.resetarPesos = resetarPesos;
