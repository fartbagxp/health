from src.wonder.client import WonderClient

client = WonderClient()
response = client.execute_query_file('src/wonder/queries/opioid-overdose-deaths-2018-2024-req.xml')
print(client.parse_response_to_arrays(response))

