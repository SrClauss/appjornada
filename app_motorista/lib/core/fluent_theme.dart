import 'package:flutter/material.dart';

class FluentColors {
  static const Color background = Color(0xFF0B0F19);
  static const Color cardBackground = Color(0xFF161E2E);
  static const Color cardBorder = Color(0x1AFFFFFF);
  
  static const Color primaryTeal = Color(0xFF00D8D6);
  static const Color emeraldGreen = Color(0xFF05C775);
  static const Color amberGold = Color(0xFFFFC83B);
  static const Color violetPurple = Color(0xFF9955FF);
  static const Color crimsonRed = Color(0xFFFF4757);
  
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);
}

class FluentDecorations {
  static BoxDecoration card({
    Color? borderColor,
    double borderRadius = 16.0,
  }) {
    return BoxDecoration(
      color: FluentColors.cardBackground,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(
        color: borderColor ?? FluentColors.cardBorder,
        width: 1.2,
      ),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withOpacity(0.3),
          blurRadius: 12,
          offset: const Offset(0, 4),
        ),
      ],
    );
  }

  static BoxDecoration glowCard({
    required Color glowColor,
    double borderRadius = 18.0,
    List<Color>? gradientColors,
  }) {
    return BoxDecoration(
      gradient: gradientColors != null
          ? LinearGradient(
              colors: gradientColors,
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            )
          : null,
      color: gradientColors == null ? FluentColors.cardBackground : null,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(
        color: glowColor.withOpacity(0.4),
        width: 1.5,
      ),
      boxShadow: [
        BoxShadow(
          color: glowColor.withOpacity(0.25),
          blurRadius: 16,
          offset: const Offset(0, 4),
        ),
      ],
    );
  }
}

class FluentThemeData {
  static ThemeData get theme {
    return ThemeData.dark().copyWith(
      scaffoldBackgroundColor: FluentColors.background,
      primaryColor: FluentColors.primaryTeal,
      colorScheme: const ColorScheme.dark(
        primary: FluentColors.primaryTeal,
        secondary: FluentColors.emeraldGreen,
        surface: FluentColors.cardBackground,
        background: FluentColors.background,
        error: FluentColors.crimsonRed,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF0F172A),
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 18,
          fontWeight: FontWeight.bold,
        ),
        iconTheme: IconThemeData(color: Colors.white),
      ),
      cardTheme: CardThemeData(
        color: FluentColors.cardBackground,
        elevation: 4,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: FluentColors.cardBorder, width: 1.2),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: FluentColors.primaryTeal,
          foregroundColor: Colors.black,
          elevation: 4,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 15,
          ),
        ),
      ),
    );
  }
}
