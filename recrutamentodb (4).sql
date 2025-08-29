-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 29/08/2025 às 05:38
-- Versão do servidor: 10.4.32-MariaDB
-- Versão do PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `recrutamentodb`
--

-- --------------------------------------------------------

--
-- Estrutura para tabela `candidatos`
--

CREATE TABLE `candidatos` (
  `id` int(11) NOT NULL,
  `nome` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `senha_hash` varchar(255) NOT NULL,
  `telefone` varchar(50) DEFAULT NULL,
  `linkedin` varchar(255) DEFAULT NULL,
  `pretensao_salarial` decimal(10,2) DEFAULT NULL,
  `cep` varchar(9) NOT NULL,
  `endereco` varchar(255) NOT NULL,
  `numero` varchar(10) NOT NULL,
  `complemento` varchar(100) DEFAULT NULL,
  `experiencia` text DEFAULT NULL,
  `competencias` text DEFAULT NULL,
  `resumo_profissional` text DEFAULT NULL,
  `caminho_curriculo` varchar(255) DEFAULT NULL,
  `data_cadastro` timestamp NOT NULL DEFAULT current_timestamp(),
  `formacao` text DEFAULT NULL,
  `data_ultima_atualizacao` timestamp NOT NULL DEFAULT current_timestamp(),
  `certificacoes` text DEFAULT NULL,
  `idiomas` text DEFAULT NULL,
  `disponibilidade` enum('Presencial','Remoto','Híbrido') DEFAULT NULL,
  `beneficios_desejados` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `candidatos`
--

INSERT INTO `candidatos` (`id`, `nome`, `email`, `senha_hash`, `telefone`, `linkedin`, `pretensao_salarial`, `cep`, `endereco`, `numero`, `complemento`, `experiencia`, `competencias`, `resumo_profissional`, `caminho_curriculo`, `data_cadastro`, `formacao`, `data_ultima_atualizacao`, `certificacoes`, `idiomas`, `disponibilidade`, `beneficios_desejados`) VALUES
(1, 'teste', 'teste@teste.com', 'scrypt:32768:8:1$Lu79vxXcfLy9aW2R$f0babcd2b61ec5d5ca4d07d080befeea79f6a92f1b378b25dc40e5452120e6e9e45f088bea48ed7b65377428190a9f11c26321c0c5201252da34f0677792d540', '11987654321', 'https://mail.google.com/mail/u/1/#inbox', 2000.00, '07032-000', 'Rua Cabo João Teruel Fregoni, Ponte Grande, Guarulhos - SP', '307', 'fdfhfg', '​\r\n ANALISTA DE DADOS JÚNIOR – TOTVS​\r\n JAN 2021 – ATUAL \r\n●​ DESENVOLVEU DASHBOARDS NO POWER BI PARA ÁREAS DE VENDAS E LOGÍSTICA.​\r\n \r\n●​ AUTOMATIZOU RELATÓRIOS EM PYTHON E SQL, REDUZINDO O TEMPO DE ENTREGA EM 40%.​\r\n \r\n●​ PARTICIPOU DE PROJETO DE MODELAGEM PREDITIVA PARA CHURN DE CLIENTES.​\r\n \r\nESTAGIÁRIA EM ANÁLISE DE DADOS – ITAÚ UNIBANCO​\r\n JUL 2019 – DEZ 2020 \r\n●​ AUXILIOU NA CRIAÇÃO DE RELATÓRIOS MENSAIS USANDO EXCEL E SQL.​\r\n \r\n●​ REALIZOU ANÁLISES EXPLORATÓRIAS DE GRANDES VOLUMES DE DADOS FINANCEIROS.​\r\n \r\n \r\nCERTIFICAÇÕES \r\n●​ GOOGLE DATA ANALYTICS PROFESSIONAL CERTIFICATE – COURSERA​\r\n \r\n●​ PYTHON FOR DATA SCIENCE – DATACAMP​\r\n \r\n●​ SQL AVANÇADO – ALURA​', 'TÉCNICAS E VISÃO \r\nESTRATÉGICA PARA OTIMIZAÇÃO DE PROCESSOS E GERAÇÃO DE INSIGHTS. \r\n \r\nRESUMO PROFISSIONAL​\r\n PROFISSIONAL COM 3 ANOS DE', '​\r\n PROFISSIONAL COM 3 ANOS DE', NULL, '2025-08-22 16:05:58', 'ACADÊMICA​\r\n BACHARELADO EM ESTATÍSTICA​\r\n UNIVERSIDADE DE SÃO PAULO – USP​\r\n 2014 – 2018', '2025-08-29 01:43:20', NULL, NULL, NULL, NULL),
(2, 'teste', 'teste2@teste.com', 'scrypt:32768:8:1$XRt43SVnMdAHtEUa$a9643de891f292bdaacad3a6f9a68e221378022a56f2055fd780c0e5a90b31fad101f8c3d1434608a62ca1d8054561eb57f0cab5c9913cef8fdeae9f2dbcf0b6', '11987654321', 'https://mail.google.com/mail/u/1/#inbox', 1000.00, '07032-000', 'Rua Cabo João Teruel Fregoni, Ponte Grande, Guarulhos - SP', '307', 'fdfhfg', 'ANALISTA DE DADOS JÚNIOR – TOTVS\r\nJAN 2021 – ATUAL\r\n- DESENVOLVEU DASHBOARDS NO POWER BI PARA ÁREAS DE VENDAS E LOGÍSTICA.\r\n- AUTOMATIZOU RELATÓRIOS EM PYTHON E SQL, REDUZINDO O TEMPO DE ENTREGA EM 40%.\r\n- PARTICIPOU DE PROJETO DE MODELAGEM PREDITIVA PARA CHURN DE CLIENTES.\r\nESTAGIÁRIA EM ANÁLISE DE DADOS – ITAÚ UNIBANCO\r\nJUL 2019 – DEZ 2020\r\n- AUXILIOU NA CRIAÇÃO DE RELATÓRIOS MENSAIS USANDO EXCEL E SQL.\r\n- REALIZOU ANÁLISES EXPLORATÓRIAS DE GRANDES VOLUMES DE DADOS FINANCEIROS.', 'TÉCNICAS E VISÃO ESTRATÉGICA PARA OTIMIZAÇÃO D', 'ATUAR NA ÁREA DE ANÁLISE DE DADOS, CONTRIBUINDO COM', NULL, '2025-08-29 01:19:12', 'ACADÊMICA\r\nBACHARELADO EM ESTATÍSTICA\r\nUNIVERSIDADE DE SÃO PAULO – USP\r\n2014 – 2018', '2025-08-29 03:12:55', '', '', '', '');

-- --------------------------------------------------------

--
-- Estrutura para tabela `candidato_vaga_favorita`
--

CREATE TABLE `candidato_vaga_favorita` (
  `id` int(11) NOT NULL,
  `candidato_id` int(11) DEFAULT NULL,
  `vaga_id` int(11) DEFAULT NULL,
  `data_criacao` timestamp NOT NULL DEFAULT current_timestamp(),
  `data_adicao` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `candidato_vaga_favorita`
--

INSERT INTO `candidato_vaga_favorita` (`id`, `candidato_id`, `vaga_id`, `data_criacao`, `data_adicao`) VALUES
(2, 1, 2, '2025-08-29 03:30:00', '2025-08-29 03:30:00');

-- --------------------------------------------------------

--
-- Estrutura para tabela `candidaturas`
--

CREATE TABLE `candidaturas` (
  `id` int(11) NOT NULL,
  `candidato_id` int(11) NOT NULL,
  `vaga_id` int(11) NOT NULL,
  `score` decimal(5,2) NOT NULL,
  `posicao` int(11) DEFAULT NULL,
  `data_candidatura` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `candidaturas`
--

INSERT INTO `candidaturas` (`id`, `candidato_id`, `vaga_id`, `score`, `posicao`, `data_candidatura`) VALUES
(2, 1, 2, 8.00, 1, '2025-08-29 00:20:58');

-- --------------------------------------------------------

--
-- Estrutura para tabela `categorias`
--

CREATE TABLE `categorias` (
  `id` int(11) NOT NULL,
  `nome` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `categorias`
--

INSERT INTO `categorias` (`id`, `nome`) VALUES
(1, 'Tecnologia');

-- --------------------------------------------------------

--
-- Estrutura para tabela `configuracao_score`
--

CREATE TABLE `configuracao_score` (
  `id` int(11) NOT NULL,
  `empresa_id` int(11) NOT NULL,
  `vaga_id` int(11) DEFAULT NULL,
  `peso_requisitos` decimal(5,2) DEFAULT 30.00,
  `peso_experiencia` decimal(5,2) DEFAULT 25.00,
  `peso_salarial` decimal(5,2) DEFAULT 20.00,
  `peso_formacao` decimal(5,2) DEFAULT 15.00,
  `peso_localizacao` decimal(5,2) DEFAULT 10.00,
  `data_criacao` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `configuracoes_score_empresa`
--

CREATE TABLE `configuracoes_score_empresa` (
  `id` int(11) NOT NULL,
  `empresa_id` int(11) NOT NULL,
  `nome_configuracao` varchar(255) DEFAULT 'Padrão',
  `peso_salarial` decimal(5,2) DEFAULT 20.00,
  `peso_requisitos` decimal(5,2) DEFAULT 40.00,
  `peso_experiencia` decimal(5,2) DEFAULT 15.00,
  `peso_diferenciais` decimal(5,2) DEFAULT 10.00,
  `peso_localizacao` decimal(5,2) DEFAULT 10.00,
  `peso_formacao` decimal(5,2) DEFAULT 5.00,
  `ativo` tinyint(1) DEFAULT 1,
  `data_criacao` timestamp NOT NULL DEFAULT current_timestamp(),
  `data_atualizacao` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `empresas`
--

CREATE TABLE `empresas` (
  `id` int(11) NOT NULL,
  `cnpj` varchar(50) NOT NULL,
  `nome` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `senha_hash` varchar(255) NOT NULL,
  `endereco` varchar(255) DEFAULT NULL,
  `cidade` varchar(100) DEFAULT NULL,
  `estado` varchar(100) DEFAULT NULL,
  `cep` varchar(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `empresas`
--

INSERT INTO `empresas` (`id`, `cnpj`, `nome`, `email`, `senha_hash`, `endereco`, `cidade`, `estado`, `cep`) VALUES
(1, '12.345.678/0001-91', 'Shevchenko INC', 'hiagoleonardodecarvalho@outlook.com', 'scrypt:32768:8:1$Swwx7Ee1sKACF2Qb$97552465848878cbce6db5602fc841c4f5d773355ec4649f282c73ee305f6b8ad645fe94af061860a57477c5b8214a3c3c92db7cfd6f69e96d037759649aae8b', 'Jardim Ponte Alta', 'Guarulhos', 'SP', '07179022'),
(2, '12.345.678/9123-45', 'texte2', 'testewrwr@teste.com', 'scrypt:32768:8:1$KSn1Vzw1ZdDCylZ8$cf91da3ef658a66a0d274e6e73cba2d88d1765b142aae92a96c8f0481a7f493af63225633b02121ce9da11f15fe3916a20c2ef14282844cd004d6120d06b1073', '', '', '', '07032-000'),
(3, '12345678901256', 'wtftfrw', 't@teste.com', 'scrypt:32768:8:1$rc0hadEUaxRLCJHy$9168f28c94b093f7cfe593a2674a14b5533a7cbce79cff609fc453c28dbbc0fa72dbdeb27cdba1e1becb2e8ef916cfec211cb423bff72f298c2fe1b642843861', '', '', '', '07032-000'),
(4, '12.345.678/9123-45', 'texte', 'santos.ingryd.p@gmail.com', 'scrypt:32768:8:1$UJObpeVvVIUACgSd$6a283b781abdbd1430f5318d17e08d704e2504f665bffc53e785522b4c7d9e3c7563736a9969c9af76add7c6594d1f56d375cc84ba484a198f47872d6f1efdbf', 'Rua Cabo João Teruel Fregoni, Ponte Grande, Guarulhos - SP', '', '', '07032-000');

-- --------------------------------------------------------

--
-- Estrutura para tabela `empresa_candidato_favorito`
--

CREATE TABLE `empresa_candidato_favorito` (
  `id` int(11) NOT NULL,
  `empresa_id` int(11) DEFAULT NULL,
  `candidato_id` int(11) DEFAULT NULL,
  `vaga_id` int(11) DEFAULT NULL,
  `data_criacao` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `empresa_favorito_candidato_geral`
--

CREATE TABLE `empresa_favorito_candidato_geral` (
  `id` int(11) NOT NULL,
  `empresa_id` int(11) NOT NULL,
  `candidato_id` int(11) NOT NULL,
  `data_criacao` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `notificacoes`
--

CREATE TABLE `notificacoes` (
  `id` int(11) NOT NULL,
  `candidato_id` int(11) NOT NULL,
  `empresa_id` int(11) NOT NULL,
  `vaga_id` int(11) NOT NULL,
  `mensagem` text NOT NULL,
  `data_envio` timestamp NOT NULL DEFAULT current_timestamp(),
  `lida` tinyint(1) DEFAULT 0,
  `tipo` varchar(50) DEFAULT 'geral',
  `titulo` varchar(255) DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `notificacoes`
--

INSERT INTO `notificacoes` (`id`, `candidato_id`, `empresa_id`, `vaga_id`, `mensagem`, `data_envio`, `lida`, `tipo`, `titulo`) VALUES
(1, 1, 2, 1, '🎯 CANDIDATURA REALIZADA COM SUCESSO!\n\n🏢 Empresa: texte2\n💼 Vaga: Desenvolvedor \n📊 Sua posição: 1º lugar (de 1 candidatos)\n⭐ Score de compatibilidade: 26%\n💰 Salário: R$ 3,000.00 (Remoto)\n\n📈 ESTATÍSTICAS DA VAGA:\n• Total de candidatos: 1\n• Vaga ativa há: 7 dias\n• Urgência: Em até 30 dias\n\n🔔 PRÓXIMOS PASSOS:\n1. Acompanhe sua posição no ranking\n2. Mantenha seu perfil atualizado\n3. Prepare-se para possível contato da empresa\n4. Continue explorando outras oportunidades\n\n💡 DICAS PARA SE DESTACAR:\n• Complete seu perfil se ainda não fez\n• Adicione certificações relevantes\n• Mantenha suas experiências atualizadas\n\nData da candidatura: 28/08/2025 às 20:09\n\nBoa sorte! 🍀', '2025-08-28 23:09:29', 0, 'nova_candidatura', '🎯 CANDIDATURA REALIZADA COM SUCESSO!'),
(2, 1, 2, 2, '🎯 CANDIDATURA REALIZADA COM SUCESSO!\n\n🏢 Empresa: texte2\n💼 Vaga: Analista de BI\n📊 Sua posição: 1º lugar (de 1 candidatos)\n⭐ Score de compatibilidade: 8%\n💰 Salário: R$ 1,000.00 (Presencial)\n\n📈 ESTATÍSTICAS DA VAGA:\n• Total de candidatos: 1\n• Vaga ativa há: 0 dias\n• Urgência: Em até 30 dias\n\n🔔 PRÓXIMOS PASSOS:\n1. Acompanhe sua posição no ranking\n2. Mantenha seu perfil atualizado\n3. Prepare-se para possível contato da empresa\n4. Continue explorando outras oportunidades\n\n💡 DICAS PARA SE DESTACAR:\n• Complete seu perfil se ainda não fez\n• Adicione certificações relevantes\n• Mantenha suas experiências atualizadas\n\nData da candidatura: 28/08/2025 às 21:20\n\nBoa sorte! 🍀', '2025-08-29 00:20:59', 0, 'nova_candidatura', '🎯 CANDIDATURA REALIZADA COM SUCESSO!'),
(3, 1, 2, 1, '🎯 CANDIDATURA REALIZADA COM SUCESSO!\n\n🏢 Empresa: texte2\n💼 Vaga: Desenvolvedor \n📊 Sua posição: 1º lugar (de 1 candidatos)\n⭐ Score de compatibilidade: 22.8%\n💰 Salário: R$ 3,000.00 (Remoto)\n\n📈 ESTATÍSTICAS DA VAGA:\n• Total de candidatos: 1\n• Vaga ativa há: 7 dias\n• Urgência: Em até 30 dias\n\n🔔 PRÓXIMOS PASSOS:\n1. Acompanhe sua posição no ranking\n2. Mantenha seu perfil atualizado\n3. Prepare-se para possível contato da empresa\n4. Continue explorando outras oportunidades\n\n💡 DICAS PARA SE DESTACAR:\n• Complete seu perfil se ainda não fez\n• Adicione certificações relevantes\n• Mantenha suas experiências atualizadas\n\nData da candidatura: 29/08/2025 às 00:04\n\nBoa sorte! 🍀', '2025-08-29 03:04:41', 0, 'nova_candidatura', '🎯 CANDIDATURA REALIZADA COM SUCESSO!');

-- --------------------------------------------------------

--
-- Estrutura para tabela `templates_score`
--

CREATE TABLE `templates_score` (
  `id` int(11) NOT NULL,
  `nome_template` varchar(255) NOT NULL,
  `descricao` text DEFAULT NULL,
  `categoria` varchar(100) DEFAULT 'geral',
  `peso_salarial` decimal(5,2) DEFAULT 20.00,
  `peso_requisitos` decimal(5,2) DEFAULT 40.00,
  `peso_experiencia` decimal(5,2) DEFAULT 15.00,
  `peso_diferenciais` decimal(5,2) DEFAULT 10.00,
  `peso_localizacao` decimal(5,2) DEFAULT 10.00,
  `peso_formacao` decimal(5,2) DEFAULT 5.00,
  `data_criacao` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `templates_score`
--

INSERT INTO `templates_score` (`id`, `nome_template`, `descricao`, `categoria`, `peso_salarial`, `peso_requisitos`, `peso_experiencia`, `peso_diferenciais`, `peso_localizacao`, `peso_formacao`, `data_criacao`) VALUES
(1, 'Padrão Equilibrado', 'Configuração balanceada para a maioria das vagas', 'geral', 20.00, 40.00, 15.00, 10.00, 10.00, 5.00, '2025-08-28 23:54:08'),
(2, 'Foco Técnico', 'Prioriza habilidades técnicas e experiência', 'tecnologia', 10.00, 50.00, 25.00, 10.00, 5.00, 0.00, '2025-08-28 23:54:08'),
(3, 'Startup Flexível', 'Para startups que valorizam potencial e flexibilidade', 'startup', 30.00, 30.00, 10.00, 20.00, 10.00, 0.00, '2025-08-28 23:54:08'),
(4, 'Empresa Tradicional', 'Valoriza formação e localização', 'tradicional', 15.00, 35.00, 20.00, 5.00, 15.00, 10.00, '2025-08-28 23:54:08'),
(5, 'Remoto First', 'Para empresas 100% remotas', 'remoto', 25.00, 45.00, 20.00, 10.00, 0.00, 0.00, '2025-08-28 23:54:08'),
(11, 'Vendas & Relacionamento', 'Para cargos de vendas e atendimento', 'vendas', 25.00, 25.00, 20.00, 20.00, 10.00, 0.00, '2025-08-29 00:32:37'),
(12, 'Gestão & Liderança', 'Para cargos de coordenação e gerência', 'gestao', 15.00, 30.00, 30.00, 15.00, 5.00, 5.00, '2025-08-29 00:32:37');

-- --------------------------------------------------------

--
-- Estrutura para tabela `vagas`
--

CREATE TABLE `vagas` (
  `id` int(11) NOT NULL,
  `empresa_id` int(11) NOT NULL,
  `titulo` varchar(255) NOT NULL,
  `descricao` text NOT NULL,
  `requisitos` text NOT NULL,
  `salario_oferecido` decimal(10,2) NOT NULL,
  `data_criacao` timestamp NOT NULL DEFAULT current_timestamp(),
  `tipo_vaga` enum('Presencial','Remoto','Híbrido') DEFAULT 'Presencial',
  `endereco_vaga` varchar(255) DEFAULT NULL,
  `status` enum('Ativa','Inativa','Congelada','Concluída') DEFAULT 'Ativa',
  `candidato_selecionado_id` int(11) DEFAULT NULL,
  `diferenciais` text DEFAULT NULL,
  `data_congelamento` timestamp NULL DEFAULT NULL,
  `candidato_contratado_id` int(11) DEFAULT NULL,
  `data_contratacao` timestamp NULL DEFAULT NULL,
  `ranking_contratacao` int(11) DEFAULT NULL,
  `categoria_id` int(11) DEFAULT NULL,
  `urgencia_contratacao` varchar(100) DEFAULT NULL,
  `data_congelamento_agendado` timestamp NULL DEFAULT NULL,
  `localizacao_endereco` varchar(255) DEFAULT NULL,
  `localizacao_cidade` varchar(100) DEFAULT NULL,
  `localizacao_estado` varchar(100) DEFAULT NULL,
  `localizacao_cep` varchar(20) DEFAULT NULL,
  `usar_endereco_empresa` tinyint(1) DEFAULT 0,
  `turno_trabalho` enum('Manhã','Tarde','Noite','Flexível','Comercial') DEFAULT 'Comercial',
  `nivel_experiencia` enum('Estagiário','Júnior','Pleno','Sênior','Especialista') DEFAULT 'Júnior',
  `regime_contratacao` enum('CLT','PJ','Estágio','Freelancer','Temporário') DEFAULT 'CLT',
  `carga_horaria` varchar(50) DEFAULT '40h',
  `formacao_minima` enum('Ensino Fundamental','Ensino Médio','Técnico','Graduação','Pós-graduação','Mestrado','Doutorado') DEFAULT 'Ensino Médio',
  `idiomas_exigidos` text DEFAULT NULL,
  `disponibilidade_viagens` tinyint(1) DEFAULT 0,
  `beneficios` text DEFAULT NULL,
  `data_limite_candidatura` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `vagas`
--

INSERT INTO `vagas` (`id`, `empresa_id`, `titulo`, `descricao`, `requisitos`, `salario_oferecido`, `data_criacao`, `tipo_vaga`, `endereco_vaga`, `status`, `candidato_selecionado_id`, `diferenciais`, `data_congelamento`, `candidato_contratado_id`, `data_contratacao`, `ranking_contratacao`, `categoria_id`, `urgencia_contratacao`, `data_congelamento_agendado`, `localizacao_endereco`, `localizacao_cidade`, `localizacao_estado`, `localizacao_cep`, `usar_endereco_empresa`, `turno_trabalho`, `nivel_experiencia`, `regime_contratacao`, `carga_horaria`, `formacao_minima`, `idiomas_exigidos`, `disponibilidade_viagens`, `beneficios`, `data_limite_candidatura`) VALUES
(1, 2, 'Desenvolvedor ', 'teste', 'teste', 3000.00, '2025-08-21 20:29:20', 'Remoto', NULL, 'Ativa', NULL, 'teste', NULL, NULL, NULL, NULL, 1, 'Em até 30 dias', NULL, '', '', '', '07032-000', 1, 'Comercial', 'Júnior', 'CLT', '40h', 'Ensino Médio', NULL, 0, NULL, NULL),
(2, 2, 'Analista de BI', 'iojiuioou', '9j997y7', 1000.00, '2025-08-29 00:20:24', 'Presencial', NULL, 'Ativa', NULL, '0u80u8u8u', NULL, NULL, NULL, NULL, 1, 'Em até 30 dias', NULL, 'Rua Cabo João Teruel Fregoni, Ponte Grande, Guarulhos - SP, 307', 'Guarrulhos', 'SP', '', 0, 'Comercial', 'Júnior', 'CLT', '40h', 'Ensino Médio', NULL, 0, NULL, NULL);

--
-- Índices para tabelas despejadas
--

--
-- Índices de tabela `candidatos`
--
ALTER TABLE `candidatos`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `candidato_vaga_favorita`
--
ALTER TABLE `candidato_vaga_favorita`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `candidaturas`
--
ALTER TABLE `candidaturas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_candidaturas_candidato` (`candidato_id`),
  ADD KEY `fk_candidaturas_vaga` (`vaga_id`);

--
-- Índices de tabela `categorias`
--
ALTER TABLE `categorias`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `configuracao_score`
--
ALTER TABLE `configuracao_score`
  ADD PRIMARY KEY (`id`),
  ADD KEY `empresa_id` (`empresa_id`),
  ADD KEY `vaga_id` (`vaga_id`);

--
-- Índices de tabela `configuracoes_score_empresa`
--
ALTER TABLE `configuracoes_score_empresa`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_empresa_config` (`empresa_id`,`nome_configuracao`);

--
-- Índices de tabela `empresas`
--
ALTER TABLE `empresas`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `empresa_candidato_favorito`
--
ALTER TABLE `empresa_candidato_favorito`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `empresa_favorito_candidato_geral`
--
ALTER TABLE `empresa_favorito_candidato_geral`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `notificacoes`
--
ALTER TABLE `notificacoes`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `templates_score`
--
ALTER TABLE `templates_score`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `nome_template` (`nome_template`);

--
-- Índices de tabela `vagas`
--
ALTER TABLE `vagas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_vagas_empresa` (`empresa_id`),
  ADD KEY `fk_vagas_categoria` (`categoria_id`);

--
-- AUTO_INCREMENT para tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `candidatos`
--
ALTER TABLE `candidatos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de tabela `candidato_vaga_favorita`
--
ALTER TABLE `candidato_vaga_favorita`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de tabela `candidaturas`
--
ALTER TABLE `candidaturas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de tabela `categorias`
--
ALTER TABLE `categorias`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `configuracao_score`
--
ALTER TABLE `configuracao_score`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `configuracoes_score_empresa`
--
ALTER TABLE `configuracoes_score_empresa`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `empresas`
--
ALTER TABLE `empresas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `empresa_candidato_favorito`
--
ALTER TABLE `empresa_candidato_favorito`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `empresa_favorito_candidato_geral`
--
ALTER TABLE `empresa_favorito_candidato_geral`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `notificacoes`
--
ALTER TABLE `notificacoes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de tabela `templates_score`
--
ALTER TABLE `templates_score`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT de tabela `vagas`
--
ALTER TABLE `vagas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `candidaturas`
--
ALTER TABLE `candidaturas`
  ADD CONSTRAINT `fk_candidaturas_candidato` FOREIGN KEY (`candidato_id`) REFERENCES `candidatos` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_candidaturas_vaga` FOREIGN KEY (`vaga_id`) REFERENCES `vagas` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `configuracao_score`
--
ALTER TABLE `configuracao_score`
  ADD CONSTRAINT `configuracao_score_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  ADD CONSTRAINT `configuracao_score_ibfk_2` FOREIGN KEY (`vaga_id`) REFERENCES `vagas` (`id`);

--
-- Restrições para tabelas `configuracoes_score_empresa`
--
ALTER TABLE `configuracoes_score_empresa`
  ADD CONSTRAINT `configuracoes_score_empresa_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `vagas`
--
ALTER TABLE `vagas`
  ADD CONSTRAINT `fk_vagas_categoria` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_vagas_empresa` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
