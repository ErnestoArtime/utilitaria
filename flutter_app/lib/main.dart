// Hallmark · pre-emit critique: P5 H5 E4 S4 R5 V4 · mobile utility workbench with catalogue rhythm.
import 'dart:convert';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

const apiBaseUrl = String.fromEnvironment('API_BASE_URL',
    defaultValue: 'https://utilitaria-api.eav-labs.com');
const apiKey = String.fromEnvironment('API_KEY');

@pragma('vm:entry-point')
Future<void> _firebaseBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    statusBarBrightness: Brightness.dark,
    systemNavigationBarColor: AppPalette.canvas,
    systemNavigationBarIconBrightness: Brightness.dark,
  ));
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    try {
      await Firebase.initializeApp();
      FirebaseMessaging.onBackgroundMessage(_firebaseBackgroundHandler);
      _setupPush();
    } catch (error) {
      debugPrint('No se pudo iniciar Firebase: $error');
    }
  }
  runApp(const UtilitariaApp());
}

Future<void> _setupPush() async {
  try {
    await FirebaseMessaging.instance.requestPermission();
    final token = await FirebaseMessaging.instance.getToken();
    if (token != null) {
      await api
          .post('/api/devices/register', {'token': token, 'name': 'Android'});
    }
    FirebaseMessaging.instance.onTokenRefresh.listen((value) {
      api.post('/api/devices/register', {'token': value, 'name': 'Android'});
    });
  } catch (error) {
    debugPrint('No se pudo registrar el dispositivo: $error');
  }
}

class UtilitariaApp extends StatelessWidget {
  const UtilitariaApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Utilitaria',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(
            seedColor: AppPalette.cyan,
            brightness: Brightness.light,
            surface: AppPalette.surface,
          ),
          scaffoldBackgroundColor: AppPalette.canvas,
          cardTheme: const CardThemeData(
            elevation: 0,
            color: AppPalette.surface,
            margin: EdgeInsets.symmetric(vertical: 6),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.all(Radius.circular(22))),
          ),
          navigationBarTheme: NavigationBarThemeData(
            backgroundColor: AppPalette.surface,
            elevation: 0,
            indicatorColor: AppPalette.mint.withValues(alpha: .28),
            indicatorShape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          ),
          inputDecorationTheme: const InputDecorationTheme(
            filled: true,
            fillColor: AppPalette.canvas,
            border: OutlineInputBorder(
                borderRadius: BorderRadius.all(Radius.circular(18)),
                borderSide: BorderSide(color: Color(0x16062a46))),
            enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.all(Radius.circular(18)),
                borderSide: BorderSide(color: Color(0x16062a46))),
            focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.all(Radius.circular(18)),
                borderSide: BorderSide(color: AppPalette.blue, width: 1.5)),
            contentPadding: EdgeInsets.symmetric(horizontal: 18, vertical: 17),
          ),
          dialogTheme: DialogThemeData(
            backgroundColor: AppPalette.surface,
            surfaceTintColor: Colors.transparent,
            insetPadding:
                const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
            titleTextStyle: const TextStyle(
                color: AppPalette.ink,
                fontSize: 23,
                fontWeight: FontWeight.w700),
          ),
          filledButtonTheme: FilledButtonThemeData(
            style: FilledButton.styleFrom(
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(18)),
                padding: const EdgeInsets.symmetric(vertical: 16)),
          ),
        ),
        home: const AppShell(),
      );
}

abstract final class AppPalette {
  static const navy = Color(0xff062a46);
  static const blue = Color(0xff075985);
  static const cyan = Color(0xff08b9d5);
  static const mint = Color(0xff63efc5);
  static const canvas = Color(0xfff3f7f8);
  static const surface = Color(0xffffffff);
  static const ink = Color(0xff102a3a);
}

class ModernAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final String eyebrow;
  final List<Widget>? actions;

  const ModernAppBar({
    super.key,
    required this.title,
    this.eyebrow = 'UTILITARIA',
    this.actions,
  });

  @override
  Size get preferredSize => const Size.fromHeight(86);

  @override
  Widget build(BuildContext context) => AppBar(
        toolbarHeight: 86,
        elevation: 0,
        foregroundColor: Colors.white,
        backgroundColor: Colors.transparent,
        systemOverlayStyle: SystemUiOverlayStyle.light,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(30)),
        ),
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [AppPalette.navy, AppPalette.blue],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.vertical(bottom: Radius.circular(30)),
          ),
        ),
        titleSpacing: 16,
        title: Padding(
          padding: const EdgeInsets.only(left: 12),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(eyebrow,
                style: const TextStyle(
                    fontSize: 10,
                    letterSpacing: 1.8,
                    fontWeight: FontWeight.w700,
                    color: AppPalette.mint)),
            const SizedBox(height: 3),
            Text(title,
                style: const TextStyle(
                    fontSize: 24,
                    height: 1.05,
                    fontWeight: FontWeight.w700,
                    color: Colors.white)),
          ]),
        ),
        actions: actions,
      );
}

Widget headerAction(
        {required IconData icon, required VoidCallback? onPressed}) =>
    Padding(
      padding: const EdgeInsets.only(right: 8),
      child: IconButton.filledTonal(
        tooltip: 'Actualizar ahora',
        onPressed: onPressed,
        style: IconButton.styleFrom(
          foregroundColor: Colors.white,
          backgroundColor: Colors.white.withValues(alpha: .14),
        ),
        icon: Icon(icon),
      ),
    );

class AppShell extends StatefulWidget {
  const AppShell({super.key});
  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int index = 0;
  final pages = const [
    HomePage(),
    NotificationsPage(),
    FinancePage(),
    AlertsPage(),
    MorePage()
  ];

  @override
  Widget build(BuildContext context) => Scaffold(
        body: IndexedStack(index: index, children: pages),
        bottomNavigationBar: SafeArea(
          top: false,
          minimum: const EdgeInsets.fromLTRB(10, 0, 10, 8),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: NavigationBar(
              height: 70,
              selectedIndex: index,
              onDestinationSelected: (value) => setState(() => index = value),
              destinations: const [
                NavigationDestination(
                    icon: Icon(Icons.dashboard_outlined),
                    selectedIcon: Icon(Icons.dashboard),
                    label: 'Inicio'),
                NavigationDestination(
                    icon: Icon(Icons.notifications_none),
                    selectedIcon: Icon(Icons.notifications),
                    label: 'Avisos'),
                NavigationDestination(
                    icon: Icon(Icons.account_balance_wallet_outlined),
                    selectedIcon: Icon(Icons.account_balance_wallet),
                    label: 'Finanzas'),
                NavigationDestination(
                    icon: Icon(Icons.notifications_active_outlined),
                    selectedIcon: Icon(Icons.notifications_active),
                    label: 'Alertas'),
                NavigationDestination(
                    icon: Icon(Icons.more_horiz), label: 'Más'),
              ],
            ),
          ),
        ),
      );
}

class CacheStatus {
  final DateTime? updatedAt;
  final bool offline;
  final bool syncing;
  const CacheStatus(
      {this.updatedAt, this.offline = false, this.syncing = false});
}

class ApiClient {
  final String baseUrl;
  final Duration requestTimeout;
  final http.Client _httpClient;
  final ValueNotifier<int> cacheChanges = ValueNotifier(0);
  final Map<String, CacheStatus> _statuses = {};
  ApiClient(
      {this.baseUrl = apiBaseUrl,
      this.requestTimeout = const Duration(seconds: 4),
      http.Client? httpClient})
      : _httpClient = httpClient ?? http.Client();

  Map<String, String> get headers => {
        if (apiKey.isNotEmpty) 'X-API-Key': apiKey,
      };

  String _cacheKey(String path) =>
      base64Url.encode(utf8.encode(path)).replaceAll('=', '');

  CacheStatus status(String path) => _statuses[path] ?? const CacheStatus();

  void _setStatus(String path, CacheStatus status) {
    _statuses[path] = status;
    cacheChanges.value++;
  }

