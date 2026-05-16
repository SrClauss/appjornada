import 'pausa_model.dart';
import 'abastecimento_model.dart';

class KmJornadaModel {
  final double? inicial;
  final double? final_;
  final double? rodados;

  const KmJornadaModel({this.inicial, this.final_, this.rodados});

  factory KmJornadaModel.fromJson(Map<String, dynamic> json) => KmJornadaModel(
        inicial: (json['inicial'] as num?)?.toDouble(),
        final_: (json['final'] as num?)?.toDouble(),
        rodados: (json['rodados'] as num?)?.toDouble(),
      );
}

class HorarioJornadaModel {
  final String? inicio;
  final String? fim;
  final int? totalHorasSegundos;

  const HorarioJornadaModel({this.inicio, this.fim, this.totalHorasSegundos});

  factory HorarioJornadaModel.fromJson(Map<String, dynamic> json) =>
      HorarioJornadaModel(
        inicio: json['inicio'] as String?,
        fim: json['fim'] as String?,
        totalHorasSegundos: json['total_horas_segundos'] as int?,
      );
}

class FaturamentoModel {
  final double? uber;
  final double? noventaNove;
  final double? outros;
  final double? totalDia;

  const FaturamentoModel({
    this.uber,
    this.noventaNove,
    this.outros,
    this.totalDia,
  });

  factory FaturamentoModel.fromJson(Map<String, dynamic> json) =>
      FaturamentoModel(
        uber: (json['uber'] as num?)?.toDouble(),
        noventaNove: (json['noventa_nove'] as num?)?.toDouble(),
        outros: (json['outros'] as num?)?.toDouble(),
        totalDia: (json['total_dia'] as num?)?.toDouble(),
      );
}

class JornadaModel {
  final String id;
  final String? status;
  final String? data;
  final KmJornadaModel? km;
  final HorarioJornadaModel? horario;
  final FaturamentoModel? faturamento;
  final double? saldoHorasDia;
  final List<PausaModel> pausas;
  final List<AbastecimentoModel> abastecimentos;

  const JornadaModel({
    required this.id,
    this.status,
    this.data,
    this.km,
    this.horario,
    this.faturamento,
    this.saldoHorasDia,
    this.pausas = const [],
    this.abastecimentos = const [],
  });

  factory JornadaModel.fromJson(Map<String, dynamic> json) => JornadaModel(
        id: json['id'] as String? ?? json['_id'] as String,
        status: json['status'] as String?,
        data: json['data'] as String?,
        km: json['km'] == null
            ? null
            : KmJornadaModel.fromJson(json['km'] as Map<String, dynamic>),
        horario: json['horario'] == null
            ? null
            : HorarioJornadaModel.fromJson(
                json['horario'] as Map<String, dynamic>),
        faturamento: json['faturamento'] == null
            ? null
            : FaturamentoModel.fromJson(
                json['faturamento'] as Map<String, dynamic>),
        saldoHorasDia: (json['saldo_horas_dia'] as num?)?.toDouble(),
        pausas: (json['pausas'] as List<dynamic>?)
                ?.map((e) => PausaModel.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [],
        abastecimentos: (json['abastecimentos'] as List<dynamic>?)
                ?.map((e) =>
                    AbastecimentoModel.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [],
      );

  bool get isAberta =>
      status == 'ABERTA' || status == 'EM_ANDAMENTO';

  bool get isEmPausa => status == 'EM_PAUSA';

  /// Returns the active (unfinished) pause, if any.
  PausaModel? get pausaAtiva =>
      pausas.where((p) => p.fim == null).firstOrNull;
}
