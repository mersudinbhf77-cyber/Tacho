# Tacho Studio — EU 561/2006 & AETR Driver Rest Compliance Analyzer

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)

**Tacho Studio** is an open-source compliance and calculation tool designed for transport operators, fleet dispatchers, and commercial drivers. It automates the parsing of digital tachograph activity logs and calculates daily and weekly rest periods strictly according to **Regulation (EC) No 561/2006** and the **AETR Agreement**.

---

## Why This Project Exists (Ecosystem Gap)

Most tachograph analysis tools are expensive proprietary enterprise suites locked behind per-vehicle monthly subscriptions. Small fleets, independent drivers, and open-source logistics developers lack a transparent, auditable, and free engine to verify daily rest violations, split-rest rules, and multi-manning exceptions without manual spreadsheet errors.

**Tacho Studio** fills this gap by providing a standalone, verifiable calculation engine and desktop interface.

---

## Key Features

- **Automated Rest Period Calculation:** Evaluates regular daily rest (11h), reduced daily rest (9h, max 3 times between weekly rests), and split daily rest (3h + 9h).
- **EU 561/2006 & AETR Rule Engine:** Flags driving time extensions, insufficient rest intervals, and 24-hour window boundary violations.
- **Report Parsing & Export:** Imports standard driver activity reports and generates clear violation summaries for audit readiness.
- **Zero Cloud Dependency:** Runs 100% locally, ensuring sensitive driver and fleet operational data never leaves the user's machine.

---

## Installation & Quick Start

### Prerequisites
- Python 3.10 or higher
- `pip` package manager

### Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/mersudinbhf77-cyber/tacho-studio.git](https://github.com/mersudinbhf77-cyber/tacho-studio.git)
   cd tacho-studio
