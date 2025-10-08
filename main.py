import requests
import bs4 as bs
import pandas as pd
import warnings

from bs4 import XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def create_parameter_xml(params):
    xml = ""
    for key, val in params.items():
        xml += "<parameter>\n<name>" + key + "</name>\n"
        if isinstance(val, list):
            for v in val:
                xml += "<value>" + v + "</value>\n"
        else:
            xml += "<value>" + val + "</value>\n"
        xml += "</parameter>\n"
    return xml


def build_request_xml():
    b = {
        "B_1": "D76.V1-level1",
        "B_2": "D76.V8",
        "B_3": "*None*",
        "B_4": "*None*",
        "B_5": "*None*",
    }

    m = {
        "M_1": "D76.M1",
        "M_2": "D76.M2",
        "M_3": "D76.M3",
        "M_41": "D76.M41",
        "M_42": "D76.M42",
    }

    f = {
        "F_D76.V1": ["*All*"],
        "F_D76.V2": ["K00-K92"],
        "F_D76.V9": ["*All*"],
        "F_D76.V10": ["*All*"],
        "F_D76.V27": ["*All*"],
    }

    i = {
        "I_D76.V1": "*All* (All Dates)",
        "I_D76.V2": "K00-K92 (Diseases of the digestive system)",
        "I_D76.V9": "*All* (The United States)",
        "I_D76.V10": "*All* (The United States)",
        "I_D76.V27": "*All* (The United States)",
    }

    v = {
        "V_D76.V1": "",
        "V_D76.V2": "",
        "V_D76.V4": "*All*",
        "V_D76.V5": ["15-24", "25-34", "35-44"],
        "V_D76.V6": "00",
        "V_D76.V7": "*All*",
        "V_D76.V8": "*All*",
        "V_D76.V9": "",
        "V_D76.V10": "",
        "V_D76.V11": "*All*",
        "V_D76.V12": "*All*",
        "V_D76.V17": "*All*",
        "V_D76.V19": "*All*",
        "V_D76.V20": "*All*",
        "V_D76.V21": "*All*",
        "V_D76.V22": "*All*",
        "V_D76.V23": "*All*",
        "V_D76.V24": "*All*",
        "V_D76.V25": "*All*",
        "V_D76.V27": "",
        "V_D76.V51": "*All*",
        "V_D76.V52": "*All*",
    }

    o = {
        "O_aar": "aar_std",
        "O_aar_pop": "0000",
        "O_age": "D76.V5",
        "O_javascript": "on",
        "O_location": "D76.V9",
        "O_precision": "1",
        "O_rate_per": "100000",
        "O_show_totals": "false",
        "O_timeout": "300",
        "O_title": "Digestive Disease Deaths, by Age Group",
        "O_ucd": "D76.V2",
        "O_urban": "D76.V19",
        "O_V1_fmode": "freg",
        "O_V2_fmode": "freg",
        "O_V9_fmode": "freg",
        "O_V10_fmode": "freg",
        "O_V27_fmode": "freg",
    }

    vm = {
        "VM_D76.M6_D76.V10": "",
        "VM_D76.M6_D76.V17": "*All*",
        "VM_D76.M6_D76.V1_S": "*All*",
        "VM_D76.M6_D76.V7": "*All*",
        "VM_D76.M6_D76.V8": "*All*",
    }

    misc = {
        "action-Send": "Send",
        "finder-stage-D76.V1": "codeset",
        "finder-stage-D76.V2": "codeset",
        "finder-stage-D76.V27": "codeset",
        "finder-stage-D76.V9": "codeset",
        "stage": "request",
    }

    xml = "<request-parameters>\n"
    for p in [b, m, f, i, v, o, vm, misc]:
        xml += create_parameter_xml(p)
    xml += "</request-parameters>"
    return xml


def post_cdc_wonder(xml_request):
    url = "https://wonder.cdc.gov/controller/datarequest/D76"
    r = requests.post(
        url, data={"request_xml": xml_request, "accept_datause_restrictions": "true"}
    )
    if r.status_code != 200:
        raise RuntimeError("CDC WONDER request failed")
    return r.text


def xml_to_table(xml_data):
    root = bs.BeautifulSoup(xml_data, "lxml")
    rows = root.find_all("r")
    out = []
    rownum = 0

    for row in rows:
        if rownum >= len(out):
            out.append([])
        for cell in row.find_all("c"):
            if "v" in cell.attrs:
                try:
                    out[rownum].append(float(cell["v"].replace(",", "")))
                except ValueError:
                    out[rownum].append(cell["v"])
            elif "l" in cell.attrs:
                label = cell["l"]
                repeat = int(cell.get("r", 1))
                for i in range(repeat):
                    if rownum + i >= len(out):
                        out.append([])
                    out[rownum + i].append(label)
        rownum += 1
    return out


def run():
    xml = build_request_xml()
    raw = post_cdc_wonder(xml)
    records = xml_to_table(raw)
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
