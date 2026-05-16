class VeiculoModel {
  final String idPlaca;
  final String? marcaModelo;
  final String? anoModelo;
  final String? cor;
  final String situacao;

  const VeiculoModel({
    required this.idPlaca,
    this.marcaModelo,
    this.anoModelo,
    this.cor,
    this.situacao = 'RODANDO',
  });

  factory VeiculoModel.fromJson(Map<String, dynamic> json) => VeiculoModel(
        idPlaca: json['id_placa'] as String? ??
            json['_id'] as String? ??
            json['id'] as String,
        marcaModelo: json['marca_modelo'] as String?,
        anoModelo: json['ano_modelo'] as String?,
        cor: json['cor'] as String?,
        situacao: json['situacao'] as String? ?? 'RODANDO',
      );

  Map<String, dynamic> toJson() => {
        'id_placa': idPlaca,
        if (marcaModelo != null) 'marca_modelo': marcaModelo,
        if (anoModelo != null) 'ano_modelo': anoModelo,
        if (cor != null) 'cor': cor,
        'situacao': situacao,
      };

  @override
  String toString() => marcaModelo != null ? '$idPlaca — $marcaModelo' : idPlaca;
}
