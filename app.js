require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const cors = require('cors');

const app = express();

// Servir arquivos estáticos da pasta 'templates' (ex: cadastro_empresa.html)
app.use(express.static('templates'));

// Requisições
app.use(express.json()); // Para JSON via fetch
app.use(express.urlencoded({ extended: true })); // Para formulários HTML
app.use(cors());

// Models
const User = require('./models/User');
const Empresa = require('./models/Empresa');

// Requisição JWT
function checkToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(" ")[1];

  if (!token) {
    return res.status(401).json({ msg: 'Acesso negado!' });
  }

  try {
    const secret = process.env.SECRET;
    jwt.verify(token, secret);
    next();
  } catch (error) {
    return res.status(400).json({ msg: 'Token inválido!' });
  }
}

// ---------------- ROTAS USUÁRIO ----------------

app.get('/', (req, res) => {
  res.status(200).json({ msg: 'Bem-vindo à nossa API' });
});

app.get('/user/:id', checkToken, async (req, res) => {
  const id = req.params.id;

  try {
    const user = await User.findById(id).select('-senha');
    if (!user) return res.status(404).json({ msg: 'Usuário não encontrado' });

    res.status(200).json({ user });
  } catch (error) {
    res.status(500).json({ msg: 'Erro ao buscar usuário' });
  }
});

app.put('/user/:id', checkToken, async (req, res) => {
  const id = req.params.id;
  const { telefone, linkedin, pretensao_salarial } = req.body;

  try {
    const updatedUser = await User.findByIdAndUpdate(
      id,
      { telefone, linkedin, pretensao_salarial },
      { new: true, runValidators: true }
    ).select('-senha');

    if (!updatedUser) return res.status(404).json({ msg: 'Usuário não encontrado para atualização' });

    res.status(200).json({ msg: 'Perfil atualizado com sucesso!', user: updatedUser });
  } catch (error) {
    res.status(500).json({ msg: 'Erro ao atualizar perfil', error });
  }
});

app.post('/auth/register', async (req, res) => {
  const { nome, email, telefone, linkedin, pretensao_salarial, senha, confirmar_senha } = req.body;

  // Validações
  if (!nome) return res.status(422).json({ msg: 'O nome é obrigatório!' });
  if (!email) return res.status(422).json({ msg: 'O email é obrigatório!' });
  if (!telefone) return res.status(422).json({ msg: 'O telefone é obrigatório!' });
  if (!linkedin) return res.status(422).json({ msg: 'O LinkedIn é obrigatório!' });
  if (pretensao_salarial == null) return res.status(422).json({ msg: 'A pretensão salarial é obrigatória!' });
  if (!senha) return res.status(422).json({ msg: 'A senha é obrigatória!' });
  if (senha !== confirmar_senha) return res.status(422).json({ msg: 'As senhas não estão iguais!' });

  const userExists = await User.findOne({ email });
  if (userExists) return res.status(422).json({ msg: 'Por favor, digite outro email!' });

  const salt = await bcrypt.genSalt(12);
  const passwordHash = await bcrypt.hash(senha, salt);

  const user = new User({
    nome,
    email,
    telefone,
    linkedin,
    pretensao_salarial,
    senha: passwordHash,
  });

  try {
    await user.save();
    res.status(201).json({ msg: 'Usuário criado com sucesso!' });
  } catch (error) {
    console.log(error);
    res.status(500).json({ msg: 'Erro no servidor, tente novamente mais tarde' });
  }
});

app.post('/auth/login', async (req, res) => {
  const { email, senha } = req.body;

  if (!email) return res.status(422).json({ msg: 'O email é obrigatório!' });
  if (!senha) return res.status(422).json({ msg: 'A senha é obrigatória!' });

  const user = await User.findOne({ email });
  if (!user) return res.status(404).json({ msg: 'Usuário não encontrado!' });

  const checkPassword = await bcrypt.compare(senha, user.senha);
  if (!checkPassword) return res.status(422).json({ msg: 'Senha inválida!' });

  try {
    const secret = process.env.SECRET;

    const token = jwt.sign({ id: user._id, nome: user.nome }, secret, { expiresIn: '1h' });

    const { nome, telefone, linkedin, pretensao_salarial } = user;

    res.status(200).json({
      msg: 'Autenticação realizada com sucesso!',
      token,
      nome,
      user: { nome, email, telefone, linkedin, pretensao_salarial }
    });
  } catch (error) {
    console.log(error);
    res.status(500).json({ msg: 'Erro no servidor, tente novamente mais tarde' });
  }
});

// ---------------- ROTAS EMPRESA ----------------

// Rota de registrar empresa
app.post('/empresa/register', async (req, res) => {
  const { cnpj, nome, email, senha } = req.body;

  if (!cnpj) return res.status(422).json({ alerta: 'O CNPJ é obrigatório!' });
  if (!nome) return res.status(422).json({ alerta: 'O nome da empresa é obrigatório!' });
  if (!email) return res.status(422).json({ alerta: 'O email é obrigatório!' });
  if (!senha) return res.status(422).json({ alerta: 'A senha é obrigatória!' });

  try {
    const cnpjExists = await Empresa.findOne({ cnpj });
    if (cnpjExists) return res.status(422).json({ alerta: 'Este CNPJ já está cadastrado!' });

    const emailExists = await Empresa.findOne({ email });
    if (emailExists) return res.status(422).json({ alerta: 'Este email já está cadastrado!' });

    const salt = await bcrypt.genSalt(12);
    const passwordHash = await bcrypt.hash(senha, salt);

    const empresa = new Empresa({
      cnpj,
      nome,
      email,
      senha: passwordHash,
    });

    await empresa.save();
    res.status(201).json({ msg: 'Empresa cadastrada com sucesso!' });
  } catch (error) {
    console.log(error);
    res.status(500).json({ alerta: 'Erro interno no servidor.' });
  }
});

// Rota login empresa 
app.post('/auth/login-empresa', async (req, res) => {
  const { cnpj, senha } = req.body;

  if (!cnpj) return res.status(422).json({ msg: 'O CNPJ é obrigatório!' });
  if (!senha) return res.status(422).json({ msg: 'A senha é obrigatória!' });

  try {
    const empresa = await Empresa.findOne({ cnpj });
    if (!empresa) return res.status(404).json({ msg: 'Empresa não encontrada!' });

    const checkPassword = await bcrypt.compare(senha, empresa.senha);
    if (!checkPassword) return res.status(422).json({ msg: 'Senha inválida!' });

    const secret = process.env.SECRET;
    const token = jwt.sign({ id: empresa._id, nome: empresa.nome }, secret, { expiresIn: '1h' });

    res.status(200).json({
      msg: 'Autenticação realizada com sucesso!',
      token,
      empresa: {
        nome: empresa.nome,
        email: empresa.email,
        cnpj: empresa.cnpj,
      }
    });
  } catch (error) {
    console.log(error);
    res.status(500).json({ msg: 'Erro no servidor, tente novamente mais tarde' });
  }
});

// ---------------- CONEXÃO MONGODB ----------------

const dbUser = process.env.DB_USER;
const dbPassword = process.env.DB_PASS;

mongoose.connect(
  `mongodb+srv://${dbUser}:${dbPassword}@oh14g0.khedpdf.mongodb.net/?retryWrites=true&w=majority&appName=oh14g0`
  
)
  .then(() => {
    console.log('Conectou ao banco!');
    app.listen(3000, () => console.log('Servidor rodando na porta 3000'));
  })
  .catch((err) => console.log('Erro ao conectar ao MongoDB:', err));