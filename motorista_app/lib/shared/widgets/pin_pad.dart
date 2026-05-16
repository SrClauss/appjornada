import 'package:flutter/material.dart';

/// A 3×4 bank-style PIN pad widget.
/// Calls [onCompleted] once [pinLength] digits have been entered.
class PinPad extends StatefulWidget {
  final int pinLength;
  final ValueChanged<String> onCompleted;

  const PinPad({
    super.key,
    this.pinLength = 4,
    required this.onCompleted,
  });

  @override
  State<PinPad> createState() => _PinPadState();
}

class _PinPadState extends State<PinPad> {
  String _pin = '';

  void _onKey(String value) {
    if (_pin.length >= widget.pinLength) return;
    setState(() => _pin += value);
    if (_pin.length == widget.pinLength) {
      widget.onCompleted(_pin);
    }
  }

  void _onDelete() {
    if (_pin.isEmpty) return;
    setState(() => _pin = _pin.substring(0, _pin.length - 1));
  }

  void clear() => setState(() => _pin = '');

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // PIN dots indicator
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(
            widget.pinLength,
            (i) => Container(
              margin: const EdgeInsets.symmetric(horizontal: 8),
              width: 16,
              height: 16,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: i < _pin.length
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context).colorScheme.outline,
              ),
            ),
          ),
        ),
        const SizedBox(height: 24),
        // Numeric grid
        GridView.count(
          crossAxisCount: 3,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 1.4,
          children: [
            for (final digit in ['1', '2', '3', '4', '5', '6', '7', '8', '9'])
              _KeyButton(label: digit, onTap: () => _onKey(digit)),
            const SizedBox.shrink(), // empty cell
            _KeyButton(label: '0', onTap: () => _onKey('0')),
            _KeyButton(
              icon: Icons.backspace_outlined,
              onTap: _onDelete,
            ),
          ],
        ),
      ],
    );
  }
}

class _KeyButton extends StatelessWidget {
  final String? label;
  final IconData? icon;
  final VoidCallback onTap;

  const _KeyButton({this.label, this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        alignment: Alignment.center,
        margin: const EdgeInsets.all(4),
        constraints: const BoxConstraints(minWidth: 60, minHeight: 60),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
        ),
        child: label != null
            ? Text(
                label!,
                style: Theme.of(context)
                    .textTheme
                    .headlineSmall
                    ?.copyWith(fontWeight: FontWeight.bold),
              )
            : Icon(icon, size: 24),
      ),
    );
  }
}
