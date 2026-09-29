import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:utilitaria/main.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('conserva la última respuesta cuando el servidor queda sin conexión',
      () async {
    SharedPreferences.setMockInitialValues({});
    var online = true;
    final httpClient = MockClient((_) async {
      if (!online) throw const SocketException('sin conexión');
      return http.Response('{"amount":"313.00"}', 200,
          headers: {'content-type': 'application/json'});
    });
    final client = ApiClient(
        baseUrl: 'https://example.test',
        requestTimeout: const Duration(milliseconds: 150),
        httpClient: httpClient);

    expect(await client.get('/api/balance'), {'amount': '313.00'});
    expect(client.status('/api/balance').offline, isFalse);
    expect(client.status('/api/balance').updatedAt, isNotNull);

    online = false;
    expect(await client.get('/api/balance'), {'amount': '313.00'});
    expect(client.status('/api/balance').offline, isTrue);
    expect(client.status('/api/balance').updatedAt, isNotNull);
  });
}
