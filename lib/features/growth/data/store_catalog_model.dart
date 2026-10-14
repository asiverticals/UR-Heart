import 'package:flutter/foundation.dart';

@immutable
class StoreProduct {
  final String id;
  final String title;
  final String description;
  final String productClass; // 'micro_perk' | 'pass'
  final double inrPrice;
  final double? usdPrice;
  final String currencySymbol;
  final String? badgeLabel;
  final String? entitlement;

  const StoreProduct({
    required this.id,
    required this.title,
    required this.description,
    required this.productClass,
    required this.inrPrice,
    this.usdPrice,
    this.currencySymbol = '₹',
    this.badgeLabel,
    this.entitlement,
  });

  bool get isPass => productClass == 'pass';

  String get formattedPrice {
    final formattedInr = inrPrice >= 1000
        ? inrPrice.toStringAsFixed(0).replaceAllMapped(
              RegExp(r'(\d+?)(?=(\d\d)+(\d)(?!\d))'),
              (m) => '${m[1]},',
            )
        : inrPrice.toStringAsFixed(0);
    return '$currencySymbol$formattedInr';
  }

  factory StoreProduct.fromJson(Map<String, dynamic> json) {
    return StoreProduct(
      id: json['id'] as String? ?? json['product_identifier'] as String? ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      productClass: json['product_class'] as String? ?? json['class'] as String? ?? 'micro_perk',
      inrPrice: (json['inr_price'] as num?)?.toDouble() ?? (json['inr'] as num?)?.toDouble() ?? 0.0,
      usdPrice: (json['usd_price'] as num?)?.toDouble() ?? (json['usd'] as num?)?.toDouble(),
      currencySymbol: json['currency_symbol'] as String? ?? '₹',
      badgeLabel: json['badge_label'] as String? ?? json['badge'] as String?,
      entitlement: json['entitlement'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'product_class': productClass,
      'inr_price': inrPrice,
      'usd_price': usdPrice,
      'currency_symbol': currencySymbol,
      'badge_label': badgeLabel,
      'entitlement': entitlement,
    };
  }
}