  Future<dynamic> get(String path) async {
    final preferences = await SharedPreferences.getInstance();
    final key = _cacheKey(path);
    final savedAt = preferences.getInt('api_cache_time_$key');
    _setStatus(
        path,
        CacheStatus(
            updatedAt: savedAt == null
                ? null
                : DateTime.fromMillisecondsSinceEpoch(savedAt),
            syncing: true));
    try {
      final response = await _httpClient
          .get(Uri.parse('$baseUrl$path'), headers: headers)
          .timeout(requestTimeout);
      if (response.statusCode >= 400) {
        throw Exception('API ${response.statusCode}');
      }
      final decoded = jsonDecode(response.body);
      final now = DateTime.now();
      await preferences.setString('api_cache_body_$key', response.body);
      await preferences.setInt(
          'api_cache_time_$key', now.millisecondsSinceEpoch);
      _setStatus(path, CacheStatus(updatedAt: now));
      return decoded;
    } catch (_) {
      final cachedBody = preferences.getString('api_cache_body_$key');
      final cachedAt = preferences.getInt('api_cache_time_$key');
      _setStatus(
          path,
          CacheStatus(
              updatedAt: cachedAt == null
                  ? null
                  : DateTime.fromMillisecondsSinceEpoch(cachedAt),
              offline: true));
      if (cachedBody != null) return jsonDecode(cachedBody);
      rethrow;
    }
  }

  Future<dynamic> post(String path, Map<String, dynamic> body) async {
    final response = await _httpClient
        .post(Uri.parse('$baseUrl$path'),
            headers: {...headers, 'Content-Type': 'application/json'},
            body: jsonEncode(body))
        .timeout(const Duration(seconds: 12));
    if (response.statusCode >= 400) {
      throw Exception('API ${response.statusCode}');
    }
    return jsonDecode(response.body);
  }

  Future<dynamic> patch(String path, Map<String, dynamic> body) async {
    final response = await _httpClient
        .patch(Uri.parse('$baseUrl$path'),
            headers: {...headers, 'Content-Type': 'application/json'},
            body: jsonEncode(body))
        .timeout(const Duration(seconds: 12));
    if (response.statusCode >= 400) {
      throw Exception('API ${response.statusCode}');
    }
    return jsonDecode(response.body);
  }
}

final api = ApiClient();

class SyncStatusBar extends StatelessWidget {
  final List<String> paths;
  final Future<void> Function() onRefresh;
  const SyncStatusBar(
      {super.key, required this.paths, required this.onRefresh});

  String _format(DateTime value) {
    final local = value.toLocal();
    String two(int number) => number.toString().padLeft(2, '0');
    return '${two(local.day)}/${two(local.month)} ${two(local.hour)}:${two(local.minute)}';
  }

  @override
  Widget build(BuildContext context) => ValueListenableBuilder<int>(
      valueListenable: api.cacheChanges,
      builder: (context, _, __) {
        final states = paths.map(api.status).toList();
        final syncing = states.any((item) => item.syncing);
        final offline = states.any((item) => item.offline);
        final dates =
            states.map((item) => item.updatedAt).whereType<DateTime>().toList();
        final updatedAt = dates.isEmpty
            ? null
            : dates
                .reduce((left, right) => left.isBefore(right) ? left : right);
        final color = offline ? Colors.orange : Colors.green;
        final message = syncing
            ? 'Sincronizando…'
            : updatedAt == null
                ? 'Todavía no hay datos guardados'
                : offline
                    ? 'Sin conexión · datos del ${_format(updatedAt)}'
                    : 'Sincronizado ${_format(updatedAt)}';
        return Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.fromLTRB(12, 8, 6, 8),
            decoration: BoxDecoration(
                color: color.withValues(alpha: .10),
                borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              if (syncing)
                const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
              else
                Icon(offline ? Icons.cloud_off : Icons.cloud_done,
                    color: color, size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text(message)),
              IconButton(
                  tooltip: 'Actualizar ahora',
                  onPressed: syncing ? null : onRefresh,
                  icon: const Icon(Icons.refresh))
            ]));
      });
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  double balance = 0;
  List<dynamic> notifications = [];
  bool loading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    refresh();
  }

  Future<void> refresh() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final result = await Future.wait(
          [api.get('/api/balance'), api.get('/api/notifications')]);
      balance = double.tryParse('${(result[0] as Map)['amount']}') ?? 0;
      notifications = result[1] as List<dynamic>;
    } catch (_) {
      error =
          'No se pudo conectar con el servidor. La interfaz está lista, falta configurar la URL de la API.';
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: ModernAppBar(title: 'Tu espacio común', actions: [
          headerAction(icon: Icons.refresh_rounded, onPressed: refresh)
        ]),
        body: RefreshIndicator(
          onRefresh: refresh,
          child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
              children: [
                SyncStatusBar(
                    paths: const ['/api/balance', '/api/notifications'],
                    onRefresh: refresh),
                Text('Panel común',
                    style: Theme.of(context)
                        .textTheme
                        .headlineSmall
                        ?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 16),
                Card(
                    child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Saldo compartido',
                                  style:
                                      Theme.of(context).textTheme.titleMedium),
                              const SizedBox(height: 8),
                              Text('${balance.toStringAsFixed(2)} €',
                                  style: Theme.of(context)
                                      .textTheme
                                      .displaySmall
                                      ?.copyWith(fontWeight: FontWeight.w700)),
                              const SizedBox(height: 8),
                              const Text(
                                  'Incluye ingresos, gastos, préstamos y ajustes.'),
                            ]))),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(
                      child: FilledButton.icon(
                          onPressed: () => _entryDialog(context),
                          icon: const Icon(Icons.add),
                          label: const Text('Movimiento'))),
                  const SizedBox(width: 10),
                  Expanded(
                      child: OutlinedButton.icon(
                          onPressed: () => _entryDialog(context, kind: 'loan'),
                          icon: const Icon(Icons.handshake_outlined),
                          label: const Text('Préstamo'))),
                ]),
                const SizedBox(height: 24),
                Text('Actividad reciente',
                    style: Theme.of(context).textTheme.titleLarge),
                if (loading)
                  const Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(child: CircularProgressIndicator())),
                if (error != null)
                  Card(
                      child: ListTile(
                          leading: const Icon(Icons.cloud_off),
                          title: const Text('API pendiente de configurar'),
                          subtitle: Text(error!))),
                if (!loading && error == null && notifications.isEmpty)
                  const Card(
                      child: ListTile(
                          leading: Icon(Icons.notifications_none),
                          title: Text('Sin notificaciones todavía'),
                          subtitle: Text(
                              'Activa el acceso a notificaciones desde Más.'))),
                ...notifications.take(5).map((item) =>
                    NotificationTile(data: item as Map<String, dynamic>)),
              ]),
        ),
      );

  Future<void> _entryDialog(BuildContext context,
      {String kind = 'income'}) async {
    final amount = TextEditingController();
    final description = TextEditingController();
    String category = 'other';
    String member = 'shared';
    await showDialog(
        context: context,
        builder: (_) => StatefulBuilder(
            builder: (context, setDialog) => AlertDialog(
                  title: Text(kind == 'loan'
                      ? 'Registrar préstamo'
                      : 'Registrar movimiento'),
                  content: SingleChildScrollView(
                      child: Column(children: [
                    TextField(
                        controller: amount,
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                        decoration: const InputDecoration(
                            labelText: 'Importe', prefixText: '€ ')),
                    TextField(
                        controller: description,
                        decoration:
                            const InputDecoration(labelText: 'Descripción')),
                    DropdownButtonFormField<String>(
                        initialValue: category,
                        decoration:
                            const InputDecoration(labelText: 'Categoría'),
                        items: const [
                          DropdownMenuItem(
                              value: 'income', child: Text('Ingreso')),
                          DropdownMenuItem(
                              value: 'expense', child: Text('Gasto')),
                          DropdownMenuItem(
                              value: 'transfer', child: Text('Transferencia')),
                          DropdownMenuItem(
                              value: 'business', child: Text('Negocio')),
                          DropdownMenuItem(value: 'other', child: Text('Otro'))
                        ],
                        onChanged: (v) => setDialog(() => category = v!)),
                    DropdownButtonFormField<String>(
                        initialValue: member,
                        decoration: const InputDecoration(labelText: 'Persona'),
                        items: const [
                          DropdownMenuItem(
                              value: 'shared', child: Text('Común')),
                          DropdownMenuItem(value: 'me', child: Text('Yo')),
                          DropdownMenuItem(
                              value: 'cousin', child: Text('Mi primo'))
                        ],
                        onChanged: (v) => setDialog(() => member = v!)),
                  ])),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Cancelar')),
                    FilledButton(
                        onPressed: () async {
                          final value =
                              double.tryParse(amount.text.replaceAll(',', '.'));
                          if (value == null ||
                              description.text.trim().isEmpty) {
                            return;
                          }
                          await api.post('/api/balance/entries', {
                            'amount': {'expense', 'business', 'transfer'}
                                    .contains(category)
                                ? -value
                                : value,
                            'description': description.text.trim(),
                            'kind': category == 'transfer' ? 'transfer' : kind,
                            'category': category,
                            'member': member,
                            'is_business': category == 'business'
                          });
                          if (context.mounted) Navigator.pop(context);
                        },
                        child: const Text('Guardar'))
                  ],
                )));
    refresh();
  }
}

