"""
NIS dataset registry: URL patterns and vaccination column definitions.

File hosting
------------
The CDC does not use one consistent location or naming scheme for NIS
public-use files, so URLs are listed per year below (taken from the index
pages as of 2026-11).  Roughly:
  2011–2014:  ftp.cdc.gov/pub/health_statistics/nchs/datasets/nis/  (DAT + SAS)
  2015–2022:  DAT on ftp.cdc.gov/pub/Vaccines_NIS/,
              SAS on www.cdc.gov/vaccines/imz-managers/nis/downloads/
  some years: www.cdc.gov/nis/media/files/<yyyy>/<mm>/

Index pages (browse available years and direct download links):
  Child: https://www.cdc.gov/nis/php/datasets-child/index.html
  Teen:  https://www.cdc.gov/nis/php/datasets-teen/index.html

If a year starts returning 404, check the index page for its new link.

Geographic scope of public-use files
-------------------------------------
National and state level only.  County-level identifiers are suppressed in
the public-use release; county data requires CDC Research Data Center access.

Vaccination columns
--------------------
Variable names beginning with P_UTD are provider-verified "up-to-date" (UTD)
status flags coded 1=UTD, 0=not UTD.  Names ending in _D typically indicate
provider-verified subsets.  Survey weights (PROVWT_D for child, PROVWT_C for
teen) should be used for nationally representative estimates.

Both column sets below are *requests* — if a column did not exist in a given
year's release, stream_dat() returns '' for that field rather than an error.
"""

from dataclasses import dataclass

_FTP_NCHS = "https://ftp.cdc.gov/pub/health_statistics/nchs/datasets/nis"
_FTP_VAX = "https://ftp.cdc.gov/pub/Vaccines_NIS"
_CDC_DL = "https://www.cdc.gov/vaccines/imz-managers/nis/downloads"
_CDC_MEDIA = "https://www.cdc.gov/nis/media/files"

INDEX_URLS = {
    "child": "https://www.cdc.gov/nis/php/datasets-child/index.html",
    "teen": "https://www.cdc.gov/nis/php/datasets-teen/index.html",
}


@dataclass(frozen=True)
class NISYear:
    year: int
    dat_url: str
    sas_url: str


# Known available years for each survey (2011–2022). Earlier years exist but use
# different file layouts; later years have not been verified against the parser.
_CHILD_URLS: dict[int, tuple[str, str]] = {
    2011: (f"{_FTP_NCHS}/NISPUF11.DAT", f"{_FTP_NCHS}/NISPUF11.SAS"),
    2012: (f"{_FTP_NCHS}/NISPUF12.DAT", f"{_FTP_NCHS}/NISPUF12.SAS"),
    2013: (f"{_FTP_NCHS}/NISPUF13.DAT", f"{_FTP_NCHS}/NISPUF13.SAS"),
    2014: (f"{_FTP_NCHS}/NISPUF14.DAT", f"{_FTP_NCHS}/NISPUF14.SAS"),
    2015: (f"{_FTP_VAX}/NISPUF15.DAT", f"{_CDC_DL}/NIS-PUF15.SAS"),
    2016: (f"{_FTP_VAX}/NISPUF16.DAT", f"{_CDC_DL}/NISPUF16.SAS"),
    2017: (f"{_FTP_VAX}/NISPUF17.DAT", f"{_CDC_DL}/NIS-PUF17.SAS"),
    2018: (f"{_FTP_VAX}/NISPUF18.DAT", f"{_CDC_DL}/NIS-PUF18.SAS"),
    2019: (f"{_FTP_VAX}/NISPUF19.DAT", f"{_CDC_MEDIA}/2024/09/NISPUF19.SAS"),
    2020: (f"{_FTP_VAX}/NISPUF20.DAT", f"{_CDC_DL}/NIS-PUF20.SAS"),
    2021: (f"{_FTP_VAX}/NISPUF21.DAT", f"{_CDC_DL}/NIS-PUF21.SAS"),
    2022: (f"{_FTP_VAX}/NISPUF22.DAT", f"{_CDC_DL}/NIS-PUF22.SAS"),
}
_TEEN_URLS: dict[int, tuple[str, str]] = {
    2011: (f"{_FTP_NCHS}/NISTEENPUF11.DAT", f"{_FTP_NCHS}/NISTEENPUF11.SAS"),
    2012: (f"{_FTP_NCHS}/NISTEENPUF12.DAT", f"{_FTP_NCHS}/NISTEENPUF12.SAS"),
    2013: (f"{_FTP_NCHS}/NISTEENPUF13.DAT", f"{_FTP_NCHS}/NISTEENPUF13.SAS"),
    2014: (f"{_FTP_NCHS}/NISTEENPUF14.DAT", f"{_FTP_NCHS}/NISTEENPUF14.SAS"),
    2015: (
        "https://ftp.cdc.gov/pub/vaccines2/nis-teen/NISTEENPUF15.DAT",
        f"{_CDC_DL}/NIS-teen-puf15.sas",
    ),
    2016: (f"{_FTP_VAX}/NISTEENPUF16.DAT", f"{_CDC_DL}/NIS-TEEN-PUF16.SAS"),
    2017: (f"{_FTP_VAX}/NISTEENPUF17.DAT", f"{_CDC_DL}/NIS-TEEN-PUF17.SAS"),
    2018: (f"{_FTP_VAX}/NISTEENPUF18.DAT", f"{_CDC_DL}/NIS-TEEN-PUF18.SAS"),
    2019: (f"{_FTP_VAX}/NISTEENPUF19.DAT", f"{_CDC_DL}/NIS-TEEN-PUF19.SAS"),
    2020: (f"{_FTP_VAX}/NISTEENPUF20.DAT", f"{_CDC_DL}/NIS-TEEN-PUF20.SAS"),
    2021: (f"{_FTP_VAX}/NISTEENPUF21.DAT", f"{_CDC_DL}/NIS-TEEN-PUF21.SAS"),
    2022: (f"{_FTP_VAX}/NISTEENPUF22.DAT", f"{_CDC_MEDIA}/2025/02/NISTEENPUF22.SAS"),
}

