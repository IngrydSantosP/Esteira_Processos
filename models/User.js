const mongoose = require('mongoose');

// Definindo o UserSchema com nomes consistentes
const userSchema = new mongoose.Schema({
  nome: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  senha: { type: String, required: true },
  telefone: String,
  linkedin: String,
  pretensao_salarial: Number, 
});

module.exports = mongoose.model('User', userSchema);