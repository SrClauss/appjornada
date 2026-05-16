import 'package:intl/intl.dart';

final _currencyFormatter = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
final _dateFormatter = DateFormat('dd/MM/yyyy', 'pt_BR');
final _dateTimeFormatter = DateFormat('dd/MM/yyyy HH:mm', 'pt_BR');

String formatCurrency(double? value) =>
    value != null ? _currencyFormatter.format(value) : 'R\$ 0,00';

String formatDate(String? isoDate) {
  if (isoDate == null) return '—';
  try {
    return _dateFormatter.format(DateTime.parse(isoDate));
  } catch (_) {
    return isoDate;
  }
}

String formatDateTime(String? iso) {
  if (iso == null) return '—';
  try {
    return _dateTimeFormatter.format(DateTime.parse(iso));
  } catch (_) {
    return iso;
  }
}

String formatDuration(int? seconds) {
  if (seconds == null) return '—';
  final d = Duration(seconds: seconds);
  final h = d.inHours.toString().padLeft(2, '0');
  final m = (d.inMinutes % 60).toString().padLeft(2, '0');
  return '${h}h${m}min';
}
