// ---------- Validação de senha ----------
export function aplicarValidacaoSenha(formSelector, senhaId = 'senha', confirmarId = 'confirmar_senha') {
    const form = document.querySelector(formSelector);
    const senhaInput = document.getElementById(senhaId);
    const confirmarSenhaInput = document.getElementById(confirmarId);

    if (!form || !senhaInput || !confirmarSenhaInput) return;

    // Mensagem de força da senha
    const senhaMsg = document.createElement('small');
    senhaMsg.className = 'text-xs mt-1 block';
    senhaInput.insertAdjacentElement('afterend', senhaMsg);

    // Mensagem de verificação de senha
    const confirmarMsg = document.createElement('small');
    confirmarMsg.className = 'text-xs mt-1 block';
    confirmarSenhaInput.insertAdjacentElement('afterend', confirmarMsg);

    // Força da senha
    senhaInput.addEventListener('input', () => {
        const senha = senhaInput.value;
        let forca = 0;

        if (senha.length >= 8) forca++;
        if (/[A-Z]/.test(senha)) forca++;
        if (/[0-9]/.test(senha)) forca++;
        if (/[^A-Za-z0-9]/.test(senha)) forca++;

        if (!senha) {
            senhaMsg.textContent = '';
        } else if (forca <= 1) {
            senhaMsg.textContent = 'Senha fraca: use pelo menos 8 caracteres, números e letras maiúsculas.';
            senhaMsg.style.color = 'red';
        } else if (forca === 2) {
            senhaMsg.textContent = 'Senha média: adicione símbolos para fortalecer.';
            senhaMsg.style.color = 'orange';
        } else {
            senhaMsg.textContent = 'Senha forte.';
            senhaMsg.style.color = 'green';
        }
    });

    // Verificação de igualdade
    confirmarSenhaInput.addEventListener('input', () => {
        const senha = senhaInput.value;
        const confirmar = confirmarSenhaInput.value;

        if (!confirmar) {
            confirmarMsg.textContent = '';
        } else if (senha !== confirmar) {
            confirmarMsg.textContent = '❌ As senhas não coincidem.';
            confirmarMsg.style.color = 'red';
        } else {
            confirmarMsg.textContent = '✅ As senhas coincidem.';
            confirmarMsg.style.color = 'green';
        }
    });

    // Validação no envio
    form.addEventListener('submit', (e) => {
        if (!senhaInput.value || !confirmarSenhaInput.value || senhaInput.value !== confirmarSenhaInput.value) {
            e.preventDefault();
            alert("As senhas são obrigatórias e devem coincidir.");
            confirmarSenhaInput.focus();
        }
    });
}


// ---------- Máscara e validação de CNPJ ----------
export function aplicarMascaraCNPJ(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '').slice(0, 14);
        value = value.replace(/^(\d{2})(\d)/, '$1.$2')
                     .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
                     .replace(/^(\d{2})\.(\d{3})\.(\d{3})(\d)/, '$1.$2.$3/$4')
                     .replace(/^(\d{2})\.(\d{3})\.(\d{3})\/(\d{4})(\d)/, '$1.$2.$3/$4-$5');
        e.target.value = value;
    });
}

export function validarCNPJNoSubmit(formSelector, inputId = 'cnpj') {
    const form = document.querySelector(formSelector);
    const input = document.getElementById(inputId);
    if (!form || !input) return;

    form.addEventListener('submit', function(e) {
        const cnpj = input.value.replace(/\D/g, '');
        if (cnpj.length !== 14) {
            e.preventDefault();
            alert('CNPJ deve conter exatamente 14 dígitos.');
            input.focus();
        }
    });
}

// ---------- Validação de CEP com preenchimento automático ----------
export function aplicarBuscaEndereco(cepId = 'cep', enderecoId = 'endereco') {
  const cepInput = document.getElementById(cepId);
  const enderecoInput = document.getElementById(enderecoId);

  if (!cepInput || !enderecoInput) return;

  cepInput.addEventListener('input', () => {
    let cep = cepInput.value.replace(/\D/g, '');
    if (cep.length > 5) {
      cep = cep.substring(0, 5) + '-' + cep.substring(5, 8);
    }
    cepInput.value = cep;
  });

  cepInput.addEventListener('blur', () => {
    const cep = cepInput.value.replace(/\D/g, '');
    if (cep.length !== 8) return;

    fetch(`https://viacep.com.br/ws/${cep}/json/`)
      .then(res => res.json())
      .then(data => {
        if (!data.erro) {
          enderecoInput.value = `${data.logradouro}, ${data.bairro}, ${data.localidade} - ${data.uf}`;
          enderecoInput.classList.remove('hidden'); // mostra o campo quando preencher
        } else {
          alert('CEP não encontrado.');
          enderecoInput.classList.add('hidden'); // esconde se não encontrar
          enderecoInput.value = '';
        }
      })
      .catch(() => {
        alert('Erro ao buscar endereço.');
        enderecoInput.classList.add('hidden');
        enderecoInput.value = '';
      });
  });
}