class NotificationsPage extends StatefulWidget {
  const NotificationsPage({super.key});
  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  List<dynamic> items = [];
  String filter = 'all';
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final data = await api.get('/api/notifications');
      if (mounted) setState(() => items = data as List<dynamic>);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final visible = items
        .where((raw) => filter == 'all' || (raw as Map)['category'] == filter)
        .toList();
    return Scaffold(
        appBar: ModernAppBar(title: 'Notificaciones', actions: [
          headerAction(icon: Icons.refresh_rounded, onPressed: load)
        ]),
        body: Column(children: [
          Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
              child: SyncStatusBar(
                  paths: const ['/api/notifications'], onRefresh: load)),
          SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.all(12),
              child: Row(
                  children: ['all', 'business', 'income', 'private']
                      .map((value) => Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: ChoiceChip(
                              label: Text(value == 'all'
                                  ? 'Todas'
                                  : value == 'business'
                                      ? 'Negocio'
                                      : value == 'income'
                                          ? 'Ingresos'
                                          : 'Privadas'),
                              selected: filter == value,
                              onSelected: (_) =>
                                  setState(() => filter = value))))
                      .toList())),
          Expanded(
              child: RefreshIndicator(
                  onRefresh: load,
                  child: visible.isEmpty
                      ? ListView(children: const [
                          SizedBox(
                              height: 360,
                              child: EmptyState(
                                  icon: Icons.notifications_none,
                                  title: 'No hay notificaciones',
                                  message:
                                      'Cuando el lector de Android reciba una notificación aparecerá aquí.'))
                        ])
                      : ListView.builder(
                          physics: const AlwaysScrollableScrollPhysics(),
                          itemCount: visible.length,
                          itemBuilder: (_, i) => NotificationTile(
                              data: visible[i] as Map<String, dynamic>,
                              onBusiness: () => _mark(visible[i]['id'], true),
                              onPrivate: () =>
                                  _mark(visible[i]['id'], false))))),
        ]));
  }

  Future<void> _mark(dynamic id, bool business) async {
    await api.patch('/api/notifications/$id', {
      'is_business': business,
      'category': business ? 'business' : 'private',
      'shared_with_family': business
    });
    load();
  }
}

class FinancePage extends StatefulWidget {
  const FinancePage({super.key});
  @override
  State<FinancePage> createState() => _FinancePageState();
}

