class PerfilMotoristaModel {
  final String? cpf;
  final String? telefone;
  final CnhModel? cnh;
  final DadosBancariosModel? dadosBancarios;

  const PerfilMotoristaModel({
    this.cpf,
    this.telefone,
    this.cnh,
    this.dadosBancarios,
  });

  factory PerfilMotoristaModel.fromJson(Map<String, dynamic> json) =>
      PerfilMotoristaModel(
        cpf: json['cpf'] as String?,
        telefone: json['telefone'] as String?,
        cnh: json['cnh'] == null
            ? null
            : CnhModel.fromJson(json['cnh'] as Map<String, dynamic>),
        dadosBancarios: json['dados_bancarios'] == null
            ? null
            : DadosBancariosModel.fromJson(
                json['dados_bancarios'] as Map<String, dynamic>),
      );

  Map<String, dynamic> toJson() => {
        if (cpf != null) 'cpf': cpf,
        if (telefone != null) 'telefone': telefone,
        if (cnh != null) 'cnh': cnh!.toJson(),
        if (dadosBancarios != null) 'dados_bancarios': dadosBancarios!.toJson(),
      };
}

class CnhModel {
  final String? vencimento;
  final String? imagemUrl;

  const CnhModel({this.vencimento, this.imagemUrl});

  factory CnhModel.fromJson(Map<String, dynamic> json) => CnhModel(
        vencimento: json['vencimento'] as String?,
        imagemUrl: json['imagem_url'] as String?,
      );

  Map<String, dynamic> toJson() => {
        if (vencimento != null) 'vencimento': vencimento,
        if (imagemUrl != null) 'imagem_url': imagemUrl,
      };

  bool get isExpired {
    if (vencimento == null) return false;
    return DateTime.parse(vencimento!).isBefore(DateTime.now());
  }
}

class DadosBancariosModel {
  final String? banco;
  final String? agencia;
  final String? conta;
  final String? cnpj;

  const DadosBancariosModel({
    this.banco,
    this.agencia,
    this.conta,
    this.cnpj,
  });

  factory DadosBancariosModel.fromJson(Map<String, dynamic> json) =>
      DadosBancariosModel(
        banco: json['banco'] as String?,
        agencia: json['agencia'] as String?,
        conta: json['conta'] as String?,
        cnpj: json['cnpj'] as String?,
      );

  Map<String, dynamic> toJson() => {
        if (banco != null) 'banco': banco,
        if (agencia != null) 'agencia': agencia,
        if (conta != null) 'conta': conta,
        if (cnpj != null) 'cnpj': cnpj,
      };
}

class UserModel {
  final String id;
  final String nome;
  final String email;
  final String role;
  final PerfilMotoristaModel? perfilMotorista;

  const UserModel({
    required this.id,
    required this.nome,
    required this.email,
    required this.role,
    this.perfilMotorista,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) => UserModel(
        id: json['id'] as String? ?? json['_id'] as String,
        nome: json['nome'] as String,
        email: json['email'] as String,
        role: json['role'] as String,
        perfilMotorista: json['perfil_motorista'] == null
            ? null
            : PerfilMotoristaModel.fromJson(
                json['perfil_motorista'] as Map<String, dynamic>),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'nome': nome,
        'email': email,
        'role': role,
        if (perfilMotorista != null)
          'perfil_motorista': perfilMotorista!.toJson(),
      };
}
