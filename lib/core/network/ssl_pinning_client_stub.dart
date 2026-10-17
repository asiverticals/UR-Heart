import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;

/// Helper to compute lowercase hex SHA-256 fingerprint from certificate DER bytes.
String computeCertSha256Fingerprint(Uint8List derBytes) {
  return sha256.convert(derBytes).toString().toLowerCase().replaceAll(':', '').trim();
}

/// Web/fallback implementation of secured HTTP client factory.
/// Web browsers enforce their own Web PKI and do not expose raw TLS socket handles.
http.Client createSecuredHttpClient({
  Set<String>? pinnedSha256Fingerprints,
  bool enablePinning = false,
}) {
  return http.Client();
}

/// Returns false on web or platforms where native socket-level TLS pinning is not directly configurable.
bool isSslPinningSupported() => false;
