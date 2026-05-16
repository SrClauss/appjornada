import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../shared/models/user_model.dart';
import '../../features/auth/services/auth_service.dart';

class AuthState {
  final UserModel? user;
  final bool isLoading;
  final String? error;

  const AuthState({this.user, this.isLoading = false, this.error});

  AuthState copyWith({UserModel? user, bool? isLoading, String? error}) =>
      AuthState(
        user: user ?? this.user,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState());

  Future<void> login(String email, String pin) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await AuthService.login(email, pin);
      await loadCurrentUser();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }

  Future<void> loadCurrentUser() async {
    final user = await AuthService.getMe();
    state = state.copyWith(user: user, isLoading: false);
  }

  Future<void> logout() async {
    await AuthService.logout();
    state = const AuthState();
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (_) => AuthNotifier(),
);
