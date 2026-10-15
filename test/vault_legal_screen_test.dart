import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/features/legal_vault/presentation/screens/vault_legal_screen.dart';

class MockVaultHttpClient implements SanctuaryHttpClient {
  final Map<String, dynamic>? mockNominee;
  final List<dynamic>? mockGrievances;
  final List<String> requestedPaths = [];
  final List<Map<String, dynamic>?> requestedBodies = [];

  MockVaultHttpClient({this.mockNominee, this.mockGrievances});

  @override
  Duration get requestTimeout => const Duration(seconds: 5);

  @override
  Future<Map<String, dynamic>> get(String path) async {
    requestedPaths.add(path);
    if (path == '/api/v1/legal/nominee' || path == '/api/v1/vault/nominee') {
      return {
        'success': true,
        'data': mockNominee,
      };
    } else if (path == '/api/v1/legal/grievances' || path == '/api/v1/vault/grievances') {
      return {
        'success': true,
        'data': mockGrievances ?? [],
      };
    }
    return {'success': true, 'data': {}};
  }

  @override
  Future<Map<String, dynamic>> post(String path, {Map<String, dynamic>? body}) async {
    requestedPaths.add(path);
    requestedBodies.add(body);

    if (path == '/api/v1/legal/nominee' || path == '/api/v1/vault/nominee') {
      return {
        'success': true,
        'data': {
          'nominee_name': body?['nominee_name'] ?? 'Saved Nominee',
          'nominee_contact': body?['nominee_contact'] ?? '+919999999999',
          'relationship': body?['relationship'] ?? 'Brother',
          'assigned_at': DateTime.now().toIso8601String(),
          'verification_status': 'designated',
        },
      };
    } else if (path == '/api/v1/legal/grievance' || path == '/api/v1/vault/grievance') {
      return {
        'success': true,
        'data': {
          'dossier_reference_id': 'URH-GRV-20261015-NEW999',
          'status': 'acknowledged',
          'acknowledgment_sent_at': DateTime.now().toIso8601String(),
          'statutory_resolution_due_at': DateTime.now().add(const Duration(days: 15)).toIso8601String(),
        },
      };
    } else if (path == '/api/v1/legal/data-export' || path == '/api/v1/vault/data-export') {
      return {
        'success': true,
        'data': {
          'compliance_seal': {
            'act': 'DPDP Act 2023 Section 11',
            'sanitized': true,
          },
          'user_profile': {
            'full_name': 'Sovereign Test Seeker',
          },
        },
      };
    }
    return {'success': true};
  }

  @override
  Future<Map<String, dynamic>> delete(String path, {Map<String, dynamic>? body}) async {
    return {'success': true};
  }

  @override
  Future<Map<String, dynamic>> put(String path, {Map<String, dynamic>? body}) async {
    return {'success': true};
  }
}

Widget buildTestApp({
  required SanctuaryHttpClient client,
}) {
  return ProviderScope(
    overrides: [
      sanctuaryHttpClientProvider.overrideWithValue(client),
    ],
    child: const MaterialApp(
      home: VaultLegalScreen(),
    ),
  );
}

