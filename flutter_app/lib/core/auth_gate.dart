import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import 'api_client.dart';

class AuthGate extends StatefulWidget {
  final Widget child;
  final Future<void> Function()? onAuthenticated;

  const AuthGate({
    super.key,
    required this.child,
    this.onAuthenticated,
  });

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  static const settingsChannel = MethodChannel('utilitaria/settings');
  bool checking = true;
  bool authenticated = false;

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    final token = await api.accessToken();
    if (token != null) {
      try {
        await api.get('/api/auth/me', useCache: false);
        authenticated = true;
        await widget.onAuthenticated?.call();
        await _rescanAndroidNotifications();
      } on ApiException catch (error) {
        if (error.isUnauthorized) await api.clearAccessToken();
      } catch (_) {
        // Un dispositivo ya activado puede seguir consultando la caché sin red.
        authenticated = true;
      }
    }
    if (mounted) setState(() => checking = false);
  }

  Future<void> _activated() async {
    setState(() => authenticated = true);
    await widget.onAuthenticated?.call();
    await _rescanAndroidNotifications();
  }

  Future<void> _rescanAndroidNotifications() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    try {
      await settingsChannel.invokeMethod('rescanNotifications');
    } catch (_) {
      // El permiso puede no estar concedido todavía; el lector escaneará al conectarse.
    }
  }

  @override
  Widget build(BuildContext context) {
    if (checking) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (authenticated) return widget.child;
    return _ActivationPage(onActivated: _activated);
  }
}

class _ActivationPage extends StatefulWidget {
  final Future<void> Function() onActivated;
  const _ActivationPage({required this.onActivated});

  @override
  State<_ActivationPage> createState() => _ActivationPageState();
}

class _ActivationPageState extends State<_ActivationPage> {
  final code = TextEditingController();
  final name = TextEditingController(text: 'Mi teléfono');
  bool saving = false;
  String? error;

  Future<void> submitActivation() async {
    if (saving || code.text.trim().isEmpty || name.text.trim().isEmpty) return;
    setState(() {
      saving = true;
      error = null;
    });
    try {
      final result = await api.post(
        '/api/auth/enroll',
        {'code': code.text.trim(), 'device_name': name.text.trim()},
        anonymous: true,
      ) as Map<String, dynamic>;
      await api.saveAccessToken(result['access_token'].toString());
      await widget.onActivated();
    } catch (exception) {
      if (mounted) setState(() => error = readableApiError(exception));
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 440),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Icon(Icons.shield_outlined, size: 52),
                    const SizedBox(height: 24),
                    Text('Activar este dispositivo',
                        style: Theme.of(context)
                            .textTheme
                            .headlineMedium
                            ?.copyWith(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 8),
                    const Text(
                      'Introduce el código que te proporcionó el administrador. La clave privada quedará guardada solamente en este dispositivo.',
                    ),
                    const SizedBox(height: 28),
                    TextField(
                      controller: name,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                          labelText: 'Nombre del dispositivo'),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: code,
                      obscureText: true,
                      onSubmitted: (_) => submitActivation(),
                      decoration: const InputDecoration(
                          labelText: 'Código de activación'),
                    ),
                    if (error != null) ...[
                      const SizedBox(height: 12),
                      Text(error!, style: const TextStyle(color: Colors.red)),
                    ],
                    const SizedBox(height: 20),
                    FilledButton.icon(
                      onPressed: saving ? null : submitActivation,
                      icon: saving
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.lock_open_outlined),
                      label: Text(saving ? 'Activando…' : 'Activar'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );

  @override
  void dispose() {
    code.dispose();
    name.dispose();
    super.dispose();
  }
}
