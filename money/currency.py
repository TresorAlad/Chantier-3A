"""
ISO 4217 currency table (ported from backend/internal/money/currency.go).

Amounts elsewhere in Cackle are stored as integer minor units; the exponent here
is the number of decimal places for that currency (e.g. 2 for EUR, 0 for XOF).
"""

from __future__ import annotations


class CurrencyError(Exception):
    """Base class for currency validation errors."""


class ErrInvalidCurrency(CurrencyError):
    """Raised when the code is not a 3-letter ISO 4217 string."""


class ErrUnknownCurrency(CurrencyError):
    """Raised when the code is well-formed but not in CURRENCY_DEFS."""


# code -> (minor_unit_exponent, English display name)
CURRENCY_DEFS: dict[str, tuple[int, str]] = {
    "AED": (2, 'United Arab Emirates Dirham'),
    "AFN": (2, 'Afghan Afghani'),
    "ALL": (2, 'Albanian Lek'),
    "AMD": (2, 'Armenian Dram'),
    "ANG": (2, 'Netherlands Antillean Guilder'),
    "AOA": (2, 'Angolan Kwanza'),
    "ARS": (2, 'Argentine Peso'),
    "AUD": (2, 'Australian Dollar'),
    "AWG": (2, 'Aruban Florin'),
    "AZN": (2, 'Azerbaijani Manat'),
    "BAM": (2, 'Bosnia-Herzegovina Convertible Mark'),
    "BBD": (2, 'Barbadian Dollar'),
    "BDT": (2, 'Bangladeshi Taka'),
    "BGN": (2, 'Bulgarian Lev'),
    "BHD": (3, 'Bahraini Dinar'),
    "BIF": (0, 'Burundian Franc'),
    "BMD": (2, 'Bermudian Dollar'),
    "BND": (2, 'Brunei Dollar'),
    "BOB": (2, 'Bolivian Boliviano'),
    "BRL": (2, 'Brazilian Real'),
    "BSD": (2, 'Bahamian Dollar'),
    "BTN": (2, 'Bhutanese Ngultrum'),
    "BWP": (2, 'Botswana Pula'),
    "BYN": (2, 'Belarusian Ruble'),
    "BZD": (2, 'Belize Dollar'),
    "CAD": (2, 'Canadian Dollar'),
    "CDF": (2, 'Congolese Franc'),
    "CHF": (2, 'Swiss Franc'),
    "CLP": (0, 'Chilean Peso'),
    "CNY": (2, 'Chinese Yuan'),
    "COP": (2, 'Colombian Peso'),
    "CRC": (2, 'Costa Rican Colon'),
    "CUP": (2, 'Cuban Peso'),
    "CVE": (2, 'Cape Verdean Escudo'),
    "CZK": (2, 'Czech Koruna'),
    "DJF": (0, 'Djiboutian Franc'),
    "DKK": (2, 'Danish Krone'),
    "DOP": (2, 'Dominican Peso'),
    "DZD": (2, 'Algerian Dinar'),
    "EGP": (2, 'Egyptian Pound'),
    "ETB": (2, 'Ethiopian Birr'),
    "EUR": (2, 'Euro'),
    "FJD": (2, 'Fijian Dollar'),
    "GBP": (2, 'British Pound Sterling'),
    "GEL": (2, 'Georgian Lari'),
    "GHS": (2, 'Ghanaian Cedi'),
    "GMD": (2, 'Gambian Dalasi'),
    "GNF": (0, 'Guinean Franc'),
    "GTQ": (2, 'Guatemalan Quetzal'),
    "GYD": (2, 'Guyanese Dollar'),
    "HKD": (2, 'Hong Kong Dollar'),
    "HNL": (2, 'Honduran Lempira'),
    "HTG": (2, 'Haitian Gourde'),
    "HUF": (2, 'Hungarian Forint'),
    "IDR": (2, 'Indonesian Rupiah'),
    "ILS": (2, 'Israeli New Shekel'),
    "INR": (2, 'Indian Rupee'),
    "IQD": (3, 'Iraqi Dinar'),
    "IRR": (2, 'Iranian Rial'),
    "ISK": (0, 'Icelandic Krona'),
    "JMD": (2, 'Jamaican Dollar'),
    "JOD": (3, 'Jordanian Dinar'),
    "JPY": (0, 'Japanese Yen'),
    "KES": (2, 'Kenyan Shilling'),
    "KGS": (2, 'Kyrgyzstani Som'),
    "KHR": (2, 'Cambodian Riel'),
    "KMF": (0, 'Comorian Franc'),
    "KRW": (0, 'South Korean Won'),
    "KWD": (3, 'Kuwaiti Dinar'),
    "KYD": (2, 'Cayman Islands Dollar'),
    "KZT": (2, 'Kazakhstani Tenge'),
    "LAK": (2, 'Lao Kip'),
    "LBP": (2, 'Lebanese Pound'),
    "LKR": (2, 'Sri Lankan Rupee'),
    "LRD": (2, 'Liberian Dollar'),
    "LSL": (2, 'Lesotho Loti'),
    "LYD": (3, 'Libyan Dinar'),
    "MAD": (2, 'Moroccan Dirham'),
    "MDL": (2, 'Moldovan Leu'),
    "MGA": (2, 'Malagasy Ariary'),
    "MKD": (2, 'Macedonian Denar'),
    "MMK": (2, 'Myanmar Kyat'),
    "MNT": (2, 'Mongolian Tugrik'),
    "MOP": (2, 'Macanese Pataca'),
    "MRU": (2, 'Mauritanian Ouguiya'),
    "MUR": (2, 'Mauritian Rupee'),
    "MVR": (2, 'Maldivian Rufiyaa'),
    "MWK": (2, 'Malawian Kwacha'),
    "MXN": (2, 'Mexican Peso'),
    "MYR": (2, 'Malaysian Ringgit'),
    "MZN": (2, 'Mozambican Metical'),
    "NAD": (2, 'Namibian Dollar'),
    "NGN": (2, 'Nigerian Naira'),
    "NIO": (2, 'Nicaraguan Cordoba'),
    "NOK": (2, 'Norwegian Krone'),
    "NPR": (2, 'Nepalese Rupee'),
    "NZD": (2, 'New Zealand Dollar'),
    "OMR": (3, 'Omani Rial'),
    "PAB": (2, 'Panamanian Balboa'),
    "PEN": (2, 'Peruvian Sol'),
    "PGK": (2, 'Papua New Guinean Kina'),
    "PHP": (2, 'Philippine Peso'),
    "PKR": (2, 'Pakistani Rupee'),
    "PLN": (2, 'Polish Zloty'),
    "PYG": (0, 'Paraguayan Guarani'),
    "QAR": (2, 'Qatari Riyal'),
    "RON": (2, 'Romanian Leu'),
    "RSD": (2, 'Serbian Dinar'),
    "RUB": (2, 'Russian Ruble'),
    "RWF": (0, 'Rwandan Franc'),
    "SAR": (2, 'Saudi Riyal'),
    "SBD": (2, 'Solomon Islands Dollar'),
    "SCR": (2, 'Seychellois Rupee'),
    "SDG": (2, 'Sudanese Pound'),
    "SEK": (2, 'Swedish Krona'),
    "SGD": (2, 'Singapore Dollar'),
    "SLE": (2, 'Sierra Leonean Leone'),
    "SOS": (2, 'Somali Shilling'),
    "SRD": (2, 'Surinamese Dollar'),
    "SSP": (2, 'South Sudanese Pound'),
    "STN": (2, 'Sao Tome and Principe Dobra'),
    "SZL": (2, 'Eswatini Lilangeni'),
    "THB": (2, 'Thai Baht'),
    "TJS": (2, 'Tajikistani Somoni'),
    "TMT": (2, 'Turkmenistani Manat'),
    "TND": (3, 'Tunisian Dinar'),
    "TOP": (2, "Tongan Pa'anga"),
    "TRY": (2, 'Turkish Lira'),
    "TTD": (2, 'Trinidad and Tobago Dollar'),
    "TWD": (2, 'New Taiwan Dollar'),
    "TZS": (2, 'Tanzanian Shilling'),
    "UAH": (2, 'Ukrainian Hryvnia'),
    "UGX": (0, 'Ugandan Shilling'),
    "USD": (2, 'United States Dollar'),
    "UYU": (2, 'Uruguayan Peso'),
    "UZS": (2, 'Uzbekistani Som'),
    "VES": (2, 'Venezuelan Bolivar Soberano'),
    "VND": (0, 'Vietnamese Dong'),
    "VUV": (0, 'Vanuatu Vatu'),
    "WST": (2, 'Samoan Tala'),
    "XAF": (0, 'Central African CFA Franc'),
    "XCD": (2, 'East Caribbean Dollar'),
    "XOF": (0, 'West African CFA Franc'),
    "XPF": (0, 'CFP Franc'),
    "YER": (2, 'Yemeni Rial'),
    "ZAR": (2, 'South African Rand'),
    "ZMW": (2, 'Zambian Kwacha'),
}

def normalize(code: str) -> str:
    """Return upper-case code if known; raise CurrencyError otherwise."""
    c = (code or "").strip().upper()
    if len(c) != 3 or not c.isalpha():
        raise ErrInvalidCurrency("invalid currency code")
    if c not in CURRENCY_DEFS:
        raise ErrUnknownCurrency("unknown currency code")
    return c

def list_currencies() -> list[dict]:
    """Sorted catalog for GET /api/meta/currencies and org/event forms."""
    out = [{"code": code, "exponent": exp, "name": name} for code, (exp, name) in CURRENCY_DEFS.items()]
    out.sort(key=lambda x: x["code"])
    return out