void main() {
  testWidgets(
    'Test 1: VaultLegalScreen renders statutory nominee status, grievance list with SLA countdown chips, and export button',
    (tester) async {
      tester.view.physicalSize = const Size(800, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final mockClient = MockVaultHttpClient(
        mockNominee: {
          'nominee_name': 'Kavita Verma',
          'nominee_contact': '+919876500000',
          'relationship': 'Sister',
          'assigned_at': '2026-10-15T00:00:00.000Z',
          'verification_status': 'designated',
        },
        mockGrievances: [
          {
            'dossier_reference_id': 'URH-GRV-20261015-A1B2C3',
            'violation_category': 'harassment',
            'evidence_text': 'Repeated unwanted outreach',
            'status': 'acknowledged',
            'acknowledgment_sent_at': '2026-10-15T00:00:00.000Z',
            'statutory_resolution_due_at': DateTime.now().add(const Duration(days: 14)).toIso8601String(),
            'created_at': '2026-10-15T00:00:00.000Z',
          },
        ],
      );

      await tester.pumpWidget(buildTestApp(client: mockClient));
      await tester.pumpAndSettle();

      // Top Bar Title
      expect(find.text('Sacred Legal Vault'), findsOneWidget);
      expect(find.text('Statutory Rights & DPDP Act 2023 Protections'), findsOneWidget);

      // Section 1: Nominee
      expect(find.text('Digital Nominee Designation'), findsOneWidget);
      expect(find.text('Kavita Verma'), findsOneWidget);
      expect(find.text('Sister • +919876500000'), findsOneWidget);
      expect(find.text('DESIGNATED'), findsOneWidget);

      // Section 2: Grievances
      expect(find.text('Statutory Grievance Redressal'), findsOneWidget);
      expect(find.text('URH-GRV-20261015-A1B2C3'), findsOneWidget);
      expect(find.text('HARASSMENT'), findsOneWidget);
      expect(find.textContaining('days remaining'), findsOneWidget);
      expect(find.text('File Statutory Grievance'), findsOneWidget);

      // Section 3: Data Export
      expect(find.text('Machine-Readable Data Portability'), findsOneWidget);
      expect(find.text('Generate Full Data Export (JSON)'), findsOneWidget);
    },
  );

  testWidgets(
    'Test 2: Submitting nominee form dispatches valid payload and updates screen state',
    (tester) async {
      tester.view.physicalSize = const Size(800, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final mockClient = MockVaultHttpClient(
        mockNominee: null, // Initially unassigned
      );

      await tester.pumpWidget(buildTestApp(client: mockClient));
      await tester.pumpAndSettle();

      // Verify unassigned alert chip
      expect(find.text('No digital nominee appointed yet.'), findsOneWidget);
      final designateBtn = find.text('Designate Digital Nominee');
      expect(designateBtn, findsOneWidget);

      // Open Modal Sheet
      await tester.tap(designateBtn);
      await tester.pumpAndSettle();

      expect(find.text('Designate Digital Nominee'), findsWidgets);

      // Fill Form
      final textFields = find.byType(TextField);
      expect(textFields, findsNWidgets(3));

      await tester.enterText(textFields.at(0), 'Aditya Kashyap');
      await tester.enterText(textFields.at(1), '+919811223344');
      await tester.enterText(textFields.at(2), 'Brother');
      await tester.pumpAndSettle();

      // Submit
      final sealBtn = find.text('Seal Nominee into Vault');
      expect(sealBtn, findsOneWidget);
      await tester.tap(sealBtn);
      await tester.pumpAndSettle();

      // Verify POST call was dispatched
      expect(mockClient.requestedPaths, contains('/api/v1/legal/nominee'));
      final nomineeBody = mockClient.requestedBodies.firstWhere(
        (b) => b?['nominee_name'] == 'Aditya Kashyap',
      );
      expect(nomineeBody?['nominee_contact'], '+919811223344');
      expect(nomineeBody?['relationship'], 'Brother');

      // Verify Screen updated with new nominee
      expect(find.text('Aditya Kashyap'), findsOneWidget);
      expect(find.text('DESIGNATED'), findsOneWidget);
    },
  );

  testWidgets(
    'Test 3: Tapping Generate Full Data Export triggers export and opens archive dialog',
    (tester) async {
      tester.view.physicalSize = const Size(800, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final mockClient = MockVaultHttpClient();

      await tester.pumpWidget(buildTestApp(client: mockClient));
      await tester.pumpAndSettle();

      final exportBtn = find.text('Generate Full Data Export (JSON)');
      expect(exportBtn, findsOneWidget);

      await tester.tap(exportBtn);
      await tester.pumpAndSettle();

      // Verify dialog opened
      expect(find.text('Data Portability Archive Ready'), findsOneWidget);
      expect(find.textContaining('DPDP Act 2023 Section 11'), findsOneWidget);
      expect(find.text('Copy JSON'), findsOneWidget);
      expect(find.text('Close'), findsOneWidget);
    },
  );
}
