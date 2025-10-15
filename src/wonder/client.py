import requests


class Client:
    def post_cdc_wonder(self, data):
        url = "https://wonder.cdc.gov/controller/datarequest/D76"
        r = requests.post(url, data=data)
        if r.status_code != 200:
            raise RuntimeError("CDC WONDER request failed")
        return r.text
