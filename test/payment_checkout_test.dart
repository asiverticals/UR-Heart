import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ur_heart/core/billing/sanctuary_billing_service.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/features/growth/data/payment_service.dart';
import 'package:ur_heart/features/growth/data/store_catalog_model.dart';
import 'package:ur_heart/features/growth/presentation/controllers/growth_hub_controller.dart';

class MockSanctuaryHttpClient implements SanctuaryHttpClient {
  final List<String> requestedPaths = [];
  final List<Map<String, dynamic>?> requestedBodies = [];

  @override
  Duration get requestTimeout => const Duration(seconds: 5);

  @override
  Future<Map<String, dynamic>> post(String path, {Map<String, dynamic>? body}) async {
    requestedPaths.add(path);
    requestedBodies.add(body);

    if (path == '/api/v1/payments/create-order') {
      return {
        'success': true,
        'data': {
          'order_id': 'order_test_mock_123',
          'amount': 29.0,
          'amount_paise': 2900,
          'currency': 'INR',
          'key_id': 'rzp_test_key_abc',
        },
      };
    } else if (path == '/api/v1/payments/verify-checkout') {
      return {
        'success': true,
        'data': {
          'success': true,
          'transaction_id': body?['razorpay_payment_id'],
        },
      };
    }
    return {'success': true};
  }

