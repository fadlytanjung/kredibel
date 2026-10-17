"""The fictional world of the synthetic books (docs/18 §2).

Every name, number and address is invented; tax IDs start with `99-` so they are visibly fake.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .model import Party, PayTo

YEAR = 2026
MONTHS = [f"{YEAR}-{m:02d}" for m in range(1, 7)]
WATERMARK = "SYNTHETIC — FOR TESTING"
VAT_RATE = Decimal("0.11")

BUSINESS = Party(
    name="Sunrise Coffee Roasters",
    address=("12 Roastery Lane", "Bandung 40135"),
    tax_id="99-731.204.5-018.000",
)
LEGAL_FORM = "PARTNERSHIP"
INDUSTRY = "Coffee roasting & wholesale"
PARTNER = "Andi Pratama"
HOLDER = "SUNRISE COFFEE ROASTERS"

BANK_NAME = "Archipelago Commerce Bank"
BANK_SHORT = "ACB"
BRANCH = "Bandung Dago Branch"
ACCOUNT = "9900004821"
SECOND_ACCOUNT = "9900005577"  # undeclared-account fixture
STATEMENT_PRODUCER = "ACB CoreBanking ReportEngine 4.2"
STATEMENT_CREATOR = "ACB e-Statement"
SECOND_BANK = "Meridian Savings Bank"

OWN_PAY_TO = PayTo(BANK_NAME, ACCOUNT, HOLDER)


@dataclass(frozen=True)
class Client:
    party: Party
    lo: int  # invoice subtotal range, rupiah
    hi: int


CLIENTS = [
    Client(
        Party("Harborview Hotel Group", ("88 Pier Road", "Bandung 40115"), "99-412.087.3-421.000"),
        40_000_000,
        65_000_000,
    ),
    Client(
        Party("Daybreak Café", ("4 Morning Street", "Bandung 40132"), "99-208.551.9-423.000"),
        16_000_000,
        30_000_000,
    ),
    Client(
        Party("Highland Resort & Spa", ("1 Summit Way", "Lembang 40391"), "99-617.330.2-441.000"),
        42_000_000,
        70_000_000,
    ),
    Client(
        Party("Souvenir Corner", ("27 Market Lane", "Bandung 40181"), "99-905.114.6-429.000"),
        8_000_000,
        15_000_000,
    ),
    Client(
        Party(
            "Spice Route Restaurant", ("9 Clove Avenue", "Bandung 40117"), "99-330.762.1-422.000"
        ),
        12_000_000,
        24_000_000,
    ),
    Client(
        Party("Hillside Coffee Bar", ("51 Ridge Street", "Bandung 40142"), "99-781.402.8-424.000"),
        11_000_000,
        21_000_000,
    ),
]

# Spec 024: more clients for the demo's volume only; the books of docs/18 never use them.
EXTRA_CLIENTS = [
    Client(
        Party("Kopi Senja Café", ("Jl. Riau 41", "Bandung 40115"), "99-102.338.4-423.000"),
        3_000_000,
        9_000_000,
    ),
    Client(
        Party("Braga Corner Coffee", ("Jl. Braga 12", "Bandung 40111"), "99-118.502.7-423.000"),
        4_000_000,
        11_000_000,
    ),
    Client(
        Party(
            "Lembang Hillside Hotel",
            ("Jl. Raya Lembang 260", "Lembang 40391"),
            "99-225.611.3-441.000",
        ),
        25_000_000,
        48_000_000,
    ),
    Client(
        Party(
            "Dago Bakery & Co.", ("Jl. Ir. H. Juanda 88", "Bandung 40135"), "99-341.907.2-423.000"
        ),
        5_000_000,
        14_000_000,
    ),
    Client(
        Party(
            "Cimahi Office Pantry Services",
            ("Jl. Amir Machmud 15", "Cimahi 40526"),
            "99-456.220.9-421.000",
        ),
        9_000_000,
        20_000_000,
    ),
    Client(
        Party(
            "Pasar Baru Grocers",
            ("Jl. Otto Iskandardinata 70", "Bandung 40181"),
            "99-563.118.5-429.000",
        ),
        12_000_000,
        26_000_000,
    ),
    Client(
        Party("Sunda Kitchen Group", ("Jl. Pasteur 33", "Bandung 40161"), "99-672.405.1-422.000"),
        30_000_000,
        55_000_000,
    ),
    Client(
        Party(
            "Jatinangor Campus Canteen",
            ("Jl. Raya Jatinangor 9", "Sumedang 45363"),
            "99-781.539.6-446.000",
        ),
        6_000_000,
        16_000_000,
    ),
]

PRODUCTS = [
    ("Arabica roasted beans, 1 kg", Decimal("285000")),
    ("Robusta roasted beans, 1 kg", Decimal("180000")),
    ("House blend espresso, 1 kg", Decimal("240000")),
    ("Drip bags, box of 20", Decimal("95000")),
    ("Cold brew concentrate, 1 L", Decimal("120000")),
]


@dataclass(frozen=True)
class Supplier:
    code: str
    party: Party
    pay_to: PayTo
    layout: str
    expense_account: str
    category: str
    products: tuple[tuple[str, Decimal, int, int], ...]  # description, unit price, qty lo, qty hi


GREEN_VALLEY = Supplier(
    "gvf",
    Party(
        "Green Valley Farms",
        ("Km 14 Ciwidey Road", "Bandung Regency 40973"),
        "99-114.906.4-445.000",
    ),
    PayTo(BANK_NAME, "9900007312", "GREEN VALLEY FARMS"),
    "gvf",
    "5100",
    "INVENTORY_PURCHASE",
    (
        ("Green beans, Arabica Java Preanger, 60 kg sack", Decimal("6900000"), 2, 4),
        ("Green beans, Robusta Temanggung, 60 kg sack", Decimal("3850000"), 1, 3),
    ),
)
PRIMEPACK = Supplier(
    "primepack",
    Party(
        "PrimePack Packaging",
        ("Block C-7 Cimahi Industrial Estate", "Cimahi 40552"),
        "99-552.031.7-421.000",
    ),
    PayTo(BANK_NAME, "9900016645", "PRIMEPACK PACKAGING"),
    "primepack",
    "5200",
    "INVENTORY_PURCHASE",
    (
        ("Valve bags 250 g, printed", Decimal("1850"), 1500, 3000),
        ("Kraft boxes 1 kg", Decimal("4200"), 300, 700),
    ),
)
ROASTLINE = Supplier(
    "roastline",
    Party(
        "Roastline Equipment Service",
        ("33 Foundry Street", "Bandung 40213"),
        "99-873.250.6-422.000",
    ),
    PayTo(BANK_NAME, "9900023318", "ROASTLINE EQUIPMENT SERVICE"),
    "roastline",
    "6600",
    "SUPPLIER_PAYMENT",
    (
        ("Roaster maintenance visit", Decimal("2750000"), 1, 1),
        ("Burner nozzle set", Decimal("640000"), 1, 3),
    ),
)
# S4 (T12): Roastline's May invoice asks to be paid into a new account at another bank.
ROASTLINE_NEW_PAY_TO = PayTo(SECOND_BANK, "7100553108", "ROASTLINE EQUIPMENT SVC")
# S4 (T13): a supplier nobody has ever paid.
BLUEWATER = Supplier(
    "bluewater",
    Party(
        "Bluewater Trading Co.",
        ("Unit 5, 210 Harbour Road", "Jakarta 14430"),
        "99-660.417.3-031.000",
    ),
    PayTo(SECOND_BANK, "7100689921", "BLUEWATER TRADING CO"),
    "bluewater",
    "5100",
    "INVENTORY_PURCHASE",
    (("Green beans, Arabica Gayo, 60 kg sack", Decimal("7400000"), 1, 2),),
)
SUPPLIERS = [GREEN_VALLEY, PRIMEPACK, ROASTLINE]
# Spec 024: more suppliers for the demo's volume only (a real roaster's month has many bills); the
# books of docs/18 never use them.
EXTRA_SUPPLIERS = [
    Supplier(
        "gayo",
        Party(
            "Gayo Highland Coffee Cooperative",
            ("Jl. Takengon 12", "Aceh Tengah 24552"),
            "99-401.226.8-101.000",
        ),
        PayTo(BANK_NAME, "9900031876", "GAYO HIGHLAND COFFEE COOP"),
        "gvf",
        "5100",
        "INVENTORY_PURCHASE",
        (("Green beans, Arabica Gayo, 60 kg sack", Decimal("7150000"), 1, 3),),
    ),
    Supplier(
        "sinar",
        Party(
            "Sinar Label Printing", ("Jl. Cibaduyut 77", "Bandung 40239"), "99-318.540.2-422.000"
        ),
        PayTo(BANK_NAME, "9900042259", "SINAR LABEL PRINTING"),
        "primepack",
        "5200",
        "INVENTORY_PURCHASE",
        (
            ("Bag labels, full colour", Decimal("420"), 2000, 6000),
            ("Gift sleeves", Decimal("2600"), 100, 400),
        ),
    ),
    Supplier(
        "kilat",
        Party(
            "Kilat Logistics", ("Jl. Soekarno-Hatta 455", "Bandung 40266"), "99-207.815.5-424.000"
        ),
        PayTo(BANK_NAME, "9900055041", "KILAT LOGISTICS"),
        "roastline",
        "6300",
        "SUPPLIER_PAYMENT",
        (("Pallet freight, Bandung to Jakarta", Decimal("1250000"), 1, 4),),
    ),
    Supplier(
        "parahyangan",
        Party(
            "Parahyangan Office Supply", ("Jl. Braga 38", "Bandung 40111"), "99-590.114.7-423.000"
        ),
        PayTo(BANK_NAME, "9900068813", "PARAHYANGAN OFFICE SUPPLY"),
        "roastline",
        "6200",
        "SUPPLIER_PAYMENT",
        (
            ("Printer paper, box", Decimal("265000"), 2, 8),
            ("Toner cartridge", Decimal("890000"), 1, 2),
        ),
    ),
    Supplier(
        "toba",
        Party("Toba Jute Sacks", ("Jl. Sisingamangaraja 9", "Medan 20217"), "99-713.402.6-121.000"),
        PayTo(BANK_NAME, "9900079120", "TOBA JUTE SACKS"),
        "primepack",
        "5200",
        "INVENTORY_PURCHASE",
        (("Jute sacks, 60 kg, printed", Decimal("38500"), 100, 400),),
    ),
]
# Which suppliers invoice in which month: 3, 2, 3, 2, 3, 3 = 16 (docs/18 §3.6).
SUPPLIER_SCHEDULE: dict[str, list[Supplier]] = {
    "2026-01": [GREEN_VALLEY, PRIMEPACK, ROASTLINE],
    "2026-02": [GREEN_VALLEY, PRIMEPACK],
    "2026-03": [GREEN_VALLEY, PRIMEPACK, ROASTLINE],
    "2026-04": [GREEN_VALLEY, PRIMEPACK],
    "2026-05": [GREEN_VALLEY, PRIMEPACK, ROASTLINE],
    "2026-06": [GREEN_VALLEY, PRIMEPACK, ROASTLINE],
}


@dataclass(frozen=True)
class Merchant:
    party: Party
    account: str
    items: tuple[tuple[str, Decimal, int, int], ...]


MERCHANTS = [
    Merchant(
        Party("Cendana Fuel Station", ("Jl. Setiabudi 210", "Bandung")),
        "6100",
        (("Diesel, litre", Decimal("6800"), 20, 90),),
    ),
    Merchant(
        Party("Papyrus Office Supply", ("Jl. Braga 14", "Bandung")),
        "6200",
        (
            ("Printer paper A4, ream", Decimal("58000"), 1, 6),
            ("Shipping labels, roll", Decimal("42000"), 1, 4),
        ),
    ),
    Merchant(
        Party("Swift Courier", ("Jl. Pasteur 77", "Bandung")),
        "6300",
        (
            ("Same-day parcel, Bandung", Decimal("38000"), 2, 9),
            ("Express parcel, Jakarta", Decimal("64000"), 1, 5),
        ),
    ),
    Merchant(
        Party("Lotus Hardware", ("Jl. Kopo 120", "Bandung")),
        "6500",
        (("Cable ties, pack", Decimal("27000"), 1, 4), ("Shelf bracket", Decimal("46000"), 2, 8)),
    ),
    Merchant(
        Party("Corner Bakery", ("Jl. Dago 5", "Bandung")),
        "6400",
        (
            ("Pastry box for tasting", Decimal("85000"), 1, 3),
            ("Bread loaf", Decimal("32000"), 1, 4),
        ),
    ),
]

# LedgerLite 3 chart of accounts (docs/18 §3.5).
ACCOUNTS = {
    "1000": "Petty cash",
    "1110": "Cash at bank – ACB",
    "1200": "Accounts receivable",
    "1300": "Prepaid income tax",
    "1400": "VAT input",
    "2100": "Accounts payable",
    "2200": "VAT output",
    "2300": "Bank loan",
    "3100": "Owner drawings",
    "4000": "Sales",
    "4100": "Retail sales",
    "5100": "Green coffee purchases",
    "5200": "Packaging",
    "6000": "Salaries and wages",
    "6050": "Warehouse rent",
    "6100": "Fuel",
    "6150": "Utilities",
    "6200": "Office supplies",
    "6300": "Courier",
    "6400": "Meals and tasting",
    "6500": "Repairs and maintenance",
    "6600": "Equipment service",
    "6900": "Bank charges",
    "7100": "Interest expense",
}

LOAN_REF = "LN-0071-2291"
LOAN_INSTALLMENT = Decimal("8450000.00")
LOAN_INTEREST = Decimal("1215000.00")
RENT = Decimal("15000000.00")
INTERNET = Decimal("1150000.00")  # above any receipt, so never ambiguous with one
ADMIN_FEE = Decimal("25000.00")
OPENING_JANUARY = Decimal("120000000.00")
T1_ANCHOR_DATE = date(YEAR, 3, 14)
T1_ANCHOR_AMOUNT = Decimal("1250000.00")
T1_EDITED_AMOUNT = Decimal("7250000.00")
T11_FROM = date(YEAR, 5, 12)  # S3 duplicates the first referenced bank journal from this day


def month_parts(month: str) -> tuple[int, int]:
    year, mon = month.split("-")
    return int(year), int(mon)


MONTH_ABBR = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MONTH_NAME = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
