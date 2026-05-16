import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

/// A photo picker widget with inline preview.
/// [onImageSelected] is called whenever the user picks/takes a new photo.
class FotoPickerWidget extends StatefulWidget {
  final String label;
  final ValueChanged<File> onImageSelected;
  final File? initialImage;

  const FotoPickerWidget({
    super.key,
    required this.label,
    required this.onImageSelected,
    this.initialImage,
  });

  @override
  State<FotoPickerWidget> createState() => _FotoPickerWidgetState();
}

class _FotoPickerWidgetState extends State<FotoPickerWidget> {
  File? _image;
  final _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _image = widget.initialImage;
  }

  Future<void> _pick(ImageSource source) async {
    if (source == ImageSource.camera) {
      final status = await Permission.camera.request();
      if (!status.isGranted) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Permissão de câmera negada')),
          );
        }
        return;
      }
    }
    final picked = await _picker.pickImage(source: source, imageQuality: 80);
    if (picked != null) {
      final file = File(picked.path);
      setState(() => _image = file);
      widget.onImageSelected(file);
    }
  }

  void _showSourceDialog() {
    showModalBottomSheet<void>(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text('Tirar foto'),
              onTap: () {
                Navigator.pop(context);
                _pick(ImageSource.camera);
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Escolher da galeria'),
              onTap: () {
                Navigator.pop(context);
                _pick(ImageSource.gallery);
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(widget.label, style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 8),
        GestureDetector(
          onTap: _showSourceDialog,
          child: Container(
            width: double.infinity,
            height: 180,
            decoration: BoxDecoration(
              border: Border.all(
                color: Theme.of(context).colorScheme.outline,
                style: _image == null ? BorderStyle.none : BorderStyle.solid,
              ),
              borderRadius: BorderRadius.circular(12),
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
            ),
            child: _image == null
                ? Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.add_a_photo_outlined,
                          size: 48,
                          color: Theme.of(context).colorScheme.primary),
                      const SizedBox(height: 8),
                      Text(
                        'Toque para adicionar foto',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurfaceVariant),
                      ),
                    ],
                  )
                : ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.file(_image!, fit: BoxFit.cover),
                  ),
          ),
        ),
        if (_image != null) ...[
          const SizedBox(height: 4),
          TextButton.icon(
            onPressed: _showSourceDialog,
            icon: const Icon(Icons.refresh, size: 16),
            label: const Text('Alterar foto'),
          ),
        ],
      ],
    );
  }
}