  @override
  Future<Map<String, dynamic>> get(String path) async {
    requestedPaths.add(path);
    return {'success': true, 'data': {}};
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

class MockBillingService implements SanctuaryBillingService {
  int fetchCatalogCalls = 0;
  int fetchBalancesCalls = 0;

  @override
  Future<Map<String, dynamic>> fetchStoreCatalog() async {
    fetchCatalogCalls++;
    return {
      'success': true,
      'data': {
        'currency': 'INR',
        'usd_enabled': false,
        'products': [
          {
            'id': 'direct_letter_single',
            'title': 'Direct Thought Letter',
            'description': 'Send an intentional direct letter.',
            'product_class': 'micro_perk',
            'inr_price': 29.0,
            'currency_symbol': '₹',
          }
        ],
      },
    };
  }

  @override
  Future<Map<String, dynamic>> fetchBalances() async {
    fetchBalancesCalls++;
    return {
      'success': true,
      'data': {
        'reward_balance': 100,
        'streak_count': 3,
        'direct_letters_count': 5,
        'boost_points': 50,
        'swipes_remaining': 25,
        'subscription_tier': 'free',
        'is_ad_free': false,
      },
    };
  }

  @override
  Future<Map<String, dynamic>> claimReward({
    required String transactionId,
    required String adType,
    required String network,
  }) async {
    return {'success': true};
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late MockSanctuaryHttpClient mockHttpClient;
  late MockBillingService mockBillingService;
  late StoreProduct testProduct;

  setUp(() {
    mockHttpClient = MockSanctuaryHttpClient();
    mockBillingService = MockBillingService();
    testProduct = const StoreProduct(
      id: 'direct_letter_single',
      title: 'Direct Thought Letter',
      description: 'Send an intentional direct letter.',
      productClass: 'micro_perk',
      inrPrice: 29.0,
      currencySymbol: '₹',
    );
  });

  testWidgets('Test 1: initiateProductPurchase requests order from backend with correct product identifier',
      (tester) async {
    Map<String, dynamic>? capturedLauncherOptions;

    final paymentService = SanctuaryPaymentService(
      mockHttpClient,
      launcher: (context, options) async {
        capturedLauncherOptions = options;
        return const RazorpayCheckoutResult.success(
          paymentId: 'pay_test_succ_123',
          orderId: 'order_test_mock_123',
          signature: 'sig_test_valid_123',
        );
      },
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sanctuaryBillingServiceProvider.overrideWithValue(mockBillingService),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: Consumer(
              builder: (context, ref, child) {
                return ElevatedButton(
                  onPressed: () {
                    paymentService.initiateProductPurchase(
                      context: context,
                      product: testProduct,
                      ref: ref,
                    );
                  },
                  child: const Text('Buy Letter'),
                );
              },
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Buy Letter'));
    await tester.pumpAndSettle();

    // Verify order request was issued to backend with SKU
    expect(mockHttpClient.requestedPaths.contains('/api/v1/payments/create-order'), isTrue);
    final orderBody = mockHttpClient.requestedBodies[0];
    expect(orderBody?['product_identifier'], equals('direct_letter_single'));

    // Verify launcher was supplied correct Razorpay checkout options
    expect(capturedLauncherOptions, isNotNull);
    expect(capturedLauncherOptions?['amount'], equals(2900));
    expect(capturedLauncherOptions?['order_id'], equals('order_test_mock_123'));
    expect(capturedLauncherOptions?['theme']?['color'], equals('#D4AF37'));
    expect(capturedLauncherOptions?['name'], equals('UR-Heart Sanctuary'));
  });

  testWidgets('Test 2: Successful verification callback triggers wallet balance refresh',
      (tester) async {
    final paymentService = SanctuaryPaymentService(
      mockHttpClient,
      launcher: (context, options) async {
        return const RazorpayCheckoutResult.success(
          paymentId: 'pay_test_succ_999',
          orderId: 'order_test_mock_123',
          signature: 'sig_test_valid_999',
        );
      },
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sanctuaryBillingServiceProvider.overrideWithValue(mockBillingService),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: Consumer(
              builder: (context, ref, child) {
                return ElevatedButton(
                  onPressed: () {
                    paymentService.initiateProductPurchase(
                      context: context,
                      product: testProduct,
                      ref: ref,
                    );
                  },
                  child: const Text('Checkout Test'),
                );
              },
            ),
          ),
        ),
      ),
    );

    // Initial catalog calls count
    final initialCatalogCalls = mockBillingService.fetchCatalogCalls;

    await tester.tap(find.text('Checkout Test'));
    await tester.pumpAndSettle();

    // Verify verify-checkout endpoint was dispatched with correct tokens
    expect(mockHttpClient.requestedPaths.contains('/api/v1/payments/verify-checkout'), isTrue);
    final verifyBody = mockHttpClient.requestedBodies
        .firstWhere((b) => b?['razorpay_payment_id'] == 'pay_test_succ_999');
    expect(verifyBody?['razorpay_order_id'], equals('order_test_mock_123'));
    expect(verifyBody?['razorpay_signature'], equals('sig_test_valid_999'));
    expect(verifyBody?['product_identifier'], equals('direct_letter_single'));

    // Verify wallet balance & store catalog was refreshed
    expect(mockBillingService.fetchCatalogCalls, greaterThan(initialCatalogCalls));

    // Verify frosted confirmation snackbar rendered
    expect(find.text('Entitlement Sealed into Your Vault'), findsOneWidget);
  });

  testWidgets('Test 3: Dismissed or failed checkout displays gentle alert and skips verification',
      (tester) async {
    final paymentService = SanctuaryPaymentService(
      mockHttpClient,
      launcher: (context, options) async {
        return const RazorpayCheckoutResult.failure(errorMessage: 'User cancelled');
      },
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sanctuaryBillingServiceProvider.overrideWithValue(mockBillingService),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: Consumer(
              builder: (context, ref, child) {
                return ElevatedButton(
                  onPressed: () {
                    paymentService.initiateProductPurchase(
                      context: context,
                      product: testProduct,
                      ref: ref,
                    );
                  },
                  child: const Text('Cancel Test'),
                );
              },
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Cancel Test'));
    await tester.pumpAndSettle();

    // Verify verify-checkout was NOT dispatched
    expect(mockHttpClient.requestedPaths.contains('/api/v1/payments/verify-checkout'), isFalse);

    // Verify gentle frosted alert rendered
    expect(find.text('Payment paused. No charges applied.'), findsOneWidget);
  });
}
