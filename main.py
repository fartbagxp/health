import pandas as pd

from src.wonder.handler import Handler
from src.wonder.client import Client


def run():
    handler = Handler()
    xml = handler.build_request_xml()
    data = handler.build_request_data(xml)
    client = Client()
    raw = client.post_cdc_wonder(data)
    records = handler.xml_to_table(raw)
    df = pd.DataFrame(
        records,
        columns=[
            "Year",
            "Race",
            "Deaths",
            "Population",
            "Crude Rate",
            "Age-adjusted Rate",
            "Age-adjusted Rate SE",
        ],
    )
    print(df.head())


if __name__ == "__main__":
    run()