class _FinancePageState extends State<FinancePage> {
  Map<String, dynamic>? summary;
  List<dynamic> entries = [];
  String filter = 'all';
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final data = await Future.wait(
          [api.get('/api/finance/summary'), api.get('/api/balance/entries')]);
      if (mounted) {
        setState(() {
          summary = data[0] as Map<String, dynamic>;
          entries = data[1] as List<dynamic>;
        });
      }
    } catch (_) {}
  }

  String _dateTime(dynamic raw) {
    final value = DateTime.tryParse('$raw')?.toLocal();
    if (value == null) return 'Fecha desconocida';
    String two(int number) => number.toString().padLeft(2, '0');
    return '${two(value.day)}/${two(value.month)}/${value.year} · '
        '${two(value.hour)}:${two(value.minute)}';
  }

  double _memberBalance(String member) =>
      double.tryParse('${(summary?['by_member'] as Map?)?[member] ?? 0}') ?? 0;

  String _money(dynamic raw) =>
      (double.tryParse('$raw') ?? 0).toStringAsFixed(2);

  String _memberLabel(String? member) => switch (member) {
        'me' => 'Mío',
        'cousin' => 'Mi primo',
        _ => 'Común / sin asignar',
      };

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: ModernAppBar(title: 'Finanzas comunes', actions: [
        headerAction(icon: Icons.refresh_rounded, onPressed: load)
      ]),
      body: RefreshIndicator(
          onRefresh: load,
          child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              children: [
                SyncStatusBar(paths: const [
                  '/api/finance/summary',
                  '/api/balance/entries'
                ], onRefresh: load),
                Text('Dinero de los dos',
                    style: Theme.of(context)
                        .textTheme
                        .headlineSmall
                        ?.copyWith(fontWeight: FontWeight.w700)),
                const Text(
                    'Cada movimiento debe indicar de quién es el dinero.'),
                const SizedBox(height: 16),
                _MetricCard(
                    label: 'Saldo común total',
                    value: '${_money(summary?['balance'])} €',
                    icon: Icons.account_balance_wallet),
                Row(children: [
                  Expanded(
                      child: _MemberCard(
                          label: 'Mi saldo',
                          value: _memberBalance('me'),
                          icon: Icons.person_outline,
                          selected: filter == 'me',
                          onTap: () => setState(() => filter = 'me'))),
                  const SizedBox(width: 8),
                  Expanded(
                      child: _MemberCard(
                          label: 'Saldo de mi primo',
                          value: _memberBalance('cousin'),
                          icon: Icons.person_2_outlined,
                          selected: filter == 'cousin',
                          onTap: () => setState(() => filter = 'cousin'))),
                ]),
                _MemberCard(
                    label: 'Pendiente de asignar',
                    value: _memberBalance('shared'),
                    icon: Icons.group_outlined,
                    selected: filter == 'shared',
                    onTap: () => setState(() => filter = 'shared')),
                Card(
                    child: ListTile(
                        leading: const Icon(Icons.storefront),
                        title: const Text('Compras e inversión'),
                        subtitle: const Text('No cuentan para el saldo común'),
                        trailing: Text('${_money(summary?['business'])} €'),
                        onTap: () => setState(() => filter = 'business'))),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(
                      child: FilledButton.icon(
                          onPressed: () => _movementDialog(),
                          icon: const Icon(Icons.add),
                          label: const Text('Movimiento'))),
                  const SizedBox(width: 8),
                  Expanded(
                      child: OutlinedButton.icon(
                          onPressed: () => _movementDialog(
                              initialKind: 'expense',
                              initialMember: 'cousin',
                              title: 'Entrega a mi primo'),
                          icon: const Icon(Icons.payments_outlined),
                          label: const Text('Entregar/retirar'))),
                ]),
                const SizedBox(height: 20),
                Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Detalle de movimientos',
                          style: Theme.of(context).textTheme.titleLarge),
                      if (filter != 'all')
                        TextButton(
                            onPressed: () => setState(() => filter = 'all'),
                            child: const Text('Ver todos'))
                    ]),
                const SizedBox(height: 8),
                if (entries.isEmpty)
                  const ListTile(
                      leading: Icon(Icons.receipt_long),
                      title: Text('Sin movimientos registrados')),
                ...entries.where((raw) {
                  final entry = raw as Map<String, dynamic>;
                  if (filter == 'all') return true;
                  if (filter == 'business') return entry['is_business'] == true;
                  return entry['is_business'] != true &&
                      entry['member'] == filter;
                }).map((raw) {
                  final entry = raw as Map<String, dynamic>;
                  final business = entry['is_business'] == true;
                  return _MovementCard(
                      entry: entry,
                      dateLabel: _dateTime(entry['created_at']),
                      ownerLabel: business
                          ? 'Negocio · fuera del saldo común'
                          : _memberLabel('${entry['member']}'),
                      onTap: () => _editMovement(entry));
                }),
              ])));

  Future<void> _movementDialog(
      {String initialKind = 'income',
      String initialMember = 'shared',
      String title = 'Nuevo movimiento'}) async {
    final amount = TextEditingController();
    final description = TextEditingController();
    String kind = initialKind;
    String member = initialMember;
    bool business = false;
    await showDialog(
        context: context,
        builder: (_) => StatefulBuilder(
            builder: (context, setDialog) => AlertDialog(
                  title: Text(title),
                  content: SingleChildScrollView(
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                    DropdownButtonFormField<String>(
                        initialValue: kind,
                        decoration: const InputDecoration(
                            labelText: 'Tipo de movimiento'),
                        items: const [
                          DropdownMenuItem(
                              value: 'income', child: Text('Ingreso')),
                          DropdownMenuItem(
                              value: 'expense', child: Text('Gasto')),
                          DropdownMenuItem(
                              value: 'transfer', child: Text('Transferencia')),
                        ],
                        onChanged: (value) => setDialog(() => kind = value!)),
                    const SizedBox(height: 12),
                    TextField(
                        controller: amount,
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                        decoration: const InputDecoration(
                            labelText: 'Importe', prefixText: '€ ')),
                    const SizedBox(height: 12),
                    TextField(
                        controller: description,
                        decoration:
                            const InputDecoration(labelText: 'Descripción')),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                        initialValue: member,
                        decoration:
                            const InputDecoration(labelText: '¿De quién es?'),
                        items: const [
                          DropdownMenuItem(value: 'me', child: Text('Mío')),
                          DropdownMenuItem(
                              value: 'cousin', child: Text('Mi primo')),
                          DropdownMenuItem(
                              value: 'shared',
                              child: Text('Común / sin asignar'))
                        ],
                        onChanged: (value) => setDialog(() => member = value!)),
                    const SizedBox(height: 8),
                    SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        value: business,
                        title: const Text('Compra o inversión'),
                        subtitle: const Text('Excluir del saldo común'),
                        onChanged: (value) =>
                            setDialog(() => business = value)),
                  ])),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Cancelar')),
                    FilledButton(
                        onPressed: () async {
                          final value = double.tryParse(
                              amount.text.trim().replaceAll(',', '.'));
                          if (value == null ||
                              value <= 0 ||
                              description.text.trim().isEmpty) {
                            return;
                          }
                          await api.post('/api/balance/entries', {
                            'amount': kind == 'income' ? value : -value,
                            'description': description.text.trim(),
                            'kind': kind,
                            'category': business
                                ? 'business'
                                : kind == 'income'
                                    ? 'income'
                                    : kind == 'transfer'
                                        ? 'transfer'
                                        : 'expense',
                            'member': member,
                            'currency': 'EUR',
                            'is_business': business
                          });
                          if (context.mounted) Navigator.pop(context);
                          load();
                        },
                        child: const Text('Guardar'))
                  ],
                )));
  }

  Future<void> _editMovement(Map<String, dynamic> entry) async {
    String member = '${entry['member'] ?? 'shared'}';
    bool business = entry['is_business'] == true;
    final description = TextEditingController(text: '${entry['description']}');
    await showDialog(
        context: context,
        builder: (_) => StatefulBuilder(
            builder: (context, setDialog) => AlertDialog(
                  title: const Text('Detallar movimiento'),
                  content: SingleChildScrollView(
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                    TextField(
                        controller: description,
                        decoration:
                            const InputDecoration(labelText: 'Descripción')),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                        initialValue: member,
                        decoration:
                            const InputDecoration(labelText: '¿De quién es?'),
                        items: const [
                          DropdownMenuItem(value: 'me', child: Text('Mío')),
                          DropdownMenuItem(
                              value: 'cousin', child: Text('Mi primo')),
                          DropdownMenuItem(
                              value: 'shared',
                              child: Text('Común / sin asignar'))
                        ],
                        onChanged: (value) => setDialog(() => member = value!)),
                    const SizedBox(height: 8),
                    SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        value: business,
                        title: const Text('Compra o inversión'),
                        subtitle: const Text('Excluir del saldo común'),
                        onChanged: (value) =>
                            setDialog(() => business = value)),
                  ])),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Cancelar')),
                    FilledButton(
                        onPressed: () async {
                          await api
                              .patch('/api/balance/entries/${entry['id']}', {
                            'description': description.text.trim(),
                            'member': member,
                            'is_business': business,
                            'category': business
                                ? 'business'
                                : (double.tryParse('${entry['amount']}') ??
                                            0) >=
                                        0
                                    ? 'income'
                                    : 'expense'
                          });
                          if (context.mounted) Navigator.pop(context);
                          load();
                        },
                        child: const Text('Guardar'))
                  ],
                )));
  }
}

class _MovementCard extends StatelessWidget {
  final Map<String, dynamic> entry;
  final String dateLabel;
  final String ownerLabel;
  final VoidCallback onTap;

  const _MovementCard({
    required this.entry,
    required this.dateLabel,
    required this.ownerLabel,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final amount = double.tryParse('${entry['amount']}') ?? 0;
    final incoming = amount >= 0;
    final accent = incoming ? const Color(0xff3f9d63) : const Color(0xffb34a4a);
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 15),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 44,
              height: 44,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: incoming
                    ? AppPalette.cyan.withValues(alpha: .22)
                    : const Color(0xffffe2dc),
                borderRadius: BorderRadius.circular(15),
              ),
              child: Icon(
                  incoming
                      ? Icons.south_west_rounded
                      : Icons.north_east_rounded,
                  color: AppPalette.navy),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${entry['description']}',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 16, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 5),
                    Text(dateLabel,
                        style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 2),
                    Text(ownerLabel,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppPalette.blue,
                            fontWeight: FontWeight.w600)),
                  ]),
            ),
            const SizedBox(width: 10),
            Text(
                '${incoming ? '+' : ''}${amount.toStringAsFixed(2)} ${entry['currency'] ?? 'EUR'}',
                textAlign: TextAlign.end,
                style: TextStyle(color: accent, fontWeight: FontWeight.w800)),
          ]),
        ),
      ),
    );
  }
}

class _MemberCard extends StatelessWidget {
  final String label;
  final double value;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;
  const _MemberCard(
      {required this.label,
      required this.value,
      required this.icon,
      required this.selected,
      required this.onTap});

  @override
  Widget build(BuildContext context) => Card(
      color: selected ? Theme.of(context).colorScheme.primaryContainer : null,
      child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: onTap,
          child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(icon),
                    const SizedBox(height: 10),
                    Text(label),
                    const SizedBox(height: 4),
                    Text('${value.toStringAsFixed(2)} €',
                        style: Theme.of(context)
                            .textTheme
                            .titleLarge
                            ?.copyWith(fontWeight: FontWeight.bold))
                  ]))));
}

class AlertsPage extends StatefulWidget {
  const AlertsPage({super.key});
  @override
  State<AlertsPage> createState() => _AlertsPageState();
}

class _AlertsPageState extends State<AlertsPage> {
  Map<String, dynamic>? data;
  bool loading = true;
  bool checking = false;
  String? error;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    if (mounted) setState(() => error = null);
    try {
      final result = await api.get('/api/alerts');
      if (mounted) setState(() => data = result as Map<String, dynamic>);
    } catch (_) {
      if (mounted) setState(() => error = 'No se pudieron cargar las alertas.');
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> checkNow() async {
    setState(() => checking = true);
    try {
      await api.post('/api/alerts/check', {});
      await load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Comprobación terminada')));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('No se pudo comprobar ahora')));
      }
    } finally {
      if (mounted) setState(() => checking = false);
    }
  }

