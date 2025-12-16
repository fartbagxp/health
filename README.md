# Overview

This is a repository to collect and run fun experiments on various publicly available health APIs.

## Sources

| Data Source                                                           | Origin |
| --------------------------------------------------------------------- | ------ |
| [Wide-ranging ONline Data for Epidemiologic Research (WONDER)]        | [CDC]  |
| [National Wastewater Surveillance System (NWSS)]                      | [CDC]  |
| [National Syndromic Surveillance Program (NSSP)]                      | [CDC]  |
| [National Respiratory and Enteric Virus Surveillance System (NREVSS)] | [CDC]  |
| [National Healthcare Safety Network (NHSN)]                           | [CDC]  |
| [Children Vaccination]                                                | [CDC]  |

### CDC WONDER

[CDC WONDER - Wide-ranging ONline Data for Epidemiologic Research](https://wonder.cdc.gov/) includes an unauthenticated Application Programmatic Interface (API) for birth (natality), death, and cancer statistics. The [Wonder API](https://wonder.cdc.gov/wonder/help/wonder-api.html) is a non-standard custom XML on HTTPS API with non-standard headers like sending `accept_datause_restrictions` with a value of "true" as a XML parameter via a HTTP POST to accept an agreement.

The XML parameters it supports is similar to querying a database, with these examples.

- U.S. national cancer deaths (ICD-10 codes C00-D48) by year and by race, for the 5 year time period 2009-2013. Number of deaths, population estimates, crude death rates and age-adjusted death rates per 100,000 persons, 95% confidence intervals and standard errors for age-adjusted death rates.

  - [Request for Cancer Death Rate](https://wonder.cdc.gov/wonder/help/api-examples/D76_Example1-req.xml)
  - [Response for Cancer Death Rate](https://wonder.cdc.gov/wonder/help/api-examples/D76_Example1-resp.xml)

- U.S. national injury deaths for persons age 18 and under, by Injury Intent and Injury Mechanism, for years 1999-2013. Number of deaths, population estimates, crude death rates.
  - [Request for National Injury Deaths](https://wonder.cdc.gov/wonder/help/API-Examples/D76_Example2-req.xml)
  - [Response for National Injury Deaths](https://wonder.cdc.gov/wonder/help/API-Examples/D76_Example2-resp.xml)

We can find better explanation of the parameters via an [open source repository by alipphardt](https://github.com/alipphardt/cdc-wonder-api?tab=readme-ov-file#reference-for-all-request-parameters).

The soft rate limit is a query every two minutes to let the WONDER database recover.

[CDC]: https://www.cdc.gov
[Wide-ranging ONline Data for Epidemiologic Research (WONDER)]: https://wonder.cdc.gov/wonder/help/wonder-api.html
[National Wastewater Surveillance System (NWSS)]: https://www.cdc.gov/nwss/about.html
[National Syndromic Surveillance Program (NSSP)]: https://data.cdc.gov/Public-Health-Surveillance/NSSP-Emergency-Department-Visit-Trajectories-by-St/rdmq-nq56/about_data
[National Respiratory and Enteric Virus Surveillance System (NREVSS)]: https://www.cdc.gov/nrevss/php/dashboard/index.html
[National Healthcare Safety Network (NHSN)]: https://www.cdc.gov/nhsn/datastat/index.html
[Children Vaccination]: https://data.cdc.gov/Child-Vaccinations/Vaccination-Coverage-among-Young-Children-0-35-Mon/fhky-rtsk/about_data
