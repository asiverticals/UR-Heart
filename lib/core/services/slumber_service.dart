import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

final slumberServiceProvider = Provider<SlumberService>((ref) {
  return SlumberService();
});

/// Sensor service orchestrating nocturnal slumber tracking and morning harvest circadian bounds.
class SlumberService {
  static const String slumberStartKey = 'sanctuary_slumber_start_epoch';
  static const String slumberEndKey = 'sanctuary_slumber_end_epoch';
  static const String lastHarvestDateKey = 'sanctuary_last_harvest_date';

  /// Default baseline rest duration in hours when sensor hardware or sleep epoch is unavailable.
  static const double defaultBaselineHours = 7.0;

  /// Generates the storage key for harvest claim tracking, scoped by account if userId is provided.
  static String harvestKey([String? userId]) =>
      userId != null && userId.isNotEmpty ? '${lastHarvestDateKey}_$userId' : lastHarvestDateKey;

  bool _isTracking = false;
  bool get isTracking => _isTracking;

  /// Starts low-frequency nocturnal movement detection.
  /// Replaces existing start marker with current timestamp and clears stale end markers
  /// so each night starts an independent, paired sleep period.
  Future<void> startSlumberTracking([DateTime? timestamp]) async {
    _isTracking = true;
    final now = timestamp ?? DateTime.now();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(slumberStartKey, now.millisecondsSinceEpoch);
    await prefs.remove(slumberEndKey);
  }

  /// Stops tracking and marks wake-up time.
  Future<void> stopSlumberTracking([DateTime? timestamp]) async {
    _isTracking = false;
    await recordSlumberEnd(timestamp);
  }

  /// Explicitly records the onset of restful nocturnal slumber and clears any stale end marker.
  Future<void> recordSlumberStart([DateTime? timestamp]) async {
    final prefs = await SharedPreferences.getInstance();
    final time = timestamp ?? DateTime.now();
    await prefs.setInt(slumberStartKey, time.millisecondsSinceEpoch);
    await prefs.remove(slumberEndKey);
  }

  /// Explicitly records device wake-up and the conclusion of slumber.
  Future<void> recordSlumberEnd([DateTime? timestamp]) async {
    final prefs = await SharedPreferences.getInstance();
    final time = timestamp ?? DateTime.now();
    await prefs.setInt(slumberEndKey, time.millisecondsSinceEpoch);
  }

  /// Computes elapsed hours between recorded slumber start and wake event.
  /// Output is cleanly clamped between 0.0 and 12.0 hours. Defaults to 7.0 hours if unrecorded.
  Future<double> resolveLastNightSleepHours() async {
    final prefs = await SharedPreferences.getInstance();
    final startEpoch = prefs.getInt(slumberStartKey);
    final endEpoch = prefs.getInt(slumberEndKey);

    if (startEpoch == null || endEpoch == null) {
      return defaultBaselineHours;
    }

    final elapsedMs = endEpoch - startEpoch;
    if (elapsedMs <= 0) {
      return defaultBaselineHours;
    }

    final hours = elapsedMs / (1000 * 60 * 60);
    // Bounded between 0.0 and 12.0 hours
    return clampDouble(hours, 0.0, 12.0);
  }

  /// Validates whether the morning harvest is claimable:
  /// 1. Prioritizes server's morning_harvest_available if provided.
  /// 2. Otherwise validates current window (05:00 - 12:00) and ensures harvest has not been claimed today (UTC).
  Future<bool> isMorningHarvestAvailable({
    String? userId,
    DateTime? now,
    bool? serverHarvestAvailable,
  }) async {
    if (serverHarvestAvailable != null) {
      return serverHarvestAvailable;
    }

    final current = now ?? DateTime.now();
    if (current.hour < 5 || current.hour >= 12) {
      return false;
    }

    final prefs = await SharedPreferences.getInstance();
    final lastHarvestDate = prefs.getString(harvestKey(userId));
    final todayString = _formatDate(current);

    if (lastHarvestDate == todayString) {
      return false;
    }

    return true;
  }

  /// Marks today's morning harvest as successfully claimed for the given account.
  Future<void> markHarvestClaimed({String? userId, DateTime? now}) async {
    final prefs = await SharedPreferences.getInstance();
    final current = now ?? DateTime.now();
    await prefs.setString(harvestKey(userId), _formatDate(current));
  }

  /// Resets stored sleep timestamps for testing or new night tracking cycle.
  Future<void> clearSlumberData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(slumberStartKey);
    await prefs.remove(slumberEndKey);
  }

  String _formatDate(DateTime dt) {
    return '${dt.year.toString().padLeft(4, '0')}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}';
  }
}
