let vagaAtualId = null;
let candidatoSelecionado = null;

// Bloquear/desbloquear rolagem do fundo
function bloquearFundo() {
    document.body.classList.add('overflow-hidden');
}
function desbloquearFundo() {
    document.body.classList.remove('overflow-hidden');
}

async function abrirModalEncerramento(vagaId, vagaTitulo) {
    vagaAtualId = vagaId;
    candidatoSelecionado = null;

    document.getElementById('vagaTitulo').textContent = vagaTitulo;
    document.getElementById('mensagemPersonalizada').value = '';
    document.getElementById('contadorCaracteres').textContent = '0';

    try {
        const response = await fetch(`/candidaturas/api/json/candidatos_vaga/${vagaId}`);
        const candidatos = await response.json();

        const secaoCandidatos = document.getElementById('secaoCandidatos');
        const listaCandidatos = document.getElementById('listaCandidatos');
        const btnContratar = document.getElementById('btnContratar');

        if (candidatos.length > 0) {
            secaoCandidatos.classList.remove('hidden');
            listaCandidatos.innerHTML = '';

            candidatos.forEach(candidato => {
                const item = document.createElement('div');
                item.className = 'p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0 candidate-item';
                item.innerHTML = `
                    <div class="flex justify-between items-center">
                        <div>
                            <p class="font-medium text-gray-800">${candidato.nome}</p>
                            <p class="text-sm text-gray-600">Score: ${candidato.score.toFixed(1)}%</p>
                        </div>
                        <input type="radio" name="candidatoSelecionado" value="${candidato.id}" 
                               class="w-4 h-4 text-purple-600 focus:ring-purple-500">
                    </div>
                `;

                item.addEventListener('click', () => {
                    const radio = item.querySelector('input[type="radio"]');
                    radio.checked = true;
                    candidatoSelecionado = candidato.id;

                    document.querySelectorAll('.candidate-item').forEach(el => {
                        el.classList.remove('bg-purple-50', 'border-purple-200');
                    });

                    item.classList.add('bg-purple-50', 'border-purple-200');
                    btnContratar.classList.remove('hidden');
                });

                listaCandidatos.appendChild(item);
            });
        } else {
            secaoCandidatos.classList.add('hidden');
            btnContratar.classList.add('hidden');
        }
    } catch (error) {
        console.error('Erro ao carregar candidatos:', error);
        document.getElementById('vagaTitulo').textContent = 'Erro ao carregar';
    }

    document.getElementById('modalEncerramento').classList.remove('hidden');
    bloquearFundo();
}

document.getElementById('mensagemPersonalizada').addEventListener('input', function () {
    const contador = document.getElementById('contadorCaracteres');
    contador.textContent = this.value.length;
});

async function encerrarVagaModal(acao) {
    if (!vagaAtualId) return;

    if (acao === 'contratar' && !candidatoSelecionado) {
        showToast('Por favor, selecione um candidato para contratar.', 'error');
        return;
    }

    let confirmMessage = '';
    switch(acao) {
        case 'excluir':
            confirmMessage = 'Tem certeza que deseja excluir esta vaga? Esta ação não pode ser desfeita.';
            break;
        case 'congelar':
            confirmMessage = 'Tem certeza que deseja congelar esta vaga? Ela ficará inativa temporariamente.';
            break;
        case 'contratar':
            confirmMessage = 'Confirma a contratação do candidato selecionado? A vaga será marcada como concluída.';
            break;
    }

    if (confirmMessage && !confirm(confirmMessage)) {
        return;
    }

    const mensagem = document.getElementById('mensagemPersonalizada').value.trim();

    try {
        const response = await fetch('/encerrar_vaga', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vaga_id: vagaAtualId,
                acao: acao,
                candidato_id: candidatoSelecionado,
                mensagem_personalizada: mensagem
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
            showToast(result.message || 'Operação realizada com sucesso!', 'success');
            fecharModalEncerramento();
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast('Erro: ' + (result.error || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('Erro ao encerrar vaga:', error);
        showToast('Erro ao processar solicitação. Tente novamente.', 'error');
    }
}

function fecharModalEncerramento() {
    document.getElementById('modalEncerramento').classList.add('hidden');
    vagaAtualId = null;
    candidatoSelecionado = null;
    desbloquearFundo();
}

// Fechar modal ao clicar fora
document.getElementById('modalEncerramento').addEventListener('click', function (e) {
    if (e.target === this) {
        fecharModalEncerramento();
    }
});

// Toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 z-50 px-6 py-4 rounded-xl shadow-lg transform translate-y-full transition-all duration-300 ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        'bg-blue-500 text-white'
    }`;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('translate-y-full');
    }, 100);

    setTimeout(() => {
        toast.classList.add('translate-y-full');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}