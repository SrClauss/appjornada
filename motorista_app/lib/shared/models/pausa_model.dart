class PausaModel {
  final String id;
  final String tipo;
  final String? inicio;
  final String? fim;
  final int? duracaoSegundos;

  const PausaModel({
    required this.id,
    required this.tipo,
    this.inicio,
    this.fim,
    this.duracaoSegundos,
  });

  factory PausaModel.fromJson(Map<String, dynamic> json) => PausaModel(
        id: json['id'] as String,
        tipo: json['tipo'] as String? ?? 'PAUSA_MOTORISTA',
        inicio: json['inicio'] as String?,
        fim: json['fim'] as String?,
        duracaoSegundos: json['duracao_segundos'] as int?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'tipo': tipo,
        if (inicio != null) 'inicio': inicio,
        if (fim != null) 'fim': fim,
        if (duracaoSegundos != null) 'duracao_segundos': duracaoSegundos,
      };
}
