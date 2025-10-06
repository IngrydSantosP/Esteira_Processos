// ===== VARIÁVEIS GLOBAIS =====
let candidatosOriginais = [];
let candidatosFiltrados = [];
let mostrarSoFavoritos = false;
let currentStep = 1;
const totalSteps = 3;
const link = document.createElement('link');
link.rel = 'stylesheet';
link.href = '/static/style/candidatos_geral.css'; // Caminho do CSS
document.head.appendChild(link);

document.addEventListener('DOMContentLoaded', () => {

    // Navegação entre seções

    window.proximaSecao = () => { if(currentStep<totalSteps) mostrarSecao(currentStep+1); }
    window.secaoAnterior = () => { if(currentStep>1) mostrarSecao(currentStep-1); }

    mostrarSecao(1);

    // Pesos do Score
    const pesos = {
        salarial: 20,
        requisitos: 40,
        experiencia: 15,
        diferenciais: 10,
        localizacao: 10,
        formacao: 5
    };

    window.atualizarPeso = (tipo, valor) => {
        pesos[tipo] = parseInt(valor);
        document.getElementById(`valor_${tipo}`).textContent = valor;
        atualizarBarraTotal();
    }

    function atualizarBarraTotal() {
        const total = Object.values(pesos).reduce((a,b)=>a+b,0);
        document.getElementById('total-peso').textContent = total;
        const status = document.getElementById('status-peso');
        const barra = document.getElementById('barra-progresso');
        if(total===100){
            status.textContent = '✅ Válido (100%)';
            status.className = 'text-sm font-bold text-green-600';
        } else {
            status.textContent = '⚠️ Total inválido';
            status.className = 'text-sm font-bold text-red-500';
        }
        barra.style.width = Math.min(total,100)+'%';
    }

    window.resetarPesos = () => {
        Object.keys(pesos).forEach(key=>{
            const defaultValue = {
                salarial:20, requisitos:40, experiencia:15, diferenciais:10, localizacao:10, formacao:5
            }[key];
            pesos[key] = defaultValue;
            document.getElementById(`peso_${key}`).value = defaultValue;
            document.getElementById(`valor_${key}`).textContent = defaultValue;
        });
        atualizarBarraTotal();
    }

    atualizarBarraTotal();

    // Template Score
    window.aplicarTemplateScore = () => {
        const template = document.getElementById('template_score').value;
        const templates = {
            equilibrado: {salarial:20,requisitos:40,experiencia:15,diferenciais:10,localizacao:10,formacao:5},
            tecnico: {salarial:10,requisitos:50,experiencia:20,diferenciais:10,localizacao:5,formacao:5},
            startup: {salarial:15,requisitos:35,experiencia:15,diferenciais:15,localizacao:10,formacao:10},
            tradicional: {salarial:25,requisitos:30,experiencia:20,diferenciais:5,localizacao:10,formacao:10},
            remoto: {salarial:15,requisitos:30,experiencia:15,diferenciais:10,localizacao:20,formacao:10},
            vendas: {salarial:25,requisitos:20,experiencia:20,diferenciais:10,localizacao:15,formacao:10},
            gestao: {salarial:20,requisitos:25,experiencia:30,diferenciais:10,localizacao:10,formacao:5}
        };
        if(templates[template]){
            Object.keys(templates[template]).forEach(key=>{
                pesos[key] = templates[template][key];
                document.getElementById(`peso_${key}`).value = pesos[key];
                document.getElementById(`valor_${key}`).textContent = pesos[key];
            });
            atualizarBarraTotal();
        }
    }

}); // <-- FECHAMENTO DO DOMContentLoaded

function mostrarSecao(step) {
    if (step < 1 || step > totalSteps) return;
    for (let i = 1; i <= totalSteps; i++) {
        const s = document.getElementById(`secao-${i}`);
        if (s) s.style.display = (i === step ? 'block' : 'none');
        const stepIndicator = document.getElementById(`step-${i}`);
        if (stepIndicator) stepIndicator.classList.toggle('bg-green-500', i === step);
    }
    document.getElementById('btnAnterior').style.display = (step > 1 ? 'inline-flex' : 'none');
    document.getElementById('btnProximo').style.display = (step < totalSteps ? 'inline-flex' : 'none');
    document.getElementById('actionButtons').style.display = (step === totalSteps ? 'flex' : 'none');

    if (typeof atualizarProgresso === "function") atualizarProgresso(step);
    if (typeof atualizarNavegacao === "function") atualizarNavegacao(step);
    currentStep = step;
    window.scrollTo({top: 200, behavior: 'smooth'});
}


function toggleEnderecoField() {
    const tipo = document.getElementById('tipo_vaga').value;
    const container = document.getElementById('endereco_container');
    const camposEndereco = document.querySelectorAll('#campos_endereco_vaga input, #campos_endereco_vaga select');

    if (tipo === 'Presencial' || tipo === 'Híbrida') {
        container.classList.remove('hidden');
        camposEndereco.forEach(campo => { campo.required = true; });
    } else {
        container.classList.add('hidden');
        camposEndereco.forEach(campo => { campo.required = false; campo.value = ''; });
    }
}


function toggleNovaCategoria() {
    const categoriaSelect = document.getElementById('categoria_id');
    const novaContainer = document.getElementById('nova_categoria_container');
    const novaInput = document.getElementById('nova_categoria');

    if (categoriaSelect.value === 'nova') {
        novaContainer.classList.remove('hidden');
        if (novaInput) {
            novaInput.required = true;
            novaInput.focus();
        }
    } else {
        novaContainer.classList.add('hidden');
        if (novaInput) {
            novaInput.required = false;
            novaInput.value = '';
        }
    }
}


function toggleEnderecoEmpresa() {
    const usar = document.getElementById('usar_endereco_empresa').checked;
    const camposEndereco = document.getElementById('campos_endereco_vaga');

    if (usar) {
        fetch('/empresa/endereco')
        .then(response => response.json())
        .then(data => {
            if (data.endereco) {
                document.getElementById('localizacao_endereco').value = data.endereco || '';
                document.getElementById('localizacao_cidade').value = data.cidade || '';
                document.getElementById('localizacao_estado').value = data.estado || '';
            }
        })
        .catch(error => console.error('Erro ao buscar endereço:', error));

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

document.addEventListener('DOMContentLoaded', function() {
    candidatosOriginais = Array.from(document.querySelectorAll('.candidato-card')).map(card => {
        return {
            element: card,
            nome: card.dataset.nome,
            score: parseFloat(card.dataset.score),
            posicao: parseInt(card.dataset.posicao),
            candidatoId: card.dataset.candidatoId,
            favorited: card.dataset.favorited === 'true'
        };
    });
    candidatosFiltrados = [...candidatosOriginais];
    loadFavoriteStatus();
    mostrarSecao(1);
});