CHILD_YEARS: dict[int, NISYear] = {
    year: NISYear(year=year, dat_url=dat, sas_url=sas)
    for year, (dat, sas) in _CHILD_URLS.items()
}
TEEN_YEARS: dict[int, NISYear] = {
    year: NISYear(year=year, dat_url=dat, sas_url=sas)
    for year, (dat, sas) in _TEEN_URLS.items()
}

SURVEY_YEARS = {
    "child": CHILD_YEARS,
    "teen": TEEN_YEARS,
}

# ── Column definitions ─────────────────────────────────────────────────────────
# These are the variable names requested from the DAT file. Missing columns
# (not present in a particular year) silently return ''.

#: Geographic and demographic columns common to NIS-Child.
CHILD_GEO_COLS: set[str] = {
    "RETEILI",  # state/local-area FIPS estimation code
    "CEN_REGI",  # Census region (1=NE, 2=MW, 3=S, 4=W)
    "AGEGRP",  # age group (1=19-23mo, 2=24-29mo, 3=30-35mo)
    "RACE_K",  # race/ethnicity (1=H, 2=NH-W, 3=NH-B, 4=NH-Other)
    "INCPOV1",  # income/poverty (1=<100%, 2=100-133%, 3=133-322%, 4=≥322%)
    "EDUC1",  # mother's education (1=<12yr, 2=12yr, 3=some college, 4=college+)
    "MARITAL2",  # marital status (1=married, 2=not married)
    "LANGUAGE",  # survey language (1=English, 2=Spanish)
    "PROVWT_D",  # survey weight — provider-verified subsample
}

#: Provider-verified vaccination UTD flags for NIS-Child.
CHILD_VAX_COLS: set[str] = {
    # Individual vaccines
    "P_UTDDTP4",  # DTaP ≥4 doses
    "P_UTDDTP3",  # DTaP ≥3 doses
    "P_UTDMMX",  # MMR ≥1 dose
    "P_UTDPOL3",  # Polio ≥3 doses
    "P_UTDHIB4",  # Hib ≥4 doses (full series + booster)
    "P_UTDHIB3",  # Hib ≥3 doses (primary series)
    "P_UTDPCV4",  # PCV ≥4 doses
    "P_UTDPCV3",  # PCV ≥3 doses
    "P_UTDHEP_B",  # HepB ≥3 doses
    "P_UTDHEP_A",  # HepA ≥2 doses
    "P_UTDHEP_A1",  # HepA ≥1 dose
    "P_UTDVAR",  # Varicella ≥1 dose
    "P_UTDVAR2",  # Varicella ≥2 doses
    "P_UTDROT2",  # Rotavirus ≥2 doses
    "P_UTDROT3",  # Rotavirus ≥3 doses
    "P_UTDFLUN4",  # Flu ≥2 doses (first-season children)
    "P_UTDFLUN2",  # Flu ≥1 dose
    # Combined series
    "P_UTD731",  # Combined 7-vaccine series UTD
    "P_UTD431",  # Combined 4:3:1 series UTD
    "P_UTD43131",  # 4:3:1:3:1 series
    "P_UTD43131314",  # full 10-vaccine schedule
}

