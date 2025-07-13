const mongoose = require('mongoose')

const experienciaSchema = new mongoose.Schema({
  empresa: String,
  cargo: String,
  dataInicio: Date,
  dataSaida: Date,
  atualmente: Boolean,
})

const competenciaSchema = new mongoose.Schema({
  nome: String,
  nivel: String, // Exemplo: "Básico", "Intermediário", "Avançado"
})

const userSchema = new mongoose.Schema({
  nome: { type: String, required: true },
  email: { type: String, required: true },
  senha: { type: String, required: true },
  telefone: String,
  linkedin: String,
  pretensaoSalarial: Number,
  experiencias: [experienciaSchema],
  competencias: [competenciaSchema],
})

module.exports = mongoose.model('User', userSchema)