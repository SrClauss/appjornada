import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'core/auth/token_storage.dart';
import 'core/auth/auth_provider.dart';
import 'core/gps/gps_background_service.dart';
import 'features/auth/screens/login_screen.dart';
import 'features/home/screens/home_screen.dart';
import 'features/jornada/screens/abrir_jornada_screen.dart';
import 'features/jornada/screens/jornada_ativa_screen.dart';
import 'features/jornada/screens/fechar_jornada_screen.dart';
import 'features/abastecimento/screens/abastecimento_screen.dart';
import 'features/historico/screens/historico_screen.dart';
import 'features/perfil/screens/perfil_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await GpsBackgroundService.initialize();
  runApp(const ProviderScope(child: AppJornada()));
}

final _router = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const _SplashRouter(),
    ),
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: '/home',
      builder: (context, state) => const HomeScreen(),
    ),
    GoRoute(
      path: '/jornada/abrir',
      builder: (context, state) => const AbrirJornadaScreen(),
    ),
    GoRoute(
      path: '/jornada/ativa/:id',
      builder: (context, state) =>
          JornadaAtivaScreen(jornadaId: state.pathParameters['id']!),
    ),
    GoRoute(
      path: '/jornada/fechar/:id',
      builder: (context, state) =>
          FecharJornadaScreen(jornadaId: state.pathParameters['id']!),
    ),
    GoRoute(
      path: '/jornada/abastecimento/:id',
      builder: (context, state) {
        final extra = state.extra as Map<String, dynamic>?;
        return AbastecimentoScreen(
          jornadaId: state.pathParameters['id']!,
          kmAtual: extra?['kmAtual'] as double?,
        );
      },
    ),
    GoRoute(
      path: '/historico',
      builder: (context, state) => const HistoricoScreen(),
    ),
    GoRoute(
      path: '/perfil',
      builder: (context, state) => const PerfilScreen(),
    ),
  ],
);

class AppJornada extends StatelessWidget {
  const AppJornada({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'App Jornada',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1565C0),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      routerConfig: _router,
    );
  }
}

class _SplashRouter extends ConsumerStatefulWidget {
  const _SplashRouter();

  @override
  ConsumerState<_SplashRouter> createState() => _SplashRouterState();
}

class _SplashRouterState extends ConsumerState<_SplashRouter> {
  @override
  void initState() {
    super.initState();
    _checkSession();
  }

  Future<void> _checkSession() async {
    final token = await TokenStorage.readToken();
    if (token == null) {
      if (mounted) context.go('/login');
      return;
    }
    try {
      await ref.read(authProvider.notifier).loadCurrentUser();
      if (mounted) context.go('/home');
    } catch (_) {
      await TokenStorage.deleteToken();
      if (mounted) context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}