  Color _statusColor(String status) => switch (status) {
        'available' || 'active' => Colors.green,
        'unavailable' => Colors.red,
        'degraded' => Colors.orange,
        _ => Colors.grey,
      };

  String _date(dynamic value) {
    final parsed = DateTime.tryParse('$value')?.toLocal();
    if (parsed == null) return 'Pendiente de comprobar';
    return '${parsed.day.toString().padLeft(2, '0')}/${parsed.month.toString().padLeft(2, '0')} '
        '${parsed.hour.toString().padLeft(2, '0')}:${parsed.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final groups = data?['groups'] as List<dynamic>? ?? [];
    final events = data?['events'] as List<dynamic>? ?? [];
    return Scaffold(
        appBar: ModernAppBar(title: 'Alertas', actions: [
          headerAction(
              icon:
                  checking ? Icons.hourglass_top_rounded : Icons.radar_rounded,
              onPressed: checking ? null : checkNow)
        ]),
        body: loading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: load,
                child: ListView(padding: const EdgeInsets.all(16), children: [
                  SyncStatusBar(paths: const ['/api/alerts'], onRefresh: load),
                  Text('Disponibilidad vigilada',
                      style: Theme.of(context)
                          .textTheme
                          .headlineSmall
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  const Text(
                      'Te avisaremos cuando cambie el gas o algún dato de TiendaSolar.'),
                  if (error != null) ...[
                    const SizedBox(height: 12),
                    Text(error!, style: const TextStyle(color: Colors.red)),
                  ],
                  const SizedBox(height: 16),
                  ...groups.map((group) {
                    final items = group['items'] as List<dynamic>? ?? [];
                    final isGas = group['id'] == 'gas';
                    return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(children: [
                            Icon(isGas
                                ? Icons.local_fire_department_outlined
                                : Icons.solar_power_outlined),
                            const SizedBox(width: 8),
                            Text('${group['label']}',
                                style: Theme.of(context).textTheme.titleLarge)
                          ]),
                          const SizedBox(height: 8),
                          ...items.map((item) {
                            final details = item['details'] as Map? ?? {};
                            return Card(
                                child: Padding(
                                    padding: const EdgeInsets.all(14),
                                    child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Row(children: [
                                            Expanded(
                                                child: Text('${item['name']}',
                                                    style: Theme.of(context)
                                                        .textTheme
                                                        .titleMedium
                                                        ?.copyWith(
                                                            fontWeight:
                                                                FontWeight
                                                                    .bold))),
                                            Container(
                                                padding: const EdgeInsets
                                                    .symmetric(
                                                    horizontal: 10,
                                                    vertical: 5),
                                                decoration: BoxDecoration(
                                                    color: _statusColor(
                                                            '${item['status']}')
                                                        .withValues(alpha: .14),
                                                    borderRadius:
                                                        BorderRadius.circular(
                                                            20)),
                                                child: Text(
                                                    '${item['status_label']}',
                                                    style: TextStyle(
                                                        color: _statusColor(
                                                            '${item['status']}'),
                                                        fontWeight:
                                                            FontWeight.w600)))
                                          ]),
                                          if (item['price'] != null) ...[
                                            const SizedBox(height: 8),
                                            Text('Precio: ${item['price']}',
                                                style: Theme.of(context)
                                                    .textTheme
                                                    .titleMedium)
                                          ],
                                          if (details['quantity'] != null) ...[
                                            const SizedBox(height: 6),
                                            Text(
                                                'Cantidad: ${details['quantity']} unidades')
                                          ],
                                          if (details['products'] != null) ...[
                                            const SizedBox(height: 8),
                                            Text(
                                                '${details['products']} productos · ${details['available_locations']} disponibilidades')
                                          ],
                                          const SizedBox(height: 8),
                                          Text(
                                              'Última revisión: ${_date(item['last_checked_at'])}',
                                              style: Theme.of(context)
                                                  .textTheme
                                                  .bodySmall),
                                          if (item['last_error'] != null)
                                            Text('${item['last_error']}',
                                                style: const TextStyle(
                                                    color: Colors.red)),
                                          const SizedBox(height: 6),
                                          Align(
                                              alignment: Alignment.centerRight,
                                              child: TextButton.icon(
                                                  onPressed: () {
                                                    if (isGas) {
                                                      launchUrl(
                                                          Uri.parse(
                                                              '${item['url']}'),
                                                          mode: LaunchMode
                                                              .externalApplication);
                                                    } else {
                                                      Navigator.push(
                                                          context,
                                                          MaterialPageRoute(
                                                              builder: (_) =>
                                                                  const SolarCatalogPage()));
                                                    }
                                                  },
                                                  icon: Icon(isGas
                                                      ? Icons.open_in_new
                                                      : Icons.grid_view),
                                                  label: Text(isGas
                                                      ? 'Abrir producto'
                                                      : 'Ver catálogo')))
                                        ])));
                          }),
                          const SizedBox(height: 18),
                        ]);
                  }),
                  Text('Cambios recientes',
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 8),
                  if (events.isEmpty)
                    const Card(
                        child: ListTile(
                            leading: Icon(Icons.history),
                            title: Text('Todavía no hay cambios'),
                            subtitle: Text(
                                'El estado inicial ya está guardado. Aquí aparecerán las variaciones.'))),
                  ...events.map((event) => ListTile(
                      leading: const Icon(Icons.notifications_active_outlined),
                      title: Text('${event['title']}'),
                      subtitle: Text(
                          '${event['message']} · ${_date(event['created_at'])}'))),
                ])));
  }
}

class SolarCatalogPage extends StatefulWidget {
  const SolarCatalogPage({super.key});
  @override
  State<SolarCatalogPage> createState() => _SolarCatalogPageState();
}

class _SolarCatalogPageState extends State<SolarCatalogPage> {
  Map<String, dynamic>? catalog;
  String query = '';
  String location = 'all';
  String status = 'all';
  String category = 'all';
  bool loading = true;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final result = await api.get('/api/solar/catalog');
      if (mounted) setState(() => catalog = result as Map<String, dynamic>);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  List<dynamic> get _products {
    final source = catalog?['products'] as List<dynamic>? ?? [];
    return source
        .where((raw) {
          final product = raw as Map;
          final name = '${product['name']}'.toLowerCase();
          final categoryMatches =
              category == 'all' || product['category'] == category;
          final locations = product['locations'] as Map? ?? {};
          final selectedLocations =
              location == 'all' ? ['miramar', 'siboney'] : [location];
          final locationMatches =
              selectedLocations.any((loc) => locations.containsKey(loc));
          final statusMatches = status == 'all' ||
              selectedLocations.any((loc) {
                final item = locations[loc] as Map?;
                return item?['state'] == status;
              });
          return categoryMatches &&
              locationMatches &&
              statusMatches &&
              name.contains(query.toLowerCase());
        })
        .take(150)
        .toList();
  }

  void clearFilters() => setState(() {
        query = '';
        location = 'all';
        status = 'all';
        category = 'all';
      });

  String _statusLabel(String value) => switch (value) {
        'available' => 'Disponible',
        'coming_soon' => 'Próxima disponibilidad',
        'out_of_stock' => 'Agotado',
        _ => 'Todos los estados',
      };

