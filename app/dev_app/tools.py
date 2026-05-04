from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import logging
from app.utils.text import parse_structured_text, normalize_address

import requests


LOGGER = logging.getLogger(__name__)

FRANKFURTER_API_URL = "https://api.frankfurter.dev/v1"
WORLD_BANK_INDICATOR = "FP.CPI.TOTL"
WORLD_BANK_INFLATION_INDICATOR = "FP.CPI.TOTL.ZG"

CURRENCY_ALIASES = {
    "$": "USD",
    "US$": "USD",
    "USD": "USD",
    "CA$": "CAD",
    "C$": "CAD",
    "CAD": "CAD",
    "€": "EUR",
    "EUR": "EUR",
    "£": "GBP",
    "GBP": "GBP",
    "CHF": "CHF",
    "AUD": "AUD",
    "NZD": "NZD",
    "JPY": "JPY",
    "CNY": "CNY",
    "RMB": "CNY",
    "INR": "INR",
    "BRL": "BRL",
    "MXN": "MXN",
    "SEK": "SEK",
    "NOK": "NOK",
    "DKK": "DKK",
    "SGD": "SGD",
    "AED": "AED",
    "SAR": "SAR",
    "ZAR": "ZAR",
}

CURRENCY_TO_CPI_REGION = {
    "USD": "USA",
    "CAD": "CAN",
    "EUR": "DEU", #No data for the whole europe so we take Germany of France
    "GBP": "GBR",
    "CHF": "CHE",
    "AUD": "AUS",
    "NZD": "NZL",
    "JPY": "JPN",
    "CNY": "CHN",
    "INR": "IND",
    "BRL": "BRA",
    "MXN": "MEX",
    "SEK": "SWE",
    "NOK": "NOR",
    "DKK": "DNK",
    "SGD": "SGP",
    "AED": "ARE",
    "SAR": "SAU",
    "ZAR": "ZAF",
}


def _parse_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        raise ValueError("Le champ 'Fin' est manquant")

    cleaned = str(value).strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(cleaned).date()
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Format de date non gere pour 'Fin': {value}")


def _parse_amount(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if value is None or str(value).strip() == "":
        raise ValueError("Le champ 'Valeur' est vide")

    cleaned = str(value).strip().replace(" ", "").replace("\u00a0", "")
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    for token in ("USD", "CAD", "EUR", "GBP", "CHF", "$", "€", "£"):
        cleaned = cleaned.replace(token, "")

    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Valeur monetaire invalide: {value}") from exc


def _normalise_currency(value: str) -> str:
    if value is None or str(value).strip() == "":
        raise ValueError("Le champ 'Devise' est vide")

    currency = str(value).strip().upper()
    currency = CURRENCY_ALIASES.get(currency, currency)
    if currency not in CURRENCY_ALIASES.values():
        if len(currency) == 3 and currency.isalpha():
            return currency
        raise ValueError(f"Devise non geree: {value}")
    return currency


@lru_cache(maxsize=256)
def _get_world_bank_series(country_code: str, indicator: str) -> dict[int, Decimal]:
    response = requests.get(
        f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}",
        params={"format": "json", "per_page": 2000},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        raise ValueError(f"Reponse World Bank invalide pour {country_code}/{indicator}")

    series = {}
    for row in payload[1]:
        year = row.get("date")
        value = row.get("value")
        if year and value is not None:
            series[int(year)] = Decimal(str(value))

    return series


def _get_cpi_series(country_code: str) -> dict[int, Decimal]:
    return _get_world_bank_series(country_code, WORLD_BANK_INDICATOR)


def _get_inflation_rate_series(country_code: str) -> dict[int, Decimal]:
    return _get_world_bank_series(country_code, WORLD_BANK_INFLATION_INDICATOR)


def _closest_cpi_value(series: dict[int, Decimal], year: int) -> Decimal:
    eligible_years = [available_year for available_year in series if available_year <= year]
    if eligible_years:
        return series[max(eligible_years)]
    return series[min(series)]


def _actualise_from_inflation_rates(amount: Decimal, inflation_rates: dict[int, Decimal], end_year: int) -> Decimal:
    if not inflation_rates:
        raise ValueError("Aucune donnee d'inflation disponible")

    latest_year = max(inflation_rates)
    if end_year >= latest_year:
        return amount

    actualised_amount = amount
    for year in range(end_year + 1, latest_year + 1):
        rate = inflation_rates.get(year)
        if rate is None:
            continue
        actualised_amount *= Decimal("1") + (rate / Decimal("100"))

    return actualised_amount


def _actualise_amount(amount: Decimal, currency: str, end_date: date) -> Decimal:
    region = CURRENCY_TO_CPI_REGION.get(currency)
    if region is None:
        LOGGER.warning(
            "Aucune zone CPI configuree pour %s; actualisation ignoree",
            currency,
        )
        return amount

    cpi_series = _get_cpi_series(region)
    if cpi_series:
        latest_year = max(cpi_series)
        if end_date.year >= latest_year:
            return amount

        start_cpi = _closest_cpi_value(cpi_series, end_date.year)
        end_cpi = cpi_series[latest_year]
        if start_cpi == 0:
            raise ValueError(f"CPI nul pour {currency} en {end_date.year}")

        return amount * (end_cpi / start_cpi)

    inflation_rates = _get_inflation_rate_series(region)
    if inflation_rates:
        LOGGER.debug(
            "Fallback inflation rates utilise pour %s (%s), faute de serie CPI exploitable",
            currency,
            region,
        )
        return _actualise_from_inflation_rates(amount, inflation_rates, end_date.year)

    raise ValueError(f"Aucune donnee CPI ou inflation disponible pour {currency} ({region})")


@lru_cache(maxsize=256)
def _get_usd_rate(base_currency: str) -> Decimal:
    if base_currency == "USD":
        return Decimal("1")

    response = requests.get(
        f"{FRANKFURTER_API_URL}/latest",
        params={"base": base_currency, "symbols": "USD"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    rate = payload.get("rates", {}).get("USD")

    if rate is None:
        raise ValueError(f"Taux de change introuvable pour {base_currency} -> USD")

    return Decimal(str(rate))


def _actualise_USD(project: dict, attributes_to_actualise:list) -> dict:
    project = project.copy()

    currency = _normalise_currency(project.get("Devise"))
    end_date = _parse_date(project.get("Fin"))
    for attribute in attributes_to_actualise:
        amount = _parse_amount(project.get(attribute))
        actualised_amount = _actualise_amount(amount, currency, end_date)
        usd_amount = actualised_amount * _get_usd_rate(currency)
        project[attribute] = round(float(usd_amount), 2)

    project["Devise"] = "USD"
    return project


def _clean_project_text(project: dict) -> dict:
    """
    Analyze and correct projet text into a clean structure to be displayed
    """
    clean_project = project.copy()
    for key, value in clean_project.items():
        if key in ['Description_en', 'Description_fr']:
            clean_project[key] = parse_structured_text(clean_project[key])
        elif key in ['Contexte_en', 'Contexte_fr']:
            clean_project[key] = parse_structured_text(clean_project[key], mode='context')
        elif key == 'client_address': normalize_address(clean_project[key])

    return clean_project