#: Vaccine hesitancy indicators for NIS-Child.
CHILD_HESI_COLS: set[str] = {
    "SHOT_HES",  # hesitancy flag (1=yes, 0=no)
    "HESI_RECS",  # heard hesitancy-related recommendations
    "NO_VX_REC",  # provider did not recommend vaccination
}

#: All NIS-Child columns requested by default.
CHILD_COLS: set[str] = CHILD_GEO_COLS | CHILD_VAX_COLS | CHILD_HESI_COLS

# ──────────────────────────────────────────────────────────────────────────────

#: Geographic and demographic columns common to NIS-Teen.
TEEN_GEO_COLS: set[str] = {
    "STATE",  # 2-digit FIPS state code
    "RETEILI",  # state/local-area estimation code (some years)
    "CEN_REGI",  # Census region
    "AGEGRP",  # age group (13–14, 15–17, etc.)
    "RACE_K",  # race/ethnicity
    "INCPOV1",  # income/poverty ratio
    "EDUC1",  # mother's education
    "MARITAL2",  # marital status
    "LANGUAGE",  # survey language
    "PROVWT_C",  # survey weight — provider-verified subsample
}

#: Provider-verified vaccination UTD flags for NIS-Teen.
TEEN_VAX_COLS: set[str] = {
    "P_UTDTDAP",  # Tdap ≥1 dose
    "P_UTDMCV4",  # MCV4 (meningococcal) ≥1 dose
    "P_UTDMCV4TD",  # MCV4 at ≥13yr (if applicable)
    "P_UTDHPV13",  # HPV series complete (≥2 doses <15yr, ≥3 doses ≥15yr)
    "P_UTDHPV2",  # HPV ≥2 doses
    "P_UTDHPV1",  # HPV ≥1 dose (initiation)
    "P_UTDHEP_A",  # HepA ≥2 doses
    "P_UTDHEP_B",  # HepB ≥3 doses
    "P_UTD_FLU",  # Flu vaccination current season
    "P_UTDMENING_B",  # Meningococcal B ≥2 doses (added ~2020)
}

#: Vaccine hesitancy indicators for NIS-Teen.
TEEN_HESI_COLS: set[str] = {
    "SHOT_HES",  # hesitancy flag (1=yes, 0=no)
    "NOT_SURE_VACC",  # not sure about vaccinating (1=yes)
    "NO_VX_REC",  # provider did not recommend (1=yes)
}

#: All NIS-Teen columns requested by default.
TEEN_COLS: set[str] = TEEN_GEO_COLS | TEEN_VAX_COLS | TEEN_HESI_COLS

SURVEY_COLS = {
    "child": CHILD_COLS,
    "teen": TEEN_COLS,
}

SURVEY_VAX_COLS = {
    "child": CHILD_VAX_COLS,
    "teen": TEEN_VAX_COLS,
}

SURVEY_GEO_COLS = {
    "child": CHILD_GEO_COLS,
    "teen": TEEN_GEO_COLS,
}

# State FIPS → name lookup (standard US FIPS codes)
FIPS_TO_STATE: dict[str, str] = {
    "01": "Alabama",
    "02": "Alaska",
    "04": "Arizona",
    "05": "Arkansas",
    "06": "California",
    "08": "Colorado",
    "09": "Connecticut",
    "10": "Delaware",
    "11": "District of Columbia",
    "12": "Florida",
    "13": "Georgia",
    "15": "Hawaii",
    "16": "Idaho",
    "17": "Illinois",
    "18": "Indiana",
    "19": "Iowa",
    "20": "Kansas",
    "21": "Kentucky",
    "22": "Louisiana",
    "23": "Maine",
    "24": "Maryland",
    "25": "Massachusetts",
    "26": "Michigan",
    "27": "Minnesota",
    "28": "Mississippi",
    "29": "Missouri",
    "30": "Montana",
    "31": "Nebraska",
    "32": "Nevada",
    "33": "New Hampshire",
    "34": "New Jersey",
    "35": "New Mexico",
    "36": "New York",
    "37": "North Carolina",
    "38": "North Dakota",
    "39": "Ohio",
    "40": "Oklahoma",
    "41": "Oregon",
    "42": "Pennsylvania",
    "44": "Rhode Island",
    "45": "South Carolina",
    "46": "South Dakota",
    "47": "Tennessee",
    "48": "Texas",
    "49": "Utah",
    "50": "Vermont",
    "51": "Virginia",
    "53": "Washington",
    "54": "West Virginia",
    "55": "Wisconsin",
    "56": "Wyoming",
    "72": "Puerto Rico",
    "78": "U.S. Virgin Islands",
}

STATE_TO_FIPS: dict[str, str] = {v.upper(): k for k, v in FIPS_TO_STATE.items()}