  @override
  Widget build(BuildContext context) {
    final products = _products;
    final summary = catalog?['summary'] as Map? ?? {};
    final categories = catalog?['categories'] as List<dynamic>? ?? [];
    return Scaffold(
        appBar: ModernAppBar(
            title: 'TiendaSolar',
            eyebrow: 'ALERTAS',
            actions: [
              headerAction(icon: Icons.refresh_rounded, onPressed: load)
            ]),
        body: loading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: load,
                child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    children: [
                      SyncStatusBar(
                          paths: const ['/api/solar/catalog'], onRefresh: load),
                      const SizedBox(height: 4),
                      Text('Inventario comparado',
                          style: Theme.of(context)
                              .textTheme
                              .labelLarge
                              ?.copyWith(
                                  color: AppPalette.blue,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 1.2)),
                      const SizedBox(height: 5),
                      Text('Toda la tienda. Dos ubicaciones.',
                          style: Theme.of(context)
                              .textTheme
                              .headlineSmall
                              ?.copyWith(fontWeight: FontWeight.w800)),
                      const SizedBox(height: 5),
                      Text(
                          'Compara Miramar y Siboney y abre el artículo original cuando quieras revisar sus detalles.',
                          style: Theme.of(context).textTheme.bodyMedium),
                      const SizedBox(height: 18),
                      Row(children: [
                        Expanded(
                            child: _CatalogStat(
                                value: '${summary['products'] ?? '—'}',
                                label: 'artículos')),
                        const SizedBox(width: 8),
                        Expanded(
                            child: _CatalogStat(
                                value: '${summary['availableMiramar'] ?? '—'}',
                                label: 'Miramar')),
                        const SizedBox(width: 8),
                        Expanded(
                            child: _CatalogStat(
                                value: '${summary['availableSiboney'] ?? '—'}',
                                label: 'Siboney')),
                      ]),
                      const SizedBox(height: 18),
                      TextField(
                          decoration: const InputDecoration(
                              prefixIcon: Icon(Icons.search_rounded),
                              labelText: 'Buscar un artículo'),
                          onChanged: (value) => setState(() => query = value)),
                      const SizedBox(height: 12),
                      Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('Filtros',
                                style: Theme.of(context)
                                    .textTheme
                                    .titleMedium
                                    ?.copyWith(fontWeight: FontWeight.w700)),
                            TextButton(
                                onPressed: clearFilters,
                                child: const Text('Limpiar')),
                          ]),
                      DropdownButtonFormField<String>(
                          initialValue: location,
                          decoration:
                              const InputDecoration(labelText: 'Ubicación'),
                          items: const [
                            DropdownMenuItem(
                                value: 'all', child: Text('Miramar y Siboney')),
                            DropdownMenuItem(
                                value: 'miramar', child: Text('Miramar')),
                            DropdownMenuItem(
                                value: 'siboney', child: Text('Siboney')),
                          ],
                          onChanged: (value) =>
                              setState(() => location = value!)),
                      const SizedBox(height: 10),
                      DropdownButtonFormField<String>(
                          initialValue: status,
                          decoration:
                              const InputDecoration(labelText: 'Estado'),
                          items: const [
                            DropdownMenuItem(
                                value: 'all', child: Text('Todos los estados')),
                            DropdownMenuItem(
                                value: 'available', child: Text('Disponible')),
                            DropdownMenuItem(
                                value: 'coming_soon',
                                child: Text('Próxima disponibilidad')),
                            DropdownMenuItem(
                                value: 'out_of_stock', child: Text('Agotado')),
                          ],
                          onChanged: (value) =>
                              setState(() => status = value!)),
                      const SizedBox(height: 10),
                      DropdownButtonFormField<String>(
                          initialValue: category,
                          decoration:
                              const InputDecoration(labelText: 'Categoría'),
                          items: [
                            const DropdownMenuItem(
                                value: 'all',
                                child: Text('Todas las categorías')),
                            ...categories.map((item) => DropdownMenuItem(
                                value: '${item['id']}',
                                child: Text('${item['label']}'))),
                          ],
                          onChanged: (value) =>
                              setState(() => category = value!)),
                      const SizedBox(height: 18),
                      Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('${products.length} resultados',
                                style: Theme.of(context)
                                    .textTheme
                                    .titleLarge
                                    ?.copyWith(fontWeight: FontWeight.w800)),
                            Text(_statusLabel(status),
                                style: Theme.of(context).textTheme.bodySmall),
                          ]),
                      const SizedBox(height: 8),
                      if (products.isEmpty)
                        const Card(
                            child: ListTile(
                                leading: Icon(Icons.search_off_rounded),
                                title: Text('No encontramos artículos'),
                                subtitle: Text(
                                    'Prueba otra palabra, categoría o ubicación.'))),
                      ...products.map((product) =>
                          _CatalogProductCard(product: product as Map)),
                    ])));
  }
}

class _CatalogStat extends StatelessWidget {
  final String value;
  final String label;
  const _CatalogStat({required this.value, required this.label});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.fromLTRB(12, 14, 8, 13),
        decoration: BoxDecoration(
            color: AppPalette.surface, borderRadius: BorderRadius.circular(18)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(value,
              style:
                  const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
          const SizedBox(height: 3),
          Text(label, style: Theme.of(context).textTheme.bodySmall),
        ]),
      );
}

class _CatalogProductCard extends StatelessWidget {
  final Map product;
  const _CatalogProductCard({required this.product});

  Widget _location(BuildContext context, String key, String label) {
    final locations = product['locations'] as Map? ?? {};
    final data = locations[key] as Map?;
    final state = '${data?['state'] ?? 'unavailable'}';
    final available = data?['available'] == true;
    final color = state == 'available'
        ? const Color(0xff3f9d63)
        : state == 'coming_soon'
            ? const Color(0xffc28522)
            : Theme.of(context).colorScheme.outline;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
            color: AppPalette.canvas, borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label,
              style:
                  const TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text('${data?['label'] ?? 'No listado'}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                  color: color, fontSize: 11, fontWeight: FontWeight.w700)),
          if (available && data?['quantity'] != null)
            Text('${data?['quantity']} unidades',
                style: Theme.of(context).textTheme.bodySmall),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final prices = (product['prices'] as Map? ?? {}).values.toSet().join(' · ');
    final imageUrl = '${product['imageUrl'] ?? ''}';
    final proxiedImage = imageUrl.isEmpty
        ? ''
        : '$apiBaseUrl/api/solar/image?url=${Uri.encodeQueryComponent(imageUrl)}';
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          AspectRatio(
            aspectRatio: 1.25,
            child: Container(
              decoration: BoxDecoration(
                  color: AppPalette.canvas,
                  borderRadius: BorderRadius.circular(18)),
              padding: const EdgeInsets.all(14),
              child: Image.network(proxiedImage,
                  headers: {'X-API-Key': apiKey},
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) => const Icon(
                      Icons.solar_power_rounded,
                      size: 44,
                      color: AppPalette.blue)),
            ),
          ),
          const SizedBox(height: 13),
          Text('${product['categoryLabel'] ?? 'Sin categoría'}',
              style: const TextStyle(
                  color: AppPalette.blue,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: .5)),
          const SizedBox(height: 5),
          Text('${product['name']}',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style:
                  const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
          const SizedBox(height: 5),
          Text(prices.isEmpty ? 'Precio no indicado' : prices,
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 12),
          Row(children: [
            _location(context, 'miramar', 'Miramar'),
            const SizedBox(width: 8),
            _location(context, 'siboney', 'Siboney'),
          ]),
          const SizedBox(height: 8),
          Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                  onPressed: () => launchUrl(Uri.parse('${product['url']}'),
                      mode: LaunchMode.externalApplication),
                  icon: const Icon(Icons.open_in_new_rounded, size: 17),
                  label: const Text('Ver artículo'))),
        ]),
      ),
    );
  }
}

class MorePage extends StatefulWidget {
  const MorePage({super.key});
  @override
  State<MorePage> createState() => _MorePageState();
}

