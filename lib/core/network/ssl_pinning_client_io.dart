import 'dart:io';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

/// Helper to compute lowercase hex SHA-256 fingerprint from certificate DER bytes.
String computeCertSha256Fingerprint(Uint8List derBytes) {
  return sha256.convert(derBytes).toString().toLowerCase().replaceAll(':', '').trim();
}

/// Creates a hardened IOClient with strict TLS configuration and optional certificate fingerprint pinning.
http.Client createSecuredHttpClient({
  Set<String>? pinnedSha256Fingerprints,
  bool enablePinning = false,
}) {
  // If strict pinning is enabled with specific pins, do not inherit system user-installed CAs.
  // This blocks user-installed rogue MITM proxy certificates (Burp, Charles, mitmproxy).
  final securityContext = SecurityContext(withTrustedRoots: !enablePinning);

  final httpClient = HttpClient(context: securityContext)
    ..badCertificateCallback = (X509Certificate cert, String host, int port) {
      if (!enablePinning || pinnedSha256Fingerprints == null || pinnedSha256Fingerprints.isEmpty) {
        // Reject any bad certificate that fails standard CA trust
        return false;
      }

      final certFingerprint = computeCertSha256Fingerprint(cert.der);

      for (final pinned in pinnedSha256Fingerprints) {
        final cleanPinned = pinned.replaceAll(':', '').trim().toLowerCase();
        if (cleanPinned == certFingerprint) {
          return true;
        }
      }

      return false;
    };

  return IOClient(httpClient);
}

/// Returns true on native Dart IO platforms where socket-level certificate inspection is supported.
bool isSslPinningSupported() => true;
