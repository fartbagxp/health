"""
National Immunization Survey (NIS) — Python parser for CDC fixed-width DAT files.

Two surveys are supported:
  NIS-Child  children 19–35 months  (https://www.cdc.gov/nis/php/datasets-child/index.html)
  NIS-Teen   adolescents 13–17 yr   (https://www.cdc.gov/nis/php/datasets-teen/index.html)

Data are fixed-width ASCII .dat files distributed with SAS/R import programs.
This module parses the SAS codebook on the fly and streams the .dat file
without writing anything to disk.

Geographic scope of public-use files:
  National and state level — county-level identifiers are suppressed in
  the public-use release and require CDC Research Data Center access.
"""