class _MorePageState extends State<MorePage> with WidgetsBindingObserver {
  static const settingsChannel = MethodChannel('utilitaria/settings');
  bool? notificationAccess;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _refreshAccess();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _refreshAccess();
  }

  Future<void> _refreshAccess() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    try {
      final enabled = await settingsChannel
          .invokeMethod<bool>('isNotificationAccessGranted');
      if (mounted) setState(() => notificationAccess = enabled ?? false);
    } catch (_) {
      if (mounted) setState(() => notificationAccess = false);
    }
  }

  Future<void> _openNotificationAccess() async {
    try {
      await settingsChannel.invokeMethod('openNotificationAccess');
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('No se pudieron abrir los ajustes de Android.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: const ModernAppBar(title: 'Más opciones'),
      body: ListView(children: [
        const ListTile(
            title: Text('Configuración'),
            subtitle: Text('Privacidad, dispositivos y preferencias')),
        const Divider(),
        ListTile(
            leading: const Icon(Icons.notifications_active_outlined),
            title: Text(notificationAccess == true
                ? 'Lector de notificaciones activo'
                : 'Activar lector de notificaciones'),
            subtitle: Text(notificationAccess == true
                ? 'Utilitaria puede registrar los avisos bancarios'
                : 'Toca aquí para abrir el permiso exacto en Android'),
            trailing: Icon(
                notificationAccess == true
                    ? Icons.check_circle
                    : Icons.chevron_right,
                color: notificationAccess == true ? Colors.green : null),
            onTap: _openNotificationAccess),
        ListTile(
            leading: const Icon(Icons.currency_exchange),
            title: const Text('Tasas elTOQUE'),
            subtitle: const Text('USD, EUR, MLC y criptomonedas'),
            onTap: () => Navigator.push(
                context, MaterialPageRoute(builder: (_) => const RatesPage()))),
        ListTile(
            leading: const Icon(Icons.filter_alt_outlined),
            title: const Text('Filtros de privacidad'),
            subtitle: const Text('Decide qué avisos se comparten con tu primo'),
            onTap: () => _showRules(context)),
        ListTile(
            leading: const Icon(Icons.send_outlined),
            title: const Text('WhatsApp / OpenWA'),
            subtitle: const Text('Destinatarios, avisos y prueba de envío'),
            onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (_) => const WhatsAppSettingsPage()))),
      ]));

  void _showRules(BuildContext context) => Navigator.push(
      context, MaterialPageRoute(builder: (_) => const RulesPage()));
}

class WhatsAppSettingsPage extends StatefulWidget {
  const WhatsAppSettingsPage({super.key});

  @override
  State<WhatsAppSettingsPage> createState() => _WhatsAppSettingsPageState();
}

class _WhatsAppSettingsPageState extends State<WhatsAppSettingsPage> {
  final recipientsController = TextEditingController();
  bool enabled = true;
  bool transferReceived = true;
  bool transferSent = true;
  bool balanceChanges = true;
  bool loading = true;
  bool saving = false;

  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  void dispose() {
    recipientsController.dispose();
    super.dispose();
  }

  Future<void> load() async {
    try {
      final data = Map<String, dynamic>.from(
          await api.get('/api/whatsapp/config') as Map);
      final values = data['recipients'] as List? ?? const [];
      recipientsController.text = values.join('\n');
      if (mounted) {
        setState(() {
          enabled = data['enabled'] == true;
          transferReceived = data['transfer_received'] != false;
          transferSent = data['transfer_sent'] != false;
          balanceChanges = data['balance_changes'] != false;
          loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => loading = false);
    }
  }

  List<String> get _recipients => recipientsController.text
      .split(RegExp(r'[\n,]'))
      .map((value) => value.trim())
      .where((value) => value.isNotEmpty)
      .toList();

  Future<void> save() async {
    setState(() => saving = true);
    try {
      await api.patch('/api/whatsapp/config', {
        'recipients': _recipients,
        'enabled': enabled,
        'transfer_received': transferReceived,
        'transfer_sent': transferSent,
        'balance_changes': balanceChanges,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Configuración de WhatsApp guardada.')));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('No se pudo guardar. Revisa la conexión.')));
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Future<void> sendTest() async {
    try {
      final result = Map<String, dynamic>.from(await api.post(
          '/api/whatsapp/test', {
        'message': 'Prueba de Utilitaria: OpenWA está conectado correctamente.'
      }));
      final sent = (result['results'] as List?)
              ?.whereType<Map>()
              .where((item) => item['sent'] == true)
              .length ??
          0;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(sent > 0
                ? 'Mensaje de prueba enviado.'
                : 'OpenWA no pudo enviar el mensaje.')));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content:
                Text('No se pudo enviar la prueba. Guarda y revisa OpenWA.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: const ModernAppBar(title: 'WhatsApp', eyebrow: 'MÁS'),
        body: loading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: load,
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                  children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(18),
                        child: Row(children: [
                          const CircleAvatar(
                              backgroundColor: Color(0xffdcf8e8),
                              child: Icon(Icons.groups_rounded,
                                  color: Color(0xff16844a))),
                          const SizedBox(width: 14),
                          Expanded(
                              child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: const [
                                Text('Glender Moviles',
                                    style: TextStyle(
                                        fontSize: 17,
                                        fontWeight: FontWeight.w700)),
                                SizedBox(height: 4),
                                Text(
                                    'Grupo configurado para los avisos de saldo',
                                    style: TextStyle(color: Colors.black54)),
                              ])),
                        ]),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text('Destinatarios',
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 8),
                    TextField(
                      controller: recipientsController,
                      maxLines: 3,
                      decoration: const InputDecoration(
                        labelText: 'Chat ID o teléfono',
                        hintText: '120363420329472237@g.us',
                        helperText:
                            'Puedes añadir uno por línea o separados por comas.',
                      ),
                    ),
                    const SizedBox(height: 16),
                    Card(
                      child: Column(children: [
                        SwitchListTile.adaptive(
                            title: const Text('Avisos por WhatsApp'),
                            subtitle:
                                const Text('Activar o pausar todos los envíos'),
                            value: enabled,
                            onChanged: (value) =>
                                setState(() => enabled = value)),
                        const Divider(height: 1),
                        SwitchListTile.adaptive(
                            title: const Text('Transferencias recibidas'),
                            value: transferReceived,
                            onChanged: enabled
                                ? (value) =>
                                    setState(() => transferReceived = value)
                                : null),
                        SwitchListTile.adaptive(
                            title: const Text('Transferencias realizadas'),
                            value: transferSent,
                            onChanged: enabled
                                ? (value) =>
                                    setState(() => transferSent = value)
                                : null),
                        SwitchListTile.adaptive(
                            title: const Text('Cambios de saldo'),
                            subtitle: const Text(
                                'Nuevo saldo común después del movimiento'),
                            value: balanceChanges,
                            onChanged: enabled
                                ? (value) =>
                                    setState(() => balanceChanges = value)
                                : null),
                      ]),
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                        onPressed: saving ? null : save,
                        icon: saving
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2))
                            : const Icon(Icons.save_outlined),
                        label: const Text('Guardar configuración')),
                    OutlinedButton.icon(
                        onPressed: enabled ? sendTest : null,
                        icon: const Icon(Icons.send_outlined),
                        label: const Text('Enviar mensaje de prueba')),
                  ],
                ),
              ),
      );
}

class RatesPage extends StatefulWidget {
  const RatesPage({super.key});
  @override
  State<RatesPage> createState() => _RatesPageState();
}

