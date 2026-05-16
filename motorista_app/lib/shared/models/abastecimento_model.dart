class AbastecimentoModel {
  final String id;
  final double? km;
  final double? valorGasolina;
  final double? valorGnv;
  final double? valorEtanol;
  final String? fotoComprovanteUrl;

  const AbastecimentoModel({
    required this.id,
    this.km,
    this.valorGasolina,
    this.valorGnv,
    this.valorEtanol,
    this.fotoComprovanteUrl,
  });

  factory AbastecimentoModel.fromJson(Map<String, dynamic> json) =>
      AbastecimentoModel(
        id: json['id'] as String,
        km: (json['km'] as num?)?.toDouble(),
        valorGasolina: (json['valor_gasolina'] as num?)?.toDouble(),
        valorGnv: (json['valor_gnv'] as num?)?.toDouble(),
        valorEtanol: (json['valor_etanol'] as num?)?.toDouble(),
        fotoComprovanteUrl: json['foto_comprovante_url'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        if (km != null) 'km': km,
        if (valorGasolina != null) 'valor_gasolina': valorGasolina,
        if (valorGnv != null) 'valor_gnv': valorGnv,
        if (valorEtanol != null) 'valor_etanol': valorEtanol,
        if (fotoComprovanteUrl != null)
          'foto_comprovante_url': fotoComprovanteUrl,
      };
}