class _RatesPageState extends State<RatesPage> {
  dynamic data;
  bool loading = true;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    if (mounted) setState(() => loading = data == null);
    try {
      data = await api.get('/api/rates/eltoque');
    } catch (_) {
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  List<Map<String, dynamic>> get _items {
    final payload = data as Map?;
    final structured = payload?['items'] as List?;
    if (structured != null) {
      return structured
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
    }
    const order = ['USD', 'EUR', 'MLC', 'CAD', 'MXN', 'ZELLE', 'CLA'];
    final rates = payload?['rates'] as Map? ?? {};
    return order
        .where(rates.containsKey)
        .map((code) => <String, dynamic>{
              'code': code,
              'unit': '1 $code',
              'value': rates[code],
              'quote': 'CUP',
              'change': 0,
              'trend': 'flat',
            })
        .toList();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: ModernAppBar(
          title: 'Tasas de cambio',
          eyebrow: 'ELTOQUE',
          actions: [
            headerAction(icon: Icons.refresh_rounded, onPressed: load)
          ]),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : data == null
              ? const EmptyState(
                  icon: Icons.cloud_off_rounded,
                  title: 'No hay tasas guardadas',
                  message:
                      'Conéctate una vez para guardar la primera consulta.')
              : RefreshIndicator(
                  onRefresh: load,
                  child: ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(16),
                      children: [
                        SyncStatusBar(
                            paths: const ['/api/rates/eltoque'],
                            onRefresh: load),
                        Container(
                          clipBehavior: Clip.antiAlias,
                          decoration: BoxDecoration(
                            color: AppPalette.surface,
                            borderRadius: BorderRadius.circular(26),
                            border: Border.all(
                                color: AppPalette.cyan.withValues(alpha: .22)),
                          ),
                          child: Column(children: [
                            Container(
                              width: double.infinity,
                              padding:
                                  const EdgeInsets.fromLTRB(20, 18, 20, 16),
                              color: AppPalette.blue,
                              child: const Column(children: [
                                Icon(Icons.currency_exchange_rounded,
                                    color: AppPalette.mint, size: 30),
                                SizedBox(height: 8),
                                Text('Mercado Informal de Divisas en Cuba',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 17,
                                        fontWeight: FontWeight.w700)),
                                SizedBox(height: 2),
                                Text('Tiempo real',
                                    style: TextStyle(
                                        color: AppPalette.mint,
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600)),
                              ]),
                            ),
                            ..._items.map((item) => _RateRow(item: item)),
                            Padding(
                              padding:
                                  const EdgeInsets.fromLTRB(16, 12, 16, 16),
                              child: Row(children: [
                                const Icon(Icons.schedule_rounded,
                                    size: 16, color: AppPalette.blue),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    '${(data as Map)['source_updated_at'] ?? 'Actualización del servidor: ${(data as Map)['fetched_at'] ?? 'reciente'}'}',
                                    style:
                                        Theme.of(context).textTheme.bodySmall,
                                  ),
                                ),
                              ]),
                            ),
                          ]),
                        ),
                        const SizedBox(height: 14),
                        Card(
                          child: ListTile(
                            leading: const Icon(Icons.info_outline_rounded),
                            title: const Text('Valores de referencia'),
                            subtitle: const Text(
                                'Son estimaciones del mercado informal, no una tasa oficial.'),
                            trailing: const Icon(Icons.open_in_new_rounded),
                            onTap: () => launchUrl(
                                Uri.parse(
                                    'https://eltoque.com/tasas-de-cambio-cuba'),
                                mode: LaunchMode.externalApplication),
                          ),
                        ),
                      ])));
}

class _RateRow extends StatelessWidget {
  final Map<String, dynamic> item;
  const _RateRow({required this.item});

  String _number(dynamic raw) {
    final value = double.tryParse('$raw') ?? 0;
    return value.toStringAsFixed(2);
  }

  @override
  Widget build(BuildContext context) {
    final change = double.tryParse('${item['change']}') ?? 0;
    final positive = change > 0;
    final negative = change < 0;
    final trendColor = positive
        ? const Color(0xffb33a3a)
        : negative
            ? const Color(0xff087f67)
            : Theme.of(context).colorScheme.outline;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: BoxDecoration(
        border: Border(
            bottom: BorderSide(color: AppPalette.navy.withValues(alpha: .08))),
      ),
      child: Row(children: [
        Container(
          width: 46,
          height: 38,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppPalette.canvas,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text('${item['code']}',
              style: const TextStyle(
                  color: AppPalette.navy, fontWeight: FontWeight.w800)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${item['unit'] ?? '1 ${item['code']}'}',
                style: const TextStyle(fontWeight: FontWeight.w700)),
            if (item['name'] != null)
              Text('${item['name']}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall),
          ]),
        ),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text('${_number(item['value'])} ${item['quote'] ?? 'CUP'}',
              style: const TextStyle(
                  color: AppPalette.ink,
                  fontSize: 16,
                  fontWeight: FontWeight.w800)),
          if (change != 0)
            Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(positive ? Icons.arrow_upward : Icons.arrow_downward,
                  size: 13, color: trendColor),
              Text(_number(change.abs()),
                  style: TextStyle(
                      color: trendColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w700)),
            ])
          else
            Text('Sin variación',
                style: TextStyle(
                    color: trendColor,
                    fontSize: 11,
                    fontWeight: FontWeight.w500)),
        ]),
      ]),
    );
  }
}

class RulesPage extends StatefulWidget {
  const RulesPage({super.key});
  @override
  State<RulesPage> createState() => _RulesPageState();
}

class _RulesPageState extends State<RulesPage> {
  List<dynamic> rules = [];
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final result = await api.get('/api/notification-rules');
      if (mounted) setState(() => rules = result as List<dynamic>);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: ModernAppBar(title: 'Filtros de privacidad', actions: [
        headerAction(icon: Icons.refresh_rounded, onPressed: load),
        headerAction(icon: Icons.add_rounded, onPressed: () => _add(context))
      ]),
      body: RefreshIndicator(
          onRefresh: load,
          child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(12),
              children: [
                SyncStatusBar(
                    paths: const ['/api/notification-rules'], onRefresh: load),
                if (rules.isEmpty)
                  const SizedBox(
                      height: 360,
                      child: EmptyState(
                          icon: Icons.filter_alt_off,
                          title: 'Sin filtros',
                          message:
                              'Añade nombres o textos que no quieras compartir.')),
                ...rules.map((r) => SwitchListTile(
                    value: r['enabled'] ?? true,
                    onChanged: (_) {},
                    title: Text('${r['text_contains']}'),
                    subtitle: Text(r['action'] ?? 'exclude_share')))
              ])));
  Future<void> _add(BuildContext context) async {
    final input = TextEditingController();
    await showDialog(
        context: context,
        builder: (_) => AlertDialog(
                title: const Text('Nuevo filtro'),
                content: TextField(
                    controller: input,
                    decoration: const InputDecoration(
                        labelText: 'Texto o nombre a excluir')),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Cancelar')),
                  FilledButton(
                      onPressed: () async {
                        if (input.text.trim().isNotEmpty) {
                          await api.post('/api/notification-rules', {
                            'text_contains': input.text.trim(),
                            'action': 'exclude_share'
                          });
                        }
                        if (context.mounted) Navigator.pop(context);
                        load();
                      },
                      child: const Text('Guardar'))
                ]));
  }
}

class NotificationTile extends StatelessWidget {
  final Map<String, dynamic> data;
  final VoidCallback? onBusiness;
  final VoidCallback? onPrivate;
  const NotificationTile(
      {super.key, required this.data, this.onBusiness, this.onPrivate});
  @override
  Widget build(BuildContext context) => Card(
      child: ListTile(
          leading: Icon(data['is_business'] == true
              ? Icons.storefront
              : Icons.notifications),
          title: Text(
              '${data['title'] ?? data['package_name'] ?? 'Notificación'}'),
          subtitle: Text(
              '${data['body'] ?? ''}\n${data['category'] ?? 'other'} · ${data['shared_with_family'] == true ? 'Compartida' : 'Privada'}'),
          isThreeLine: true,
          trailing: PopupMenuButton<String>(
              onSelected: (value) {
                if (value == 'business') onBusiness?.call();
                if (value == 'private') onPrivate?.call();
              },
              itemBuilder: (_) => const [
                    PopupMenuItem(
                        value: 'business', child: Text('Marcar como negocio')),
                    PopupMenuItem(value: 'private', child: Text('No compartir'))
                  ])));
}

class _MetricCard extends StatelessWidget {
  final String label, value;
  final IconData icon;
  const _MetricCard(
      {required this.label, required this.value, required this.icon});
  @override
  Widget build(BuildContext context) => Card(
      child: ListTile(
          leading: Icon(icon),
          title: Text(label),
          trailing: Text(value,
              style: const TextStyle(fontWeight: FontWeight.bold))));
}

class EmptyState extends StatelessWidget {
  final IconData icon;
  final String title, message;
  const EmptyState(
      {super.key,
      required this.icon,
      required this.title,
      required this.message});
  @override
  Widget build(BuildContext context) => Center(
      child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, size: 48, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 12),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 6),
            Text(message, textAlign: TextAlign.center)
          ])));
}
